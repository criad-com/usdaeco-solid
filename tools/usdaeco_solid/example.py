"""Exact-body office study over the pinned clash variant."""
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import uuid
from pxr import Gf, Sdf, Usd, UsdGeom, Vt
from .cli import execute
from .paths import scope_export, study_root

ROOT=Path(__file__).resolve().parents[2]


def cohort(stage, block):
    bounds=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','proxy','render'])
    selected=[]
    for prim in stage.Traverse():
        if not prim.GetAttribute('aeco:id').Get():continue
        meshes=[p for p in prim.GetChildren() if p.IsA(UsdGeom.Mesh) and p.GetAttribute('aeco:derived:role').Get()=='body']
        if not meshes:continue
        centre=bounds.ComputeWorldBound(prim).ComputeAlignedRange().GetMidpoint()
        if block['x']-1e-6 <= centre[0] <= block['x']+block['w']+1e-6 and block['y']-1e-6 <= centre[1] <= block['y']+block['d']+1e-6:
            selected.append(prim)
    return selected


def hook(stage,out):
    import ifcopenshell
    import ifcopenshell.util.element
    import ifcopenshell.util.unit
    import yaml
    from usdaeco_ifc.exact import export_exact
    root=study_root()
    data=Path(os.environ['AECO_DATACENTRE_ROOT']).resolve()
    publication=json.loads((data/'dist/clash/dc.manifest.json').read_text())
    manifest=json.loads((data/'manifests/demo-datacentre-01.clash.json').read_text())
    block=yaml.safe_load((data/'spec/facility.yaml').read_text())['building']['blocks']['office']
    selected=cohort(stage,block)
    ids={p.GetAttribute('aeco:id').Get() for p in selected}
    spec=importlib.util.spec_from_file_location('example_input',ROOT/'examples/datacentre/inputs/generate.py')
    generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)
    source=generator.generate(data,ROOT/'.work/datacentre')
    # The source census anchors the selection to the manifest; no base counts
    # are encoded in this implementation.
    all_elements=[p for p in stage.Traverse() if 'AecoElementAPI' in p.GetAppliedSchemas()]
    assert len(all_elements)==publication['counts']['elements']
    assert sum(p.IsA(UsdGeom.Mesh) for p in stage.Traverse())==publication['counts']['meshes']
    report=export_exact(source,data/'dist/clash/dc.usda',out,identities=ids)
    if report['failed']:raise ValueError('Exact export failed: '+json.dumps(report['perClass']))
    scope_export(out,root)
    stage.GetRootLayer().subLayerPaths[:0]=['exact.usda','twins.usda']
    fallbacks=stage.GetMetadata('fallbackPrimTypes');fallbacks['BrepArray']=Vt.TokenArray(['Xform']);stage.SetMetadata('fallbackPrimTypes',fallbacks)
    stage.GetRootLayer().Save()
    paths={p.GetAttribute('aeco:props:DC_Identity:Id').Get():str(p.GetPath().AppendChild('BodyExact')) for p in selected}
    pairs=[dict(id=case['id'],paths=[paths[case['id']],paths[case['partner']]]) for case in manifest['expected']['clash']]
    measured=execute('compare',out/'example.usda',pairs=pairs)
    if any(row.get('error') for row in measured['bodies']):raise ValueError('An exact body could not be measured')
    model=ifcopenshell.open(str(source));scale=ifcopenshell.util.unit.calculate_unit_scale(model)
    indexed={str(uuid.UUID(hex=ifcopenshell.guid.expand(p.GlobalId))):p for p in model.by_type('IfcElement')}
    measurements={r['path']:r for r in measured['bodies']}
    wall_errors=[];pipe_errors=[]
    for row in report['bodies']:
        value=measurements[row['path']+'/BodyExact'];element=indexed[row['id']]
        if row['ifcClass']=='IfcWall':
            material=ifcopenshell.util.element.get_material(element,should_skip_usage=True)
            if material and material.is_a('IfcMaterialLayerSet'):
                expected=sum(layer.LayerThickness for layer in material.MaterialLayers)*scale
            else:
                # The published fixture declares single-material sections by
                # Qto Width, the same source used for Route K's one-layer build-up.
                expected=ifcopenshell.util.element.get_psets(element)['Qto_WallBaseQuantities']['Width']*scale
            wall_errors.append(abs(value['thickness']-expected))
        if row['ifcClass']=='IfcPipeSegment':
            expected=ifcopenshell.util.element.get_psets(element)['DC_Section']['OutsideDiameter']*scale
            pipe_errors.append(abs(value['outsideDiameter']-expected))
    assert wall_errors and pipe_errors and max(wall_errors)<=1e-6 and max(pipe_errors)<=1e-6
    assert all(r['withinTolerance'] for r in measured['bodies'])
    assert {r['path'].rsplit('/',1)[0] for r in measured['bodies']} == {r['path'] for r in report['bodies']}
    for case in manifest['expected']['clash']:
        actual=next(p for p in measured['pairs'] if p['id']==case['id'])
        if case['exact']['verdict']=='hard':assert actual['commonVolume']>0
        else:assert abs(actual['distance']-case['exact']['distance'])<=1e-6
    # Muting exact geometry leaves each proxy's points and placement unchanged.
    transforms=UsdGeom.XformCache()
    before={str(p.GetPath()): (str(p.GetAttribute('points').Get()),str(transforms.GetLocalToWorldTransform(p)))
            for p in stage.Traverse() if p.GetName()=='Body' and p.IsA(UsdGeom.Mesh)}
    exact_layer=str((out/'exact.usda').resolve());stage.MuteLayer(exact_layer)
    transforms.Clear()
    after={str(p.GetPath()):(str(p.GetAttribute('points').Get()),str(transforms.GetLocalToWorldTransform(p)))
           for p in stage.Traverse() if p.GetName()=='Body' and p.IsA(UsdGeom.Mesh)}
    assert before==after and len(after)==len(selected) and not stage.GetCompositionErrors()
    stage.UnmuteLayer(exact_layer)
    presentation=Sdf.Layer.CreateNew(str(out/'presentation.usda'))
    stage.GetRootLayer().subLayerPaths.insert(0,'presentation.usda')
    focus={p.rsplit('/',1)[0] for pair in pairs for p in pair['paths']}
    with Usd.EditContext(stage,presentation):
        for p in stage.Traverse():
            if p.IsA(UsdGeom.Mesh) or p.IsA(UsdGeom.BasisCurves):
                # A cutaway of the three planted cases; the crate retains all
                # exact bodies and their proxy meshes for inspection.
                show=str(p.GetParent().GetPath()) in focus and p.GetName() in ('Body','Edges')
                UsdGeom.Imageable(p).CreateVisibilityAttr('inherited' if show else 'invisible')
        from .annotation import label,mesh_strokes
        from usdaeco_ifc.exact_common import mark
        for parent in sorted(focus):
            body=UsdGeom.Mesh(stage.GetPrimAtPath(parent+'/Body'))
            is_wall=stage.GetPrimAtPath(parent).GetAttribute('aeco:class:ifc:code').Get().startswith('IfcWall')
            body.CreateDisplayColorAttr([(.24,.29,.32) if is_wall else (.05,.32,.4)])
            edges=UsdGeom.BasisCurves(stage.GetPrimAtPath(parent+'/Edges'))
            display=mesh_strokes(stage,edges,parent+'/EdgeDisplay',radius=.002)
            mark(display.GetPrim(),edges.GetPrim().GetAttribute('aeco:derived:source').Get(),'wireframe','tessellated',.004,
                 'aeco-solid 0.1.0 guide display',edges.GetPath())
        clearance=next(p['distance'] for p in measured['pairs'] if p['id']=='pipe.clash.near')
        cameras=[p for p in stage.Traverse() if p.IsA(UsdGeom.Camera) and p.GetName()=='clearance']
        camera=next((p for p in cameras if p.GetParent().GetName()=='solid'), cameras[0] if len(cameras)==1 else None)
        if camera is None:raise ValueError('A solid clearance camera is required')
        label(stage,f'{clearance*1000:.3f} mm',(23.65,-1.5,7.06),camera,root=root)
    presentation.Save()
    stage.MuteLayer(exact_layer)
    stage.Flatten(addSourceFileComment=False).Export(str(ROOT/'.work/muted.usdc'))
    stage.UnmuteLayer(exact_layer)
    from .publication import order_instances_for_flattening
    order_instances_for_flattening(stage)
    (out/'measurements.json').write_text(json.dumps(measured,indent=2,sort_keys=True)+'\n')
    findings=[dict(name='ExactOfficeBodies',sourceElements=publication['counts']['elements'],sourceMeshes=publication['counts']['meshes'],
                   selected=len(selected),exact=report['exact'],failed=report['failed'],perClass=report['perClass']),
              dict(name='Measurements',walls=len(wall_errors),pipes=len(pipe_errors),maxThicknessError=max(wall_errors),maxOdError=max(pipe_errors),
                   twins=len(measured['bodies']),twinsWithinTolerance=sum(r['withinTolerance'] for r in measured['bodies'])),
              dict(name='B7Mute',twins=len(after),samePointsAndTransforms=before==after,compositionErrors=0),
              dict(name='RepresentationReuse',mappedProducts=report['mappedProducts'],prototypes=report['prototypes'],materialSubsets=report['materialSubsets']),
              dict(name='ExactClearances',pairs=measured['pairs'])]
    return findings
