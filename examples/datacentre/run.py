#!/usr/bin/env python3
"""Run and optionally publish the exact office-wing study."""
import argparse
import json
import os
import shutil
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import bootstrap
from usdaeco_check.example import run_example
from usdaeco_solid.example import hook


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish',action='store_true')
    args=parser.parse_args()
    example=Path(__file__).parent
    budget=json.loads((example/'manifest.json').read_text())['budgetSeconds']
    manifest=run_example(example,hook,variant='clash',publish=args.publish,size=(1280,800))
    from usdaeco_render import render
    # The scene-index Embree path dirties unknown exact prims when guides
    # are enabled. The legacy delegate draws this non-instanced cutaway.
    # Stock publication above always uses the default imaging path.
    previous=os.environ.get('USDIMAGINGGL_ENGINE_ENABLE_SCENE_INDEX')
    os.environ['USDIMAGINGGL_ENGINE_ENABLE_SCENE_INDEX']='0'
    try:
        print('== stage: render exact edge guides',flush=True)
        guides=render(example/'out/example.usda',output=example/'out/guides',purposes='guide,proxy,render')
    finally:
        if previous is None:os.environ.pop('USDIMAGINGGL_ENGINE_ENABLE_SCENE_INDEX',None)
        else:os.environ['USDIMAGINGGL_ENGINE_ENABLE_SCENE_INDEX']=previous
    for record in guides:
        name='wireframe-'+Path(record['path']).name
        shutil.copyfile(example/'out/guides'/Path(record['path']).name,example/'out/renders'/name)
        record['path']='renders/'+name
        if args.publish:shutil.copyfile(example/'out/renders'/name,example/'renders'/name)
    manifest['renders'].extend(guides)
    manifest['budgetSeconds']=budget
    (example/'out/manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    if args.publish:shutil.copyfile(example/'out/manifest.json',example/'manifest.json')

if __name__=='__main__':main()
