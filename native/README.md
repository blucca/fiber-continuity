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
