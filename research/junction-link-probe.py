"""First development probe: probability-supported, tangent-conditioned short joins.

Uses frozen spline seeds and the same model probabilities. No labels are read.
The learned baseline's gap/support/margin controls remain a separate comparison.
"""
import numpy as np
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree


def arc(points):
    return np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]


def join(curves, probabilities_czyx, *, radius=12., tangent_support=8.,
         alignment=.94, probability_floor=.65, margin=.10):
    assert probabilities_czyx.shape[0] == 4 and probabilities_czyx.ndim == 4
    assert 0 < probability_floor <= 1 and 0 < alignment <= 1 and margin >= 0
    fields = {"V": probabilities_czyx[1]+probabilities_czyx[3],
              "H": probabilities_czyx[2]+probabilities_czyx[3]}
    lines = [np.asarray(c["points_xyz"], dtype=np.float64) for c in curves]
    endpoints, tokens, directions = [], [], []
    for cid, points in enumerate(lines):
        assert len(points) >= 2 and points.shape[1] == 3 and np.isfinite(points).all()
        for end in (0, 1):
            p = points if end == 0 else points[::-1]
            s = arc(p)
            if s[-1] < tangent_support:
                continue
            inner = np.array([np.interp(tangent_support, s, p[:, k]) for k in range(3)])
            outward = p[0]-inner
            norm = np.linalg.norm(outward)
            if norm < 1e-8:
                continue
            endpoints.append(p[0]); tokens.append((cid, end)); directions.append(outward/norm)
    endpoints, directions = np.asarray(endpoints), np.asarray(directions)
    if len(endpoints) < 2:
        return curves, {"candidate_pairs": 0, "accepted_pairs": [], "parameters": locals_parameters(radius, tangent_support, alignment, probability_floor, margin)}
    pairs = sorted(cKDTree(endpoints).query_pairs(radius))
    candidates, by_endpoint = [], [[] for _ in endpoints]
    for i, j in pairs:
        a, b = tokens[i][0], tokens[j][0]
        if a == b or curves[a]["family"] != curves[b]["family"]:
            continue
        delta = endpoints[j]-endpoints[i]
        distance = np.linalg.norm(delta)
        if distance < 1.:
            continue
        direction = delta/distance
        cosine_a, cosine_b = directions[i]@direction, directions[j]@-direction
        if min(cosine_a, cosine_b) < alignment:
            continue
        t = np.linspace(0., 1., max(3, int(np.ceil(distance/.5))+1))[:, None]
        # Cubic Hermite follows the incoming tangents on both sides.
        bridge = ((2*t**3-3*t**2+1)*endpoints[i]+(t**3-2*t**2+t)*directions[i]*distance
                  +(-2*t**3+3*t**2)*endpoints[j]-(t**3-t**2)*directions[j]*distance)
        field = fields[curves[a]["family"]]
        if np.any(bridge < 0) or np.any(bridge >= np.array(field.shape[::-1])-1):
            continue
        support = map_coordinates(field, bridge[:, ::-1].T.astype(np.float32),
                                  order=1, mode="constant", cval=0, prefilter=False)
        q10 = float(np.quantile(support, .10))
        if q10 < probability_floor:
            continue
        score = float(min(cosine_a, cosine_b)+q10-distance/100.)
        record = {"i": i, "j": j, "score": score, "bridge": bridge,
                  "distance_vox": float(distance), "probability_q10": q10,
                  "cosine_min": float(min(cosine_a, cosine_b))}
        k = len(candidates); candidates.append(record)
        by_endpoint[i].append(k); by_endpoint[j].append(k)
    selected = {}
    for i, rows in enumerate(by_endpoint):
        ranking = sorted(rows, key=lambda k: (-candidates[k]["score"], k))
        if ranking and (len(ranking) == 1 or candidates[ranking[0]]["score"]-candidates[ranking[1]]["score"] >= margin):
            selected[i] = ranking[0]
    parent = list(range(len(lines)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x

    edges, accepted = {}, []
    for k, record in sorted(enumerate(candidates), key=lambda v: -v[1]["score"]):
        i, j = record["i"], record["j"]
        if selected.get(i) != k or selected.get(j) != k:
            continue
        a, b = tokens[i], tokens[j]
        ca, cb = find(a[0]), find(b[0])
        if ca == cb:
            continue
        parent[ca] = cb
        edges[a] = (b, record["bridge"])
        edges[b] = (a, record["bridge"][::-1])
        accepted.append({k: v for k, v in record.items() if k != "bridge"} | {"endpoint_a": list(a), "endpoint_b": list(b)})
    outputs, used = [], set()
    for seed in range(len(lines)):
        if seed in used:
            continue
        component = [c for c in range(len(lines)) if find(c) == find(seed)]
        free = [(c, e) for c in component for e in (0, 1) if (c, e) not in edges]
        assert len(free) == 2
        current, entrance = min(free)
        points, gaps, sources = [], [], []
        while True:
            assert current not in used
            used.add(current); sources.append(str(curves[current]["id"]))
            source = lines[current] if entrance == 0 else lines[current][::-1]
            base = len(points)-1 if points else 0
            if points:
                np.testing.assert_allclose(points[-1], source[0], atol=1e-8, rtol=0)
                points.extend(source[1:].tolist())
            else:
                points.extend(source.tolist())
            for low, high in curves[current].get("gaps", []):
                if entrance == 1:
                    low, high = len(source)-1-high, len(source)-1-low
                gaps.append([int(base+low), int(base+high)])
            exit_token = (current, 1-entrance)
            if exit_token not in edges:
                break
            (next_curve, next_entrance), bridge = edges[exit_token]
            low = len(points)-1
            points.extend(bridge[1:].tolist())
            gaps.append([low, len(points)-1])
            current, entrance = next_curve, next_entrance
        outputs.append({"id": len(outputs), "family": curves[seed]["family"],
                        "points_xyz": points, "gaps": sorted(gaps), "source_curve_ids": sources})
    assert len(used) == len(curves)
    return outputs, {"candidate_pairs": len(candidates), "accepted_pairs": accepted,
                     "parameters": locals_parameters(radius, tangent_support, alignment, probability_floor, margin)}


def locals_parameters(radius, tangent_support, alignment, probability_floor, margin):
    return {"radius_vox": radius, "tangent_support_vox": tangent_support,
            "cosine_alignment_min": alignment, "union_probability_q10_min": probability_floor,
            "score_margin_min": margin, "intersection_weight": 1.}


def check():
    p = np.zeros((4, 32, 32, 96), dtype=np.float32); p[1, 14:19, 14:19, 5:90] = 1
    curves = [{"id": 0, "family": "V", "points_xyz": [[8.,16.,16.],[28.,16.,16.]], "gaps": []},
              {"id": 1, "family": "V", "points_xyz": [[34.,16.,16.],[54.,16.,16.]], "gaps": []}]
    lines, evidence = join(curves, p)
    assert len(lines) == 1 and len(evidence["accepted_pairs"]) == 1 and len(lines[0]["gaps"]) == 1
    p[1, :, :, 30:32] = 0
    assert len(join(curves, p)[0]) == 2
    p[1, 14:19, 14:19, 5:90] = 1
    symmetric = [curves[0]] + [dict(curves[1], id=i+1, points_xyz=[[34.,16.+y,16.],[54.,16.+y,16.]]) for i, y in enumerate((-.5,.5))]
    assert not join(symmetric, p)[1]["accepted_pairs"]
    print("junction probe checks passed")


if __name__ == "__main__":
    check()
