"""Build the pinned variant in private scratch space inside this checkout."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def generate(root, work):
    root,work=Path(root),Path(work)
    if json.loads((root/'library.json').read_text())['version'] != '0.4.5':
        raise ValueError('The example requires datacentre v0.4.5')
    source_files=sorted((root/'spec').rglob('*'))+sorted((root/'src/dcbuild').rglob('*.py'))
    digest=hashlib.sha256(b''.join(p.read_bytes() for p in source_files if p.is_file())).hexdigest()
    output=work/'ifc/demo-datacentre-01.ifc'
    receipt=work/'source.sha256'
    if output.is_file() and receipt.is_file() and receipt.read_text()==digest:
        return output
    work.mkdir(parents=True,exist_ok=True)
    shutil.copytree(root/'spec',work/'spec',dirs_exist_ok=True)
    command='import sys;sys.dont_write_bytecode=True;sys.path.insert(0,sys.argv.pop(1));from dcbuild.cli import main;raise SystemExit(main())'
    env={k:v for k,v in os.environ.items() if k!='PYTHONPATH'}
    result=subprocess.run([sys.executable,'-c',command,str(root/'src'),'build-ifc','--variant','clash','--out','ifc','--manifest-dir','manifests'],cwd=work,env=env,capture_output=True,text=True,timeout=240)
    if result.returncode:raise RuntimeError('Variant generation failed: '+result.stderr[-2000:])
    receipt.write_text(digest)
    return output
