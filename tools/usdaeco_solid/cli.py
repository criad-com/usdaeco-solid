"""Measure exact bodies, generate proxy twins, and compare their geometry."""
import argparse
import json
import math
from pathlib import Path
import tempfile


def execute(operation, stage, *, prim=None, output=None, deflection=0.0001, edges=False, pairs=None):
    from usdaeco_ifc.exact_runtime import run_native
    if not math.isfinite(deflection) or deflection <= 0:
        raise ValueError("Deflection must be positive and finite")
    request = dict(operation=operation, stage=str(Path(stage).resolve()), prim=prim,
                   output=str(Path(output).resolve()) if output else None,
                   deflection=deflection, edges=edges, pairs=pairs or [])
    if operation == 'tessellate':
        from pxr import Usd
        from .paths import study_root
        source = Usd.Stage.Open(request['stage'])
        request['studyRoot'] = str(study_root(source))
    with tempfile.TemporaryDirectory(prefix="aeco-solid-") as temp:
        path = Path(temp) / "request.json"
        path.write_text(json.dumps(request))
        text = run_native(Path(__file__).with_name("native_worker.py"), path)
    return json.loads(text.splitlines()[-1])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, prog="aeco-solid")
    sub = parser.add_subparsers(dest="operation", required=True)
    for name in ("measure", "tessellate", "compare"):
        command = sub.add_parser(name)
        command.add_argument("stage", type=Path)
        command.add_argument("--prim", help="BrepArray path; omit to process every exact body")
        if name == "tessellate":
            command.add_argument("--out", type=Path, required=True)
            command.add_argument("--deflection", type=float, required=True, help="Linear deflection in metres")
            command.add_argument("--edges", action="store_true")
    args = parser.parse_args(argv)
    from usdaeco_ifc.exact_runtime import RuntimeUnavailable
    print("== stage: " + args.operation, flush=True)
    try:
        result = execute(args.operation, args.stage, prim=args.prim, output=getattr(args, "out", None),
                         deflection=getattr(args, "deflection", 0.0001), edges=getattr(args, "edges", False))
    except RuntimeUnavailable as error:
        print("NOT RUN: " + str(error))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(any(row.get("error") or row.get("withinTolerance") is False for row in result["bodies"]))


if __name__ == "__main__":
    raise SystemExit(main())
