# Exact office-wing study

Open `result/example.usdc` with stock USD. Enable guide purpose to display
edge curves and the measured clearance label; proxy purpose displays twins.
`result/vanilla.png` proves a plugin-free view. Mute `presentation.usda` when
composing the own layers to inspect all 109 office products and the full source.

With the README environment configured:

```sh
env -u PYTHONPATH python examples/datacentre/run.py
env -u PYTHONPATH python examples/datacentre/run.py --publish
```

`AECO_DATACENTRE_ROOT` supplies the pinned clash stage and its manifest.
`inputs/generate.py` builds IFC into this checkout's ignored work directory;
`inputs/cameras.usda` fixes the four views. Findings are compared with
`expected/findings.json`; publication never updates that expectation.
Before flattening, mapped instances are recreated in sorted occurrence order
so prototype allocation cannot swap references between equivalent prototypes.
The root gate publishes once in a fresh temporary root, then re-flattens its
authored layers in a second process and root. The complete normalized crates
are compared, including every opinion and prototype reference. That same fresh
publication supplies the harness and validation rows.
The gate and benchmark omit the generated `inputs/source` alias when copying
the checkout; the harness recreates it for each fresh run. This also permits
running the gate after `--publish` has populated the working example.

Fresh renders default to 8 Embree samples per pixel. The manifest declares a
120-second budget; `tools/benchmark_example.py --threads 1 2` measures and
enforces it with empty source roots and native caches. The pinned v0.3.10
harness supports this manifest budget; the gate reuses its fresh publication
with `execute=False`, so that harness row does not enforce elapsed time.
The cohort, measurement definitions and source-data limits are described in
[the use case](../../docs/usecase.md).
