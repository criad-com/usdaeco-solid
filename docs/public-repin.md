# Public re-pin verification — v0.1.5

All seven direct family inputs select published release tags. Checked source
revisions are recorded in `dependencies.json`; they identify the source used
for verification, while public orphan releases resolve by tag. Requirement
ranges remain unchanged. The [machine-readable receipt](public-repin.json)
contains gate results, artifact hashes and fresh-render measurements.

| Input | Selected tag |
|---|---|
| usdaeco-toolchain | v0.3.10 |
| usdaeco-core | v0.9.4 |
| usdaeco-axis | v0.1.4 |
| usdaeco-datacentre | v0.4.8 |
| usdaeco-ifc | v0.2.2 |
| usdSolid | v0.1.4 |
| usdSolidOcct | v0.1.3 |

Both native kits follow `toolchain` and `toolchain/aeco-toolchain`; the bridge
also follows the top-level `usdSolid`. Thus their older nested family hash refs
and tags are replaced in the resolved graph. The two remaining family inputs
are the toolchain's published build input v0.4.0 and core test fixture v0.9.2,
documented in the toolchain's
[tag verification](https://github.com/criad-com/usdaeco-toolchain/blob/v0.3.10/docs/tag-pin-verification.md).
Non-family upstream revision pins are unchanged.

| Acceptance | Measured result |
|---|---|
| Source gate | 50 checks, 0 failed, 0 not run |
| Pytest inside the gate | 23 passed, 0 skipped |
| Structure lint | S01–S29: 29 checks, 0 failed |
| Required core / solid Python validators | 8 / 5 loaded; zero errors |
| Native UsdSolid validators | 20 loaded; zero findings |
| Exact bodies / twin comparisons | 109 / 109 pass; 17 IFC classes |
| Wall thickness / pipe OD | Maximum errors 2.831068712794149e-15 m / 0 m |
| Measured clearance | 0.005000000000000782 m; zero common volume |
| B7 mute | 109 unchanged twins and transforms; zero composition errors |
| Fresh publication / independent re-flattening | 71.334 s / 2.016 s; identical normalized bytes |
| Relocated plugin-free crate | 13,145 prims; zero composition errors |
| Unchanged crate and four own layers | 5 files; 6,061,018 bytes |
| Committed result inventory | 7 files; 6,178,041 bytes |
| Fresh views / retained committed PNGs | 9 nonblank / 10 byte-identical |
| Largest fresh PNG | 175,362 bytes; all views 1280 × 800 |
| Final exact-source metadata and registry smoke | 7 source versions, 3 package versions, 8 core validators |
| Publication sweep | 60 files; zero findings |
| Nix | One offline attempt; input graph and outputs evaluate; build unproven |

## Publication comparison

Run `examples/datacentre/run.py --publish` with the README environment and the
selected sources. The crate SHA-256 remains
`1f2ec7329a4b293667217f6f68863d5dcd5d181d35e48ddd4178cf2901b1384d`.
All four own layers, findings and source hashes match the preceding release.
Only the result README's source pin changes within `result/`.

The manifest now records the current pins and source revisions. Republishing
also refreshes the normalized crate digest to
`026239a6b30f7a5e429719f54fe6a58b8f6187d5e78d306ee8724bd32397c2cb`.
The crate itself is byte-identical: this replaces its legacy digest with the
toolchain's existing canonical prototype naming, introduced in v0.3.5. The
normalization label remains `sdf-usda-v1`.

Fresh PNG bytes vary between sampled renders. All nine fresh views pass the
size and nonblank checks; their observed hashes are recorded separately in
the receipt. The original nine example images and documentation thumbnail
retain their bytes. The committed manifest describes those retained images.

The data-centre v0.4.6–v0.4.8 changelogs preserve published USD; the clash
source, specification and IFC geometry-generation code match v0.4.5.
Generator package-version and integration-loading metadata changed.
IFC v0.2.1–v0.2.2 changes pins and
provenance; the exact exporter remains unchanged from v0.2.0. No upstream
geometry behavior change was found. Producer stamps remain at their existing
algorithm versions; the source package version is 0.1.5.

The gate and benchmark now omit the generated `inputs/source` symlink when
copying a checkout. Previously, checking after publication followed that alias
and copied a dependency directory, which the harness rejected. Two regressions
cover existing and dangling aliases, and preserve ordinary source directories.

## Nix reproduction

Set the five family source variables from the README to exact release checkouts;
also set `USD_SOLID_SOURCE`, `USD_SOLID_OCCT_SOURCE` and `AECO_BUILD_TOOLCHAIN`
to the matching kit releases and build toolchain v0.4.0. For example, use
`git+file://$TOOLCHAIN_DIR?ref=refs/tags/v0.3.10` as a local tag override.
The invocation was:

```sh
nix flake check --offline --no-write-lock-file --max-jobs 0 \
  --option substituters '' --option builders '' \
  --override-input toolchain "git+file://$TOOLCHAIN_DIR?ref=refs/tags/v0.3.10" \
  --override-input core "git+file://$AECO_CORE_ROOT?ref=refs/tags/v0.9.4" \
  --override-input axis "git+file://$AECO_AXIS_ROOT?ref=refs/tags/v0.1.4" \
  --override-input datacentre "git+file://$AECO_DATACENTRE_ROOT?ref=refs/tags/v0.4.8" \
  --override-input ifc "git+file://$AECO_IFC_ROOT?ref=refs/tags/v0.2.2" \
  --override-input usdSolid "git+file://$USD_SOLID_SOURCE?ref=refs/tags/v0.1.4&shallow=1" \
  --override-input usdSolidOcct "git+file://$USD_SOLID_OCCT_SOURCE?ref=refs/tags/v0.1.3&shallow=1" \
  --override-input toolchain/aeco-toolchain "git+file://$AECO_BUILD_TOOLCHAIN?ref=refs/tags/v0.4.0&shallow=1" \
  --override-input toolchain/core "git+file://$AECO_CORE_ROOT?ref=refs/tags/v0.9.2"
```

All inputs resolved, including the native kits' family follows. The source
package, library check, development shell and example app evaluated for
aarch64-darwin. Nix requested 14 checks, then failed on the first required
codeless-core build because execution was disabled. Exit code: 1. No retry
or lockfile write occurred.

## Deviations

- Both native kits are recursive flake inputs, because their package outputs
  supply the runtime. Keeping them source-only would remove that build path.
- The native gate uses a cached bridge v0.1.3 paired with schema and validators
  v0.1.0. Kit receipts contain newer artifacts although their release prose
  still says native rebuilds are pending. A runtime combining both newly
  selected kit releases is not proven by these checks.
- The single Nix attempt disabled local jobs, remote builders and substitutes
  to avoid uncached build downloads. Output evaluation is proven; build
  completion and public fetch resolution remain for release verification.
- Sampled images retain the committed baseline after fresh-render validation.
  Historical v0.1.2 acceptance and performance receipts keep their original
  pins and measurements; they are not evidence for the current release.

Final metadata, structure and registry checks used exact tag exports after
shared source checkouts advanced. The consumed core/axis schema and core
validator payloads were verified unchanged; the gate's core plugin was v0.9.4.
