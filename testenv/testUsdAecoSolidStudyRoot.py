"""Exercise real exported instances, materials and the pinned project catalog."""
import json
import os
from pathlib import Path
import shutil

import pytest
from pxr import Plug, Sdf, Usd, UsdGeom, UsdShade, Vt
from usdaeco_solid.paths import ROOT_KEY, ROOT_MARKER, scope_export, scope_layer, study_root

ROOT = Path(__file__).resolve().parents[1]
LAYERS = ROOT / 'examples/datacentre/result/layers/out'


def exported_stage(tmp_path, root):
    for name in ('exact.usda', 'twins.usda'):
        shutil.copyfile(LAYERS / name, tmp_path / name)
    scope_export(tmp_path, root)
    layer = Sdf.Layer.CreateNew(str(tmp_path / 'stage.usda'))
    layer.subLayerPaths = ['exact.usda', 'twins.usda']
    layer.pseudoRoot.SetInfo('metersPerUnit', 1.)
    layer.Save()
    return Usd.Stage.Open(layer)


def test_default_export_bytes(tmp_path, monkeypatch):
    monkeypatch.delenv('AECO_STUDY_ROOT', raising=False)
    exported_stage(tmp_path, '/')
    scope_export(tmp_path)
    for name in ('exact.usda', 'twins.usda'):
        assert (tmp_path / name).read_bytes() == (LAYERS / name).read_bytes()


@pytest.mark.parametrize('root', ['/Studies/solid', '/Analysis/Office/Exact'])
def test_scoped_pinned_export(tmp_path, monkeypatch, root):
    stage = exported_stage(tmp_path, root)
    assert not stage.GetCompositionErrors()
    assert stage.GetPrimAtPath(Sdf.Path(root).AppendChild('ExactPrototypes'))
    assert not stage.GetPrimAtPath('/__ExactPrototypes')
    assert not stage.GetPrimAtPath('/ExactMaterials')
    for prefix in Sdf.Path(root).GetPrefixes():
        prim = stage.GetPrimAtPath(prefix)
        assert prim.GetTypeName() == 'Scope' and not prim.GetAppliedSchemas()
    bodies = [p for p in stage.Traverse() if p.GetTypeName() == 'BrepArray']
    expected = json.loads((ROOT / 'examples/datacentre/expected/findings.json').read_text())
    census = next(row for row in expected if row['name'] == 'ExactOfficeBodies')
    reuse = next(row for row in expected if row['name'] == 'RepresentationReuse')
    assert len(bodies) == census['exact']
    assert sum(p.IsInstance() for p in bodies) == reuse['mappedProducts']
    for body in bodies:
        twin = body.GetParent().GetChild('Body')
        assert body.GetRelationship('proxyPrim').GetTargets() == [twin.GetPath()]
        assert twin.GetRelationship('aeco:derived:from').GetTargets() == [body.GetPath()]
        for prim in (body, twin):
            for subset in Usd.PrimRange(prim, Usd.TraverseInstanceProxies()):
                if subset.IsA(UsdGeom.Subset):
                    material, _ = UsdShade.MaterialBindingAPI(subset).ComputeBoundMaterial()
                    assert material and material.GetPath().HasPrefix(Sdf.Path(root).AppendChild('ExactMaterials'))
                    shader = material.ComputeSurfaceSource()[0]
                    assert shader and shader.GetPath().HasPrefix(material.GetPath())
    monkeypatch.setenv('AECO_STUDY_ROOT', '/Wrong')
    assert study_root(stage) == Sdf.Path(root)
    flattened = Usd.Stage.Open(stage.Flatten(addSourceFileComment=False))
    assert study_root(flattened) == Sdf.Path(root)
    from usdaeco_solid.publication import flatten_study
    published = Usd.Stage.Open(flatten_study(stage))
    assert not published.GetCompositionErrors()
    assert not any(p.GetName().startswith('Flattened_Prototype_') for p in published.GetPseudoRoot().GetAllChildren())
    assert len(published.GetPrototypes()) == len(stage.GetPrototypes())
    assert sum(p.GetTypeName() == 'BrepArray' for p in published.Traverse()) == len(bodies)
    # Existing validators discover bodies and correlation from the stage data.
    Plug.Registry().RegisterPlugins(str(ROOT / 'usdAecoSolidValidators'))
    import usdAecoSolidValidators as validators
    assert validators.stale_task(stage, None) == []
    assert validators.proxy_task(stage, None) == []
    assert all(validators.from_task(p.GetParent().GetChild('Body'), None) == [] for p in bodies)


def test_full_project_keeps_one_catalog(tmp_path):
    data = Path(os.environ.get('AECO_DATACENTRE_FULL_ROOT', ROOT.parent / 'usdaeco-datacentre-0.5.2'))
    if not data.is_dir():
        pytest.skip('Set AECO_DATACENTRE_FULL_ROOT to data centre v0.5.2')
    assert json.loads((data / 'library.json').read_text())['version'] == '0.5.2'
    source = data / 'dist/full/dc.usda'
    original = Usd.Stage.Open(str(source))
    stage = exported_stage(tmp_path, '/Studies/solid')
    stage.GetRootLayer().subLayerPaths.append(str(source))
    project = original.GetDefaultPrim().GetPath()
    stage.SetDefaultPrim(stage.GetPrimAtPath(project))
    assert not stage.GetCompositionErrors()
    assert {p.GetPath() for p in stage.GetPseudoRoot().GetAllChildren()} == {project, Sdf.Path('/Studies')}
    assert stage.GetPrimAtPath(project.AppendChild('_TypeCatalog'))
    assert not stage.GetPrimAtPath('/_TypeCatalog')
    before = [str(p.GetPath()) for p in Usd.PrimRange.AllPrims(original.GetPrimAtPath(project.AppendChild('_TypeCatalog')))]
    after = [str(p.GetPath()) for p in Usd.PrimRange.AllPrims(stage.GetPrimAtPath(project.AppendChild('_TypeCatalog')))]
    assert after == before
    assert all(p.GetPath().HasPrefix(project) for p in stage.Traverse() if p.GetTypeName() == 'BrepArray')


def test_metadata_paths_and_external_references():
    stage = Usd.Stage.CreateInMemory()
    material = UsdShade.Material.Define(stage, '/ExactMaterials/M').GetPrim()
    material.SetCustomData({'source': '/ExactMaterials/M'})
    material.GetReferences().AddReference('other.usda', '/ExactMaterials/M')
    layer = stage.GetRootLayer()
    layer.customLayerData = {'paths': Vt.StringArray(['/ExactMaterials/M', '/Project/Element']),
                            'nested': {'prototype': '/__ExactPrototypes/P'}}
    scope_layer(layer, '/Studies/solid')
    assert list(layer.customLayerData['paths']) == ['/Studies/solid/ExactMaterials/M', '/Project/Element']
    assert layer.customLayerData['nested']['prototype'] == '/Studies/solid/ExactPrototypes/P'
    spec = layer.GetPrimAtPath('/Studies/solid/ExactMaterials/M')
    assert spec.customData['source'] == '/Studies/solid/ExactMaterials/M'
    assert spec.referenceList.prependedItems[0].primPath == Sdf.Path('/ExactMaterials/M')


@pytest.mark.parametrize('value', ['', 'relative', '/Studies.property', '/Studies{v=x}'])
def test_invalid_root(value, monkeypatch):
    monkeypatch.setenv('AECO_STUDY_ROOT', value)
    with pytest.raises(ValueError, match='absolute prim path'):
        study_root()


@pytest.mark.skipif(not os.environ.get('USD_SOLID_OCCT_RUNTIME'), reason='Exact runtime absent')
def test_tessellation_owns_materials_across_libraries(tmp_path, monkeypatch):
    from usdaeco_solid.cli import execute
    stage = exported_stage(tmp_path, '/Studies/clash')
    # Simulate the peer producer's independently scoped IFC export.
    for layer in stage.GetLayerStack():
        if ROOT_KEY in layer.customLayerData:
            layer.customLayerData = {'aeco:clash:studyRoot': '/Studies/clash'}
            layer.GetPrimAtPath('/Studies/clash').customData = {}
            layer.Save()
    body = next(p for p in stage.Traverse() if p.GetTypeName() == 'BrepArray' and p.IsInstance())
    body_path = body.GetPath()
    source = tmp_path / 'peer.usdc'
    stage.Flatten(addSourceFileComment=False).Export(str(source))
    monkeypatch.setenv('AECO_STUDY_ROOT', '/Studies/solid')
    output = tmp_path / 'solid-twin.usda'
    result = execute('tessellate', source, prim=str(body_path), output=output, edges=True)
    assert not result['bodies'][0].get('error')
    composed = Sdf.Layer.CreateAnonymous()
    composed.subLayerPaths = [str(output), str(source)]
    stage = Usd.Stage.Open(composed)
    twin = stage.GetPrimAtPath(body_path.GetParentPath().AppendChild('Body'))
    for subset in twin.GetChildren():
        if subset.IsA(UsdGeom.Subset):
            material, _ = UsdShade.MaterialBindingAPI(subset).ComputeBoundMaterial()
            assert str(material.GetPath()).startswith('/Studies/solid/ExactMaterials/')
            assert material.ComputeSurfaceSource()[0]
    assert stage.GetPrimAtPath('/Studies/clash/ExactMaterials')
    monkeypatch.setenv('AECO_STUDY_ROOT', '/Wrong')
    assert study_root(stage) == Sdf.Path('/Studies/solid')
    # CLI consumers and the native validator work after reopening without a setting.
    assert execute('compare', source, prim=str(body_path))['bodies'][0]['withinTolerance']
    assert execute('validate', source, prim=str(body_path))['bodies'][0]['valid']


@pytest.mark.skipif(not os.environ.get('USD_SOLID_OCCT_RUNTIME'), reason='Exact runtime absent')
def test_live_hook_on_pinned_datacentre(tmp_path, monkeypatch):
    from usdaeco_solid.example import hook
    from usdaeco_solid.paths import scope_cameras
    data = os.environ.get('AECO_DATACENTRE_ROOT')
    if not data:
        pytest.skip('Set AECO_DATACENTRE_ROOT to data centre v0.4.8')
    assert json.loads((Path(data) / 'library.json').read_text())['version'] == '0.4.8'
    monkeypatch.setenv('AECO_STUDY_ROOT', '/Studies/solid')
    cameras = Sdf.Layer.CreateNew(str(tmp_path / 'cameras.usda'))
    cameras.TransferContent(Sdf.Layer.FindOrOpen(str(ROOT / 'examples/datacentre/inputs/cameras.usda')))
    scope_cameras(cameras)
    cameras.Save()
    source = Path(data) / 'dist/clash/dc.usda'
    stage = Usd.Stage.CreateNew(str(tmp_path / 'example.usda'))
    stage.GetRootLayer().subLayerPaths = [str(cameras.realPath), str(source)]
    base = Usd.Stage.Open(str(source))
    for name in ('metersPerUnit', 'upAxis', 'fallbackPrimTypes'):
        stage.SetMetadata(name, base.GetMetadata(name))
    stage.SetDefaultPrim(stage.GetPrimAtPath(base.GetDefaultPrim().GetPath()))
    result = hook(stage, tmp_path)
    assert next(row for row in result if row['name'] == 'ExactOfficeBodies')['exact'] == 109
    assert stage.GetPrimAtPath('/Studies/solid/MeasuredClearance')
    assert stage.GetPrimAtPath('/Studies/solid/MeasuredClearanceDisplay')
    assert stage.GetPrimAtPath('/Renders/solid/clearance')
    assert {p.GetPath() for p in stage.GetPseudoRoot().GetAllChildren()} == {
        base.GetDefaultPrim().GetPath(), Sdf.Path('/Studies'), Sdf.Path('/Renders')}
    stage.GetRootLayer().Save()
    from usdaeco_solid.cli import execute
    monkeypatch.delenv('AECO_STUDY_ROOT')
    result = execute('compare', tmp_path / 'example.usda')
    assert len(result['bodies']) == 109 and all(row['withinTolerance'] for row in result['bodies'])
