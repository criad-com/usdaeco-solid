# Changelog

## 0.1.4

- public names → github.com/criad-com in flake inputs and documentation.
- Pin toolchain v0.3.8 for the updated public-name and sanitization checks.
  Keep all other dependency pins and requirement ranges unchanged.
- Update the example manifest's toolchain pin; preserve committed results,
  findings and renders: all seven result files retain their 6,178,041 bytes.
- Verify 50 checks, 0 failed, 0 not run; 21 tests passed; structure S01–S29
  passes under v0.3.8, including S05 public names and S25 sanitization.
  No previous-organization public references remain.
- Deviation: Nix is not proven. The single offline flake-check attempt with
  exact local-source overrides failed during axis input resolution because
  Nix rejected the macOS temporary-directory symlink; no retry.

## 0.1.3

- Re-pin to train aeco-0.7.0: toolchain v0.3.4 → v0.3.6, above the
  v0.3.5 floor. Keep all other direct pins and requirement ranges unchanged.
- Verify 50 checks, 0 failed, 0 not run; 21 tests passed; structure S01–S29
  passes 29/0, including a second layout without sibling checkouts.
- Fresh publication takes 86.785 s; independent re-flattening takes 3.865 s.
  The crate, four archived layers and result README match committed bytes.
  Retain all seven result files (6,178,041 bytes) and all committed renders.
- Deviation: the new toolchain's runtime source alias exposed a relocation
  defect. Resolve external sublayers through the alias before its temporary
  directory disappears; reject incomplete composition before validation.
  The regression verifies both direct and aliased sources in a fresh process
  after deleting the original example directory. No geometry changes.
- Toolchain v0.3.5 introduced canonical prototype names for comparisons;
  v0.3.6 verifies the existing legacy manifest hash without republishing.
  Fresh PNG bytes vary and are not compared by S28; the committed images stay.
- Nix remains not proven: one offline attempt could not resolve the nested
  flake-utils input from the configured mirror; no retry. The 120-second
  example budget is unchanged; the gate's reused publication does not invoke
  harness timing enforcement (`execute=False`).

## 0.1.2

- Publish once in a fresh root, then independently re-flatten the authored layers
  in another process and root; reuse that publication for the remaining gate rows.
- Reuse built world-space bodies for measurements and clearance pairs, with one
  transform cache per stage; keep tessellation and engineering budgets unchanged.
- Default fresh CPU previews to 8 samples per pixel and declare a 120-second
  example budget. Add a repeatable fresh-root benchmark for one and two threads.
- Pin axis v0.1.2, data centre v0.4.5, IFC v0.2.0 and toolchain v0.3.4.
  Toolchain v0.3.5 was not released at the start; its budget enforcement is pending.

- Refresh only the crate and its source-pin README for the required upstream
  clash-mesh update; exact bodies, twins, measurements and all committed images
  retain their bytes. See the explicit byte-preservation deviation.

## 0.1.1

- Allocate mapped instances in sorted occurrence order before publishing, so
  interchangeable prototypes cannot change the normalized flattened crate.
- Gate two complete publications in separate temporary roots and processes,
  with separate native caches, and compare their normalized crates byte for byte.
- Add a seeded regression proving prototype reference drift and preserving
  instance sharing, composed geometry and transforms after the fix.
- Refresh the published crate; exact measurements and authored layers are unchanged.

## 0.1.0

- Add exact measurement, consumer-controlled tessellation and twin comparison.
- Register five Python UsdValidation rules with seeded-defect tests.
- Publish the 109-product office-wing exact study, material subsets, mapped
  prototypes, three clearance cases, guide renders and a self-contained crate.
- Preserve ordinary USD composition and proxy rendering when exact data is muted.
