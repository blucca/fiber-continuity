# Native V4 fiber JSON → typed ObjectStore

`native_v4_store INPUT.json OUTPUT.vcobj` uses the original native V4 codec,
checked ObjectStore writes, closed/read-only reopen, immutable typed FiberView
loads and native coordinate-frame views. Input is one isolated V4 polyline
fiber or an array of them. Controls are position-only objects; dense line
points are XYZ triplets. Graph ingestion and surface stages have separate APIs.

## Source and units

- Native API pin: **ScrollPrize/villa@c3d9da6fe42c3bb46fd2603ca060845d843296c3**.
- Stored points are **XYZ annotation voxels**. Caller-provided coordinates bind
  them to a volume; `scale_factor` means stored XYZ = volume voxel XYZ × factor.
- `coordinates.volume_uuid` stores the volume's **`metadata.json` volume.id**
  verbatim. Physical voxel size stays metadata. Apply any ROI origin in the
  input-producing stage. The CLI retains stored coordinates and validates the
  native view in volume voxels.
- The supplied fixture is entirely synthetic, including its declared frame.

## Build and check

Use an existing checkout of the documented pin. Native dependencies: C++20,
CMake ≥3.22, SQLite3, OpenSSL Crypto, ZSTD/pkg-config, nlohmann-json, CURL, ZLIB
and threads. The target uses the native ObjectStore/typed geometry and catalog
libraries; Python, CT reader, server, adapters and link detectors stay disabled.

From this repository root:

```sh
cmake -S native -B temp/native-build -DVILLA_SOURCE_ROOT=/path/to/pinned/villa \
  -DCMAKE_BUILD_TYPE=Release
cmake --build temp/native-build --target native_v4_store --parallel 1
temp/native-build/native_v4_store native/fixture.json temp/synthetic.vcobj
```

Success prints aggregate `format_roundtrip=passed` and preserves point order,
control IDs, source metadata, family, length and frame binding. An existing
output path stops the command. MIT applies to this wrapper and fixture; native
source retains its own licenses.

## From a measured trace envelope

The Python standard-library converter bridges this repository's ROI-local XYZ `curves` envelopes to the native V4 input above. Use the cleaned output for the measured native-clean endpoint. Storage scale is fixed at 1; supply the actual volume's `metadata.json` `id` and the ROI origin in XYZ order. Voxel size is descriptive metadata.

```sh
python native/check-trace-conversion.py
python native/traces_to_v4.py --traces data/clean-traces.json \
  --origin-xyz 2497 2997 8997 --volume-id 20230205180739 \
  --voxel-size-um 7.91 7.91 7.91 --output temp/native-fibers.json
temp/native-build/native_v4_store temp/native-fibers.json temp/fibers.vcobj
```

These example coordinates belong to the documented fresh s1 cube. Each source curve receives a fresh native UUID and two endpoint controls with IDs 0/1. Original source IDs/order, all other curve fields and inferred-gap ranges remain metadata; dense points keep their order and receive the origin once. `manual_tag` fixes the program-selected V/H family, matching the pinned native writer's family semantics.

[The converter's real native check](conversion-check.json) includes the entirely synthetic two-fiber fixture and all 79 fixed-DP clean curves (5,168 points) in the fresh s1 case. Every geometric/frame/source-ID/gap field exactly matches the preceding measured native input; checked writes, closed/read-only reopen and immutable typed loads pass.
