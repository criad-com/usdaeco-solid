# Exact-body acceptance

Version 0.1.2 publishes once from an empty source root and native cache, then
re-flattens the authored layers in a second process and root. It reuses the
first publication for the harness, measurement, B7 and validator rows. The
seeded interchangeable-prototype test remains, and a relocation regression
proves that changing an authored layer changes the repeated publication.
A third regression crosses the prototype identifier 9/10 boundary: re-flattening
replays the two B7 mute/unmute cycles to preserve the original allocation
counter history before the final sorted allocation.

The source gate uses usd-core 26.8; exact operations and the stock renderer
use the separate OpenUSD 0.26.11 / OCCT 7.9.3 runtime. Dependency inputs are
exact tagged archives, and no dependency checkout is built or modified.
The standard toolchain v0.3.4 structure lint runs without the old S04 adapter.

The [machine-readable acceptance](acceptance.json) and
[performance measurements](performance.json) record the final observations.

| Acceptance item | Observed result |
|---|---|
| Solid gate | **49 checks, 0 failed, 0 not run** |
| Pytest | **20 passed, 0 skipped** |
| Standard structure lint | **28 checks, 0 failed**, no adapter; 14 schema rules inapplicable |
| Fresh example, one USD thread | **85.727 s**, including nine renders; budget 120 s |
| Fresh example, two USD threads | **68.185 s**, including nine renders |
| Publication determinism | **PASS**; fresh publication 64.298 s, re-flatten 1.812 s in the gate |
| Repeated normalized crate | 16,720,180 bytes; SHA-256 `4079650453d67ea1f16c962edd932a852aef37e5cc4b6624ec4a110682f08a1a` |
| Office exact bodies | 109/109, 17 IFC classes, 0 failures |
| Wall thickness | 42 walls; maximum error 2.831068712794149e-15 m |
| Pipe outside diameter | 6 pipes; maximum error 0 m |
| Twin volume and area budgets | 109/109 within tolerance |
| B7 exact-layer mute | 109 unchanged twins and transforms; 0 composition errors |
| B7 muted stock render | PASS; 1280 × 800, 100,563 bytes |
| Core validation | 8 loaded; 0 errors, 2 source classification warnings |
| Solid validation | 5 loaded; 0 errors or warnings |
| Native UsdSolid validation | 20 loaded; 0 findings |
| Material partitions | 109/109 complete; 214 exact subsets plus 214 twin subsets |
| Mapped representations | 7 occurrences, 2 shared representation prototypes |
| Exact clearance | 0.005000000000000782 m; zero common volume |
| Hard intersection | 0.00042836676119217495 m³ common volume |
| Tangency | zero distance, zero common volume |
| Relocated crate | 13,145 prims; self-contained; 0 composition errors |
| Result inventory | 7 files; 6,178,041 / 10,000,000 bytes |
| Crate / largest own USDA | 2,205,821 / 1,782,762 bytes |
| Published images | 8 renders plus vanilla, all retained; largest 195,996 bytes |
| Nix | 1 attempt; unresolved nested input; NOT PROVEN |

The office cohort uses body bounding-box midpoints inside the office
footprint, including the boundary and both floors. The source census is
2,980 elements and 3,015 meshes.

| IFC class | Meshable | Exact | Failed |
|---|---:|---:|---:|
| IfcAirTerminal | 4 | 4 | 0 |
| IfcAlarm | 1 | 1 | 0 |
| IfcAudioVisualAppliance | 7 | 7 | 0 |
| IfcCableCarrierFitting | 1 | 1 | 0 |
| IfcCableCarrierSegment | 5 | 5 | 0 |
| IfcColumn | 10 | 10 | 0 |
| IfcCovering | 2 | 2 | 0 |
| IfcDoor | 13 | 13 | 0 |
| IfcElementAssembly | 2 | 2 | 0 |
| IfcFurniture | 2 | 2 | 0 |
| IfcLightFixture | 6 | 6 | 0 |
| IfcPipeSegment | 6 | 6 | 0 |
| IfcSanitaryTerminal | 2 | 2 | 0 |
| IfcSlab | 4 | 4 | 0 |
| IfcStair | 1 | 1 | 0 |
| IfcUnitaryEquipment | 1 | 1 | 0 |
| IfcWall | 42 | 42 | 0 |

## Performance

Run `env -u PYTHONPATH python tools/benchmark_example.py --threads 1 2` with
the README environment. Each run gets an empty temporary source root and
native cache. Timing starts before the runner process and includes IFC
fixture generation, native adapter compilation, exact export, measurements,
flattening, the plugin-free result probe and all nine 1280 × 800 renders.
Copying the source tree and the final benchmark hash reads are outside the
interval. One and two threads mean `PXR_WORK_THREAD_LIMIT=1` and `2` throughout
the child process tree. Measurements are single observations on the same
machine under ambient family-suite load, not isolated CPU reservations.

| USD threads | v0.1.1, 100 samples | v0.1.2, 8 samples | Declared budget |
|---|---:|---:|---:|
| 1 | 354.600 s | **85.727 s** | 120 s |
| 2 | 218.256 s | **68.185 s** | 120 s |

The baseline uses v0.1.1 and its original pins and 100-sample native renderer
default. The updated runner uses the new pins and defaults to 8 samples per
pixel. This preview-quality setting accounts for most of the speedup; it is
not a claim that the kernel became several times faster. The committed PNGs
are unchanged. `HDEMBREE_SAMPLES_TO_CONVERGENCE` can request higher quality;
such overrides are outside the measured budget.

A separate single-thread native profile uses the same 109 source bodies and
placements for both implementations, with a warm adapter cache. Wrappers
count and time native calls without changing their arguments or results.
The comparison worker drops from 224 to 109 Bridge.Build calls (0.971 to
0.452 s), and from 115 to 109 world transforms. Its total native time drops
from 4.477 to 3.925 s; the caller-observed comparison drops from 4.934 to
4.578 s. The exported report and measurements remain byte-identical.

The export worker already rebuilds and tessellates once per body: 109 Build
calls and 109 Tessellate calls (0.612 s for tessellation in the baseline).
Each comparison opens one stage, with no per-body stage opens or comparison
tessellation. Those operations stay unchanged. The B7 snapshots now share a
transform cache within each snapshot, clearing it after muting; an unused
intermediate flatten is removed. The determinism row does no IFC export,
Build, tessellation, measurement or rendering in its second root.

## Byte preservation and source refresh

All four own layers (`exact.usda`, `twins.usda`, `presentation.usda` and
`cameras.usda`), the exact-export report, measurements and findings match
v0.1.1 byte for byte. Every committed PNG is retained.

The required data-centre v0.4.5 pin includes the v0.4.4 clash-mesh update:
two source meshes have different tessellation, and five source meshes gain
body/derived tolerance metadata. These superseded source meshes remain in
the flattened stage, so the full crate cannot retain the old normalized SHA
while honestly composing that pin. Only the crate and result README's source
pin are refreshed. The normalized crate changes from
`f85077ffdff1c99fcaa4d5ed46b8eed7e48c34268e795710be4d05592d795d00` to
`4079650453d67ea1f16c962edd932a852aef37e5cc4b6624ec4a110682f08a1a`.
Its normalized text diff is exactly the upstream geometry-layer diff; Route S
geometry and measurements are unchanged. Normalization remains `sdf-usda-v1`.

## Deviations

- Retaining the original whole-crate SHA and adopting the required source pin
  are incompatible. The source refresh described above changes the crate and
  its source-pin README; all own layers, measured values and committed images
  retain their bytes.
- Rendering was the dominant fresh-root cost on this runtime. Fresh previews
  now default to 8 samples per pixel, while retaining size, cameras, purposes,
  all nine views and geometry. Users can override the sample count.
- Toolchain v0.3.5 had no release tag at the start. The pin is v0.3.4 and
  `budgetSeconds: 120` is declared and enforced by the benchmark. The shared
  v0.3.4 harness still has a fixed 180-second timeout; manifest-driven harness
  enforcement is not proven until v0.3.5. The gate's fresh publication also
  has a 180-second timeout and the re-flattening child has 60 seconds.
- One stock Embree child exited with signal 11 in the initial S28 run. The
  isolated stock-render probe and complete final gate passed afterward;
  no retry was added to the gate. The cause of that native crash remains **NOT PROVEN**.
- One offline Nix attempt with direct local overrides failed resolving the
  nested aeco-toolchain revision (HTTP 404). It was not retried. Nix execution,
  Linux execution and wheel installation remain **NOT PROVEN**.
- Route S owns no schema. S06–S19 are inapplicable in the standard lint;
  explicit registry, applicability, plugin, seeded-defect and native checks
  cover the core mark and UsdSolid geometry interfaces.
- The fixture supplies single-material Qto Width values and DC_Section OD,
  not compound layer sets or a complete IFC type schedule. Compound and
  type-schedule equivalence remain **NOT PROVEN**. Volume/area comparisons
  use dimensioned engineering budgets, not a general Hausdorff-error proof.
- Guide images use the legacy Embree delegate for the pictured non-instanced
  cutaway. Guide rendering of mapped occurrences remains **NOT PROVEN**.
  Plugin-free publication and B7 rendering use the default imaging path.

## What remains

Driver-to-solid evaluation, exact sync read-back, direct exact-body imaging,
compound measurement definitions and the two-engine clash comparison remain
outside this release. Publication determinism is tested from authored layers;
a second independent IFC/kernel export is no longer part of that gate row.
