"""Create a small, portable wall/pipe example from the IFC regression BReps."""
from pathlib import Path
import sys
from pxr import Gf, Usd, UsdGeom, UsdSolid, UsdSolidOcct as Bridge, Vt
import _exact_native as Native
from usdaeco_ifc.exact_common import mark
from usdaeco_ifc.exact_worker import author_twin, author_edges

source, target = map(Path, sys.argv[1:])
stage = Usd.Stage.CreateInMemory()
UsdGeom.SetStageMetersPerUnit(stage, 1)
UsdGeom.SetStageUpAxis(stage, 'Z')
stage.SetMetadata('fallbackPrimTypes', {'BrepArray': Vt.TokenArray(['Xform'])})
root = UsdGeom.Xform.Define(stage, '/World').GetPrim()
stage.SetDefaultPrim(root)
for name, identity in [('wall','250e12ab-7329-5cfa-9149-ea39df43f1ca'),('pipe','d2a39da9-fd0a-5f4f-8514-a22dd5d5cb39')]:
    shape = Native.ReadBrep((source / (name+'.brep')).read_text())
    element = UsdGeom.Xform.Define(stage, '/World/'+name.title()).GetPrim()
    element.ApplyAPI('AecoElementAPI')
    element.GetAttribute('aeco:id').Set(identity)
    element.ApplyAPI('AecoClassificationAPI', 'ifc')
    element.GetAttribute('aeco:class:ifc:code').Set('IfcWall' if name=='wall' else 'IfcPipeSegment')
    exact = UsdSolid.BrepArray.Define(stage, element.GetPath().AppendChild('BodyExact'))
    Bridge.Write(shape,exact)
    shape = Bridge.Build(exact)
    exact.CreatePurposeAttr('render')
    mark(exact.GetPrim(),identity,'body','exact',Native.Inspect(shape)['tolerance'],'aeco-ifc-exact 0.2.0 fixture')
    twin,_ = author_twin(stage,exact,shape,.0001)
    twin.CreateDisplayColorAttr([(0.62,.73,.82) if name=='wall' else (.1,.55,.7)])
    exact.CreateProxyPrimRel().SetTargets([twin.GetPath()])
    author_edges(stage,exact.GetPrim(),shape,.0001)
target.parent.mkdir(parents=True,exist_ok=True)
stage.GetRootLayer().Export(str(target))
