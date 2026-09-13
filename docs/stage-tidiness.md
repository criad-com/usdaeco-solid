# Stage-tidiness verification — v0.1.6

The [machine-readable receipt](stage-tidiness.json) records the measured results.

`AECO_STUDY_ROOT=/Studies/solid` puts exact prototypes, materials and clearance
annotations beneath plain Scope ancestors. Exact bodies and proxy twins stay
under their elements. The project retains its own catalog. Finalized standalone
cameras use `/Renders/solid/<camera>`.

The adapter processes only writable IFC-exported layers. Internal prototype
references, material bindings, shader connections and custom-data paths follow
the resources. External asset references retain their asset-local paths. Layer
metadata records the root; a prim marker preserves discovery through flattening.
A solid tessellation of a clash exact body copies its materials to solid's root.

USD-generated flattened prototypes are canonicalized with the existing toolchain
helper before moving beneath the scoped `ExactPrototypes` container. This keeps
the crate root tidy and independent re-flattening reproducible.

The default `/` is a no-op on exported layers, preserving the historical
`/__ExactPrototypes` spelling and committed example bytes. Dependency pins,
requirement ranges and geometry producer stamps are unchanged.

| Acceptance | Evidence |
|---|---|
| Export adaptation | Pinned 109-body export at `/Studies/solid` and `/Analysis/Office/Exact`; instance counts, material partitions, shader connections and proxy/source links preserved |
| Live hook | Data centre v0.4.8 clash; all 109 exact bodies and twin comparisons pass under `/Studies/solid` |
| Project catalog | Compose scoped exports over data centre v0.5.2 `dist/full/dc.usda`; only project and Studies roots, unchanged project catalog, no `/_TypeCatalog` |
| Native consumer | Tessellate a mapped peer exact body into solid-owned materials; compare and validate reopened scoped data |
| Root discovery | Persisted layer data and flattened prim marker override a different environment setting |
| Scoped standalone publication | 109 bodies, 4 instance prototypes, 9 nonblank renders; root prims are project, Studies and Renders; 4 cameras beneath `/Renders/solid` |
| Scoped reproducibility | Independent re-flattening matches after canonicalizing and nesting USD-generated prototypes |
| Input validation | Reject empty, relative, property and variant-selection roots |
| Default publication | Fresh crate and four archived layers byte-identical (6,061,018 bytes); all committed example artifacts retained |
| Source gate and pytest | 50 checks, 0 failed, 0 not run; 34 passed, 0 skipped; S01–S29 green |
| Nix | One offline evaluation attempt, exit 1: native dependency flake requires `.rev`, absent from local path overrides; no retry |

## Reproduction

Use the README environment with the exact dependency releases listed there.
Set `AECO_DATACENTRE_FULL_ROOT` to a read-only data-centre v0.5.2 checkout.
Run `env -u PYTHONPATH python check.py` and `env -u PYTHONPATH python -m pytest -q`.
For a scoped standalone result, run the example with
`AECO_STUDY_ROOT=/Studies/solid`; use a disposable checkout when publishing it.
The committed baseline describes the default root.

## Deviations

- The pinned IFC exporter has fixed output paths. Solid adapts its writable
  exports locally instead of changing the dependency or its release pin.
- Toolchain v0.3.10 discovers cameras only as direct children of `/Renders`.
  The standalone runner renders with those transient inputs, then namespaces
  cameras in the final stage, archived camera layer and flattened crate.
  The suite hook accepts namespaced input cameras directly.
- The full v0.5.2 test proves catalog composition. Geometry generation and the
  live exact hook remain on the example's v0.4.8 clash source; the full variant
  does not contain all planted clash products.
- Native checks retain the cached bridge v0.1.3 runtime with schema/validators
  v0.1.0 used in the preceding release. A complete newly pinned native build
  remains unproven.

The single Nix invocation used `flake check --offline --no-build --no-write-lock-file`
with the preceding release's exact sources as local path overrides. Evaluation
stopped in a native dependency's revision receipt; no build or public fetch was
proven and no lockfile was written.
