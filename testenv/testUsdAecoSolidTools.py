"""Kernel measurements, real tessellation changes and geometric rejection."""
import os
from pathlib import Path
import pytest
from pxr import Gf, Sdf, Usd
from usdaeco_solid.cli import execute
ROOT=Path(__file__).resolve().parents[1]
pytestmark=pytest.mark.skipif(not os.environ.get('USD_SOLID_OCCT_RUNTIME'),reason='Exact operations NOT RUN: native runtime absent')
SOURCE=ROOT/'usdAecoSolid/examples/minimal.usda'


def test_measured_dimensions():
    rows={r['path']:r for r in execute('measure',SOURCE)['bodies']}
    assert rows['/World/Wall/BodyExact']['thickness']==pytest.approx(.3,abs=1e-6)
    assert rows['/World/Pipe/BodyExact']['outsideDiameter']==pytest.approx(.08,abs=1e-6)
    assert all(r['valid'] and r['solidCount']==1 and r['area']>0 and r['volume']>0 for r in rows.values())


def test_tessellate_and_compare(tmp_path):
    output=tmp_path/'twins.usda'
    result=execute('tessellate',SOURCE,output=output,deflection=.00005,edges=True)
    assert len(result['bodies'])==2 and not any(r.get('error') for r in result['bodies'])
    layer=Sdf.Layer.CreateNew(str(tmp_path/'stage.usda'));layer.subLayerPaths=[str(output),str(SOURCE)]
    stage=Usd.Stage.Open(layer);stage.SetMetadata('metersPerUnit',1.);layer.Save()
    rows=execute('compare',tmp_path/'stage.usda')['bodies']
    assert len(rows)==2 and all(r['withinTolerance'] for r in rows)
    twin=stage.GetPrimAtPath('/World/Pipe/Body')
    assert twin.GetAttribute('aeco:derived:tolerance').Get()==.00005
    assert twin.GetAttribute('aeco:derived:stamp').Get().startswith('aeco-solid 0.1.0 source=')


def test_compare_rejects_wrong_mesh_volume(tmp_path):
    stage=Usd.Stage.Open(str(SOURCE));layer=Sdf.Layer.CreateAnonymous();layer.TransferContent(stage.GetRootLayer());stage=Usd.Stage.Open(layer)
    points=stage.GetPrimAtPath('/World/Wall/Body').GetAttribute('points')
    points.Set([p*1.5 for p in points.Get()])
    path=tmp_path/'wrong.usda';layer.Export(str(path))
    rows=execute('compare',path)['bodies']
    assert not next(r for r in rows if r['path']=='/World/Wall/BodyExact')['withinTolerance']


def test_measure_world_scale_and_reject_shear(tmp_path):
    source=Sdf.Layer.FindOrOpen(str(SOURCE));layer=Sdf.Layer.CreateAnonymous();layer.TransferContent(source);stage=Usd.Stage.Open(layer)
    from pxr import UsdGeom
    op=UsdGeom.Xformable(stage.GetPrimAtPath('/World/Pipe')).AddScaleOp();op.Set((2,2,2))
    path=tmp_path/'scaled.usda';layer.Export(str(path))
    row=execute('measure',path,prim='/World/Pipe/BodyExact')['bodies'][0]
    assert row['outsideDiameter']==pytest.approx(.16,abs=1e-6)
    op.Set((2,1,1));layer.Export(str(path))
    row=execute('measure',path,prim='/World/Pipe/BodyExact')['bodies'][0]
    assert 'uniformly scaled' in row['error']


def test_compare_detects_scaled_twin_transform(tmp_path):
    from pxr import UsdGeom
    source=Sdf.Layer.FindOrOpen(str(SOURCE));layer=Sdf.Layer.CreateAnonymous();layer.TransferContent(source)
    stage=Usd.Stage.Open(layer)
    UsdGeom.Xformable(stage.GetPrimAtPath('/World/Wall/Body')).AddScaleOp().Set((2,2,2))
    path=tmp_path/'wrong-twin-scale.usda';layer.Export(str(path))
    row=execute('compare',path,prim='/World/Wall/BodyExact')['bodies'][0]
    assert not row['withinTolerance']
