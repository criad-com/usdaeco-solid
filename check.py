#!/usr/bin/env python3
"""Run Route S acceptance and print N checks, M failed."""
import json
import os
from pathlib import Path
import re
import hashlib
import shutil
import subprocess
import sys
import tempfile
import time
import bootstrap
from usdaeco_check import Report, registry_probe, can_apply
from usdaeco_check.structure import check_structure
from usdaeco_check.example import check_example
from usdaeco_check.example_result import normalized_layer, render_vanilla
from usdaeco_check.images import image_info
from usdaeco_ifc.exact_runtime import runtime_paths, RuntimeUnavailable, run_native

ROOT = Path(__file__).resolve().parent
EXAMPLE = ROOT / 'examples/datacentre'


def double_publication():
    """Publish once from scratch, then re-flatten the authored layers elsewhere."""
    from usdaeco_solid.publication import relocate_composition
    environment = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
    for variable, sibling in (('AECO_CORE_ROOT', 'usdaeco-core'),
                              ('AECO_IFC_ROOT', 'usdaeco-ifc'),
                              ('TOOLCHAIN_DIR', 'usdaeco-toolchain'),
                              ('AECO_DATACENTRE_ROOT', 'usdaeco-datacentre')):
        environment[variable] = str(Path(environment.get(variable, ROOT.parent / sibling)).resolve())
    for variable in ('CORE_PLUGIN_DIR', 'USD_SOLID_OCCT_RUNTIME', 'USDRECORD'):
        if environment.get(variable):
            environment[variable] = str(Path(environment[variable]).resolve())
    with tempfile.TemporaryDirectory(prefix='solid-publication-') as first, \
         tempfile.TemporaryDirectory(prefix='solid-reflatten-') as second:
        root = Path(first) / 'source'
        shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(
            '.git', '.work', 'out', 'result', 'result-*', 'renders',
            '__pycache__', '.pytest_cache', '*.egg-info', '*.dist-info', 'STEERING.md'))
        child = dict(environment, AECO_EXACT_CACHE=str(root / '.work/native'),
                     PYTHONHASHSEED='1', PYTHONDONTWRITEBYTECODE='1')
        print('== stage: fresh publication with empty native cache', flush=True)
        start = time.perf_counter()
        process = subprocess.run([sys.executable, 'examples/datacentre/run.py', '--publish'],
                                 cwd=root, env=child, capture_output=True, text=True, timeout=180)
        elapsed = time.perf_counter() - start
        if process.returncode:
            raise RuntimeError('Fresh publication failed:\n' + (process.stdout + process.stderr)[-6000:])
        example = root / 'examples/datacentre'
        manifest = json.loads((example / 'manifest.json').read_text())
        if manifest['source']['mode'] != 'pinned':
            raise ValueError('Publication determinism requires the pinned data-centre source')
        original = normalized_layer(example / 'result/example.usdc')
        print('== stage: re-flatten authored layers in a second root', flush=True)
        child['PYTHONHASHSEED'] = '2'
        command = ('import bootstrap; from usdaeco_solid.publication import reflatten; '
                   'import sys; reflatten(sys.argv[1], sys.argv[2])')
        start = time.perf_counter()
        process = subprocess.run([sys.executable, '-c', command, str(example / 'out/example.usda'), second],
                                 cwd=root, env=child, capture_output=True, text=True, timeout=60)
        reflatten_seconds = time.perf_counter() - start
        if process.returncode:
            raise RuntimeError('Re-flattening failed:\n' + (process.stdout + process.stderr)[-6000:])
        repeated = normalized_layer(Path(second) / 'example.usdc')
        records = [dict(normalizedSha256=hashlib.sha256(crate).hexdigest(),
                        normalizedBytes=len(crate), primCount=manifest['result']['prim_count'],
                        seconds=round(seconds, 3), operation=operation)
                   for crate, seconds, operation in ((original, elapsed, 'freshPublication'),
                                                     (repeated, reflatten_seconds, 'reflattenOwnLayers'))]
        if original != repeated:
            raise ValueError('Publications differ after sdf-usda-v1 normalization: ' + json.dumps(records))
        # Reuse this fresh run for the harness, validation and B7 rows. The
        # first temporary root may now go away; only pinned source arcs remain.
        if (EXAMPLE / 'out').exists():
            shutil.rmtree(EXAMPLE / 'out')
        shutil.copytree(example / 'out', EXAMPLE / 'out')
        (EXAMPLE / 'out/example.usda').unlink()
        relocate_composition(example / 'out/example.usda', EXAMPLE / 'out/example.usda')
        (ROOT / '.work').mkdir(exist_ok=True)
        shutil.copyfile(root / '.work/muted.usdc', ROOT / '.work/muted.usdc')
        return records


def main():
    report = Report()
    evidence = {}
    print('== stage: required core and solid validators', flush=True)
    from pxr import Plug, Usd, UsdValidation
    core = Path(os.environ.get('AECO_CORE_ROOT', ROOT.parent / 'usdaeco-core'))
    Plug.Registry().RegisterPlugins(os.environ.get('CORE_PLUGIN_DIR', str(core / 'out/plugins/usdAeco/resources')))
    Plug.Registry().RegisterPlugins(str(core / 'usdAecoValidators'))
    Plug.Registry().RegisterPlugins(str(ROOT / 'usdAecoSolidValidators'))
    import usdAecoValidators  # Required: an import failure must fail loudly.
    import usdAecoSolidValidators
    registry = UsdValidation.ValidationRegistry()
    groups = {}
    for keyword, count in (('UsdAecoValidators', 8), ('UsdAecoSolidValidators', 5)):
        metadata = registry.GetValidatorMetadataForKeyword(keyword)
        rules = registry.GetOrLoadValidatorsByName([m.name for m in metadata])
        if len(metadata) != count or len(rules) != count or not all(rules):
            raise RuntimeError(f'{keyword}: all {count} validators must load')
        groups[keyword] = rules
        report.check(keyword + ' loaded', True, str(count))
    report.add(registry_probe(['AecoDerivedGeometryAPI', 'AecoElementAPI'], ['AecoPort']))
    report.add(can_apply([('Mesh', 'AecoDerivedGeometryAPI', True), ('Material', 'AecoDerivedGeometryAPI', False)]))
    report.check('Route S adds no geometry or kind schema', not list(ROOT.glob('*/schema.usda')))
    print('== stage: structure S01-S29', flush=True)
    structure = check_structure(ROOT)
    for result in structure:
        report.add(result)
    evidence['structure'] = dict(checks=len(structure), failed=sum(not r.ok for r in structure),
                                 inapplicable=sum('not applicable' in r.detail for r in structure))
    try:
        runtime_paths()
        native = True
    except RuntimeUnavailable as error:
        native = False
        report.not_run('exact runtime', str(error))
    print('== stage: seeded defects and kernel tools', flush=True)
    test_environment = {k:v for k,v in os.environ.items() if k != 'PYTHONPATH'}
    if not native:
        test_environment.pop('USD_SOLID_OCCT_RUNTIME', None)
    process = subprocess.run([sys.executable, '-m', 'pytest', '-q', '--tb=short', '-rs'], cwd=ROOT,
                             env=test_environment,
                             capture_output=True, text=True, timeout=180)
    print(process.stdout)
    if process.returncode:
        print(process.stderr)
    report.check('pytest', process.returncode == 0)
    passed = re.search(r'(\d+) passed', process.stdout)
    skipped = re.search(r'(\d+) skipped', process.stdout)
    evidence['pytest'] = int(passed.group(1)) if passed else 0
    evidence['skipped'] = int(skipped.group(1)) if skipped else 0
    if native:
        report.check('all native tests executed', evidence['pytest'] >= 15 and evidence['skipped'] == 0)
        published = False
        try:
            evidence['doublePublication'] = double_publication()
            published = True
            report.check('publication determinism from authored layers', True, json.dumps(evidence['doublePublication']))
        except Exception as error:
            report.check('publication determinism from authored layers', False, str(error))
        print('== stage: fresh pinned clash example and publication parity', flush=True)
        if not published:
            report.check('fresh example parity', False, 'No successful fresh publication; stale out/ is not evidence')
        if published and report.add(check_example(EXAMPLE, execute=False)):
            evidence['findings'] = findings = json.loads((EXAMPLE / 'out/findings.json').read_text())
            rows = {r['name']: r for r in findings}
            bodies = rows['ExactOfficeBodies']
            measures = rows['Measurements']
            report.check('every meshable office product exact', bodies['selected'] == bodies['exact'] > 0 and bodies['failed'] == 0,
                         f"{bodies['exact']}/{bodies['selected']} across {len(bodies['perClass'])} IFC classes")
            report.check('wall thickness within 1e-6 m', measures['walls'] > 0 and measures['maxThicknessError'] <= 1e-6, str(measures['maxThicknessError']))
            report.check('pipe OD within 1e-6 m', measures['pipes'] > 0 and measures['maxOdError'] <= 1e-6, str(measures['maxOdError']))
            report.check('every twin volume and area within budgets', measures['twinsWithinTolerance'] == measures['twins'] == bodies['exact'])
            mute = rows['B7Mute']
            report.check('B7 mute preserves all twins and transforms', mute['samePointsAndTransforms'] and mute['compositionErrors'] == 0 and mute['twins'] == bodies['exact'])
            render_vanilla(ROOT / '.work/muted.usdc', EXAMPLE / 'inputs/cameras.usda', ROOT / '.work/muted.png')
            image = image_info(ROOT / '.work/muted.png')
            evidence['mutedRender'] = image
            report.check('B7 muted stage renders without plugins', bool(image), f"{image['width']}x{image['height']}, {image['bytes']} bytes")
            cases = rows['ExactClearances']['pairs']
            near = next(r for r in cases if r['id'] == 'pipe.clash.near')
            report.check('exact 5 mm clearance', abs(near['distance'] - .005) <= 1e-6 and near['commonVolume'] == 0, str(near['distance']))
            stage = Usd.Stage.Open(str(EXAMPLE / 'out/example.usda'))
            if not stage or stage.GetCompositionErrors():
                raise RuntimeError('Fresh example must compose completely before validation')
            evidence['validation'] = {}
            for keyword, rules in groups.items():
                errors = list(UsdValidation.ValidationContext(rules).Validate(stage))
                counts = dict(validators=len(rules), errors=sum(e.GetType() == UsdValidation.ValidationErrorType.Error for e in errors),
                              warnings=sum(e.GetType() == UsdValidation.ValidationErrorType.Warn for e in errors))
                evidence['validation'][keyword] = counts
                report.check(keyword + ' example validation', counts['errors'] == 0, json.dumps(counts))
                for error in errors:
                    if error.GetType() == UsdValidation.ValidationErrorType.Error:
                        print(error.GetName(), error.GetMessage())
            result = json.loads(run_native(ROOT / 'tools/usdaeco_solid/native_acceptance.py', EXAMPLE / 'out/example.usda').splitlines()[-1])
            evidence['native'] = result
            report.check('all native UsdSolid validators clean', result['validators'] == 20 and not result['findings'], json.dumps(result['findings']))
            report.check('material face and triangle partitions valid', result['materialBodies'] == bodies['exact'] and result['materialPartitionsValid'])
            report.check('mapped representations are shared instances', result['mappedProducts'] == rows['RepresentationReuse']['mappedProducts'] and result['prototypes'] == rows['RepresentationReuse']['prototypes'])
    else:
        for row in ('native tests', 'publication determinism from authored layers', 'fresh exact example', 'measurements and comparison', 'B7 exact-layer mute', 'native solid validity'):
            report.not_run(row, 'Set USD_SOLID_OCCT_RUNTIME to execute this row')
    evidence.update(checks=len(report.results), failed=report.failed, notRun=report.not_run_count)
    (ROOT / '.work').mkdir(exist_ok=True)
    (ROOT / '.work/check.json').write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n')
    return report.finish()


if __name__ == '__main__':
    raise SystemExit(main())
