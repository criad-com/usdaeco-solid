#!/usr/bin/env python3
"""Measure complete publications with empty source roots and native caches."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bootstrap
from usdaeco_check.example_result import normalized_layer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--threads', type=int, nargs='+', default=[1, 2])
    parser.add_argument('--output', type=Path, default=ROOT / '.work/performance.json')
    args = parser.parse_args()
    if any(n < 1 for n in args.threads):
        parser.error('thread limits must be positive')
    environment = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
    for variable, sibling in (('AECO_CORE_ROOT', 'usdaeco-core'), ('AECO_IFC_ROOT', 'usdaeco-ifc'),
                              ('TOOLCHAIN_DIR', 'usdaeco-toolchain'), ('AECO_DATACENTRE_ROOT', 'usdaeco-datacentre')):
        environment[variable] = str(Path(environment.get(variable, ROOT.parent / sibling)).resolve())
    for variable in ('USDRECORD', 'CORE_PLUGIN_DIR', 'USD_SOLID_OCCT_RUNTIME'):
        if environment.get(variable):
            environment[variable] = str(Path(environment[variable]).resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for threads in args.threads:
        print(f'== stage: fresh publication, {threads} USD thread(s)', flush=True)
        with tempfile.TemporaryDirectory(prefix='solid-benchmark-') as temporary:
            root = Path(temporary) / 'source'
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(
                '.git', '.work', 'out', 'result', 'result-*', 'renders', '__pycache__',
                '.pytest_cache', '*.egg-info', '*.dist-info', 'STEERING.md'))
            child = dict(environment, PXR_WORK_THREAD_LIMIT=str(threads),
                         AECO_EXACT_CACHE=str(root / '.work/native'), PYTHONHASHSEED='1')
            start = time.perf_counter()
            with args.output.with_suffix(f'.{threads}.log').open('w') as log:
                result = subprocess.run([sys.executable, 'examples/datacentre/run.py', '--publish'],
                                        cwd=root, env=child, stdout=log, stderr=subprocess.STDOUT, timeout=600)
            seconds = time.perf_counter() - start
            if result.returncode:
                raise RuntimeError('Fresh publication failed; see the benchmark log')
            example = root / 'examples/datacentre'
            manifest = json.loads((example / 'manifest.json').read_text())
            if manifest['source']['mode'] != 'pinned':
                raise ValueError('Fresh-root timing requires the pinned source')
            record = dict(threads=threads, seconds=round(seconds, 3),
                          renderSamples=int(child['HDEMBREE_SAMPLES_TO_CONVERGENCE']),
                          normalizedSha256=hashlib.sha256(normalized_layer(example / 'result/example.usdc')).hexdigest(),
                          findingsSha256=manifest['actual_findings_sha256'],
                          measurementsSha256=hashlib.sha256((example / 'out/measurements.json').read_bytes()).hexdigest(),
                          budgetSeconds=manifest['budgetSeconds'], withinBudget=seconds <= manifest['budgetSeconds'])
            records.append(record)
            args.output.write_text(json.dumps(records, indent=2, sort_keys=True) + '\n')
            print(json.dumps(record, sort_keys=True), flush=True)
    return int(any(not r['withinBudget'] for r in records))


if __name__ == '__main__':
    raise SystemExit(main())
