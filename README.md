# usdaeco-solid — exact bodies with ordinary USD proxy twins

## Use case

Measure exported solids and decide clearances smaller than a mesh's uncertainty.
Route S carries the evaluated BRep in USD, beside a renderable Mesh twin. The
[use-case walkthrough](docs/usecase.md) explains the office-wing example and
how this complements the driver-based route.

## The schema on an index card

This repository defines **no new schema or kind API**. It consumes UsdSolid
and the core's existing `AecoDerivedGeometryAPI`.

| Representation | USD carrier | Purpose | Correlation |
|---|---|---|---|
| Exact body | `BrepArray BodyExact` | render | `approx = exact`, kernel tolerance, producer stamp |
| Tessellation | `Mesh Body` | proxy | `aeco:derived:from` targets BodyExact; deflection and source fingerprint |
| Edge display | `BasisCurves Edges` | guide | source link, discretization tolerance |

The properties are `aeco:derived:{source,role,approx,stamp,tolerance,from}`.
Exact geometry stays in UsdSolid's namespaces. Element identity stays on the
existing element. Five [Python validators](usdAecoSolidValidators/) check
tolerance, correlation, freshness, solid validity and the proxy twin.

## The example

The pinned `clash` variant supplies 2,980 elements. A documented footprint
census selects 109 office-wing products across both floors, including 42 walls
and 6 pipes. All 109 become valid exact bodies and all 109 twins pass the
volume/area comparison. The measured pipe-to-tray clearance is **5.000 mm**.

![Exact edge guides over proxy twins](examples/datacentre/renders/wireframe-overview.png)

Open `examples/datacentre/result/example.usdc` in any USD viewer. It is
flattened, self-contained and retains the BrepArray prims, their fallbacks,
material subsets and Mesh twins. `result/vanilla.png` is rendered without
family plugins. The original overlays remain under `result/layers/`.
Before flattening, the publisher recreates mapped instances in sorted occurrence
order. This stabilizes prototype references while retaining instance sharing.

## Build and check

Use the configured family Python with usd-core, IfcOpenShell 0.8.5, numpy,
PyYAML and pytest. No installation or setuptools is needed for source checks.
Set these variables to your checkouts and the built optional runtime.
Source checks select the runtime's matching stock OpenUSD 0.26.11 renderer
automatically; `USDRECORD` can override that choice. Fresh previews default to
8 Embree samples per pixel; `HDEMBREE_SAMPLES_TO_CONVERGENCE` can override it:

```sh
export TOOLCHAIN_DIR="$(pwd)/../usdaeco-toolchain"
export AECO_CORE_ROOT="$(pwd)/../usdaeco-core"
export AECO_AXIS_ROOT="$(pwd)/../usdaeco-axis"
export AECO_IFC_ROOT="$(pwd)/../usdaeco-ifc"
export AECO_DATACENTRE_ROOT="$(pwd)/../usdaeco-datacentre"
export USD_SOLID_OCCT_RUNTIME="$(pwd)/../usdSolidOcct/result-runtime"
export PYTHONDONTWRITEBYTECODE=1
export CORE_PLUGIN_DIR="$AECO_CORE_ROOT/usdAeco"
export PXR_PLUGINPATH_NAME="$CORE_PLUGIN_DIR"
env -u PYTHONPATH PYTHONPATH="$AECO_CORE_ROOT:$PWD" python check.py
env -u PYTHONPATH python -m pytest -q
env -u PYTHONPATH python examples/datacentre/run.py
env -u PYTHONPATH python tools/benchmark_example.py --threads 1 2
```

`AECO_IFC_ROOT` must contain version 0.2.2. The native runtime has a different
Python/USD ABI: the tools launch it in a separate process. A C++ compiler
builds a small adapter against its existing shared libraries; no dependencies
are installed. Set `AECO_EXACT_CACHE` to a writable directory when using an
immutable IFC package. An absent runtime produces explicit NOT RUN rows;
a present but broken runtime fails.
The gate publishes once in an empty temporary source root and native cache.
It omits the generated `inputs/source` alias from that copy; the harness
recreates the alias against the selected data-centre source.
It then re-flattens the already-authored layers in a second process and root,
comparing normalized crate bytes with the unchanged `sdf-usda-v1` contract.
The harness and validator rows reuse that fresh publication. This tests
publication determinism; a second IFC/kernel execution is no longer part of
that row. Use the exact releases listed below for source checks; newer sibling checkouts may have different example data.

```sh
env -u PYTHONPATH python tools/aeco_solid.py measure examples/datacentre/result/example.usdc
env -u PYTHONPATH python tools/aeco_solid.py compare examples/datacentre/result/example.usdc
env -u PYTHONPATH python tools/aeco_solid.py tessellate examples/datacentre/result/example.usdc --out twins.usda --deflection 0.0001 --edges
nix flake check
```

Installed entry point: `aeco-solid`. The source module also supports
`python -m usdaeco_solid` when the package is on the import path.
Flake inputs use public repository names. Deployment mirrors are supplied
outside this repository through the toolchain's registry-file wrapper or
`--override-input`; see the [toolchain convention](https://github.com/criad-com/usdaeco-toolchain/blob/v0.3.10/docs/repo-conventions.md).
Both native kits are recursive inputs to supply the runtime package. Their
family inputs follow the selected toolchain and usdSolid releases, including
build toolchain v0.4.0. Core, axis, data centre and IFC remain source inputs.

For suite composition, set `AECO_STUDY_ROOT=/Studies/solid` before calling the
example hook or running the example. Exact prototypes and materials then live
at `/Studies/solid/ExactPrototypes` and `/Studies/solid/ExactMaterials`; exact
bodies and twins keep their element paths. Clearance labels share the study
scope, and finalized example cameras use `/Renders/solid/<camera>`. The study
ancestors are plain Scopes. No catalog is added: the project keeps its catalog.

The default `/` preserves the committed example, including the historical
`/__ExactPrototypes` name. `scope_export(output, root)` in
`usdaeco_solid.paths` also scopes writable IFC-exported `exact.usda` and
`twins.usda` layers for callers that select their own elements. It updates
bindings, internal references, shader connections and metadata paths together.
Each library exports its own materials; a new solid tessellation copies its
source material into solid's root. Persisted solid metadata takes precedence
over the environment, including after flattening. Measurements and validators
discover exact bodies and their relationships directly from stage data.

The standalone runner finalizes camera namespaces after rendering: pinned
toolchain v0.3.10 requires direct `/Renders` children in its temporary render
inputs. The suite can supply `/Renders/solid` cameras to the hook directly.
Set `AECO_DATACENTRE_FULL_ROOT` to the v0.5.2 checkout for the additional
full-stage catalog test; the example itself remains pinned to v0.4.8.

## Family

| Dependency | Supported range | Tested target |
|---|---|---|
| core | >=0.9,<1.0 | v0.9.4 |
| IFC integration | >=0.2,<0.3 | v0.2.2 |
| UsdSolid / usdSolidOcct | >=0.1,<0.2 | v0.1.4 / v0.1.3 |
| toolchain | example/validation kit | v0.3.10 |
| data centre | pinned example source | v0.4.8, clash |
| axis | family compatibility pin | v0.1.4 |

The exact exporter belongs to `usdaeco-ifc`; its default converter remains
unchanged. This library consumes exported results and adds no editing driver.

## Layout

`tools/usdaeco_solid/` contains the commands and native worker;
`usdAecoSolidValidators/` is the Python UsdValidation plugin;
`usdAecoSolid/` holds user documentation and the minimal example;
`testenv/` holds seeded defects and kernel checks;
`examples/datacentre/` contains the input hook, findings, renders and result.

## Status

Version 0.1.6: **50 checks, 0 failed, 0 not run; 34 tests passed**.
Configurable study roots preserve the default example bytes; the scoped crate
contains only the project, Studies and Renders at its root. See
[stage-tidiness acceptance and deviations](docs/stage-tidiness.md).
Version 0.1.5: **50 checks, 0 failed, 0 not run; 23 tests passed**.
The public re-pin reproduces the crate and all four authored layers byte for
byte (6,061,018 bytes), retaining all ten committed PNGs. Nine fresh renders
are nonblank. The v0.1.5 [acceptance and deviations](docs/public-repin.md) record
the pins, source revisions and render evidence. The native gate uses a cached
bridge v0.1.3 runtime paired with schema/validators v0.1.0; the complete newly
pinned native build remains unproven. The single offline Nix attempt resolves
the input graph and evaluates the outputs, but does not complete the build.
Version 0.1.2 fresh publication: **85.727 s with one USD thread; 68.185 s with two**,
including fixture generation, native compilation and nine 8-sample renders.
The historical v0.1.2 source re-pin refreshed the crate and its source-pin README;
exact layers, measurements and all committed images retain their bytes.
Publication is reproducible from relocated authored layers.
The example declares `budgetSeconds: 120`; the benchmark enforces it.
Pinned toolchain v0.3.10 supports manifest-driven harness budgets;
this gate reuses its fresh publication with `execute=False`.
Exact export, measurement, tessellation, material subsets,
mapped prototypes and B7 composition are exercised on the pinned example.
See [release notes](CHANGELOG.md) and [historical v0.1.2 acceptance and deviations](docs/acceptance.md)
for check totals, source-data limitations and the Nix attempt. Stage-side driver evaluation,
exact sync read-back and direct exact-body rendering remain deferred.

## Licence

MIT. See [LICENSE](LICENSE). Runtime dependencies keep their own licences:
OpenUSD and the UsdSolid fork retain their upstream licence; IfcOpenShell is
LGPL-3.0; OCCT is LGPL-2.1 with its exception and is dynamically linked only.
