"""Seed the interchangeable-prototype defect without requiring the kernel."""
import subprocess
import sys

import pytest
from pxr import Gf, Sdf, Usd, UsdGeom
from usdaeco_solid.publication import order_instances_for_flattening
from usdaeco_solid.publication import reflatten


def instance_stage(order):
    stage = Usd.Stage.CreateInMemory()
    for name in ('First', 'Second'):
        source = stage.CreateClassPrim('/Sources/' + name)
        UsdGeom.Cube.Define(stage, source.GetPath().AppendChild('Shape'))
    for name, source in (('A', 'First'), ('B', 'Second'), ('C', 'Second')):
        prim = UsdGeom.Xform.Define(stage, '/World/' + name).GetPrim()
        prim.GetReferences().AddInternalReference('/Sources/' + source)
        UsdGeom.Xformable(prim).AddTranslateOp().Set(Gf.Vec3d(len(name), ord(name), 0))
    for name in order:
        stage.GetPrimAtPath('/World/' + name).SetInstanceable(True)
    return stage


def snapshot(stage):
    return {
        str(p.GetPath()): (str(UsdGeom.XformCache().GetLocalToWorldTransform(p)),
                          p.GetAttribute('size').Get())
        for p in stage.Traverse(Usd.TraverseInstanceProxies())
    }


def test_interchangeable_prototypes_publish_identically(tmp_path):
    first = instance_stage('ABC')
    second = instance_stage('BCA')
    # Prove the defect before applying the fix: identical prototype contents,
    # different occurrence references after allocation in a different order.
    assert first.Flatten(False).ExportToString() != second.Flatten(False).ExportToString()
    before = snapshot(first)
    outputs = []
    for index, stage in enumerate((first, second)):
        assert order_instances_for_flattening(stage) == 3
        assert snapshot(stage) == before
        assert len(stage.GetPrototypes()) == 2
        assert stage.GetPrimAtPath('/World/B').GetPrototype() == stage.GetPrimAtPath('/World/C').GetPrototype()
        assert all(stage.GetPrimAtPath('/World/' + name).IsInstance() for name in 'ABC')
        assert not stage.GetCompositionErrors()
        path = tmp_path / f'publication-{index}.usdc'
        assert stage.Flatten(False).Export(str(path))
        outputs.append(Sdf.Layer.OpenAsAnonymous(str(path)).ExportToString().encode('utf-8'))
    assert outputs[0] == outputs[1]


@pytest.mark.parametrize('source_alias', [False, True])
def test_reflatten_reads_relocated_own_layers_and_pinned_source(tmp_path, source_alias):
    """A changed authored layer must change the repeated publication."""
    source = tmp_path / 'first'
    (source / 'out').mkdir(parents=True)
    pinned = Usd.Stage.CreateNew(str(tmp_path / 'pinned.usda'))
    UsdGeom.Xform.Define(pinned, '/World')
    UsdGeom.Cube.Define(pinned, '/World/PinnedBody')
    pinned.GetRootLayer().Save()
    authored = instance_stage('BCA')
    authored.GetRootLayer().Export(str(source / 'out/twins.usda'))
    root = Sdf.Layer.CreateNew(str(source / 'out/example.usda'))
    source_path = '../../pinned.usda'
    if source_alias:
        (source / 'inputs').mkdir()
        (source / 'inputs/source').symlink_to(tmp_path, target_is_directory=True)
        source_path = '../inputs/source/pinned.usda'
    root.subLayerPaths = ['twins.usda', source_path]
    stage = Usd.Stage.Open(root)
    order_instances_for_flattening(stage)
    root.Save()
    expected = stage.Flatten(False).ExportToString()
    source_bytes = (source / 'out/twins.usda').read_bytes()
    crate = reflatten(source / 'out/example.usda', tmp_path / 'second')
    assert Sdf.Layer.OpenAsAnonymous(str(crate)).ExportToString() == expected
    assert (tmp_path / 'second/out/twins.usda').read_bytes() == source_bytes
    # The new stage depends on its copied own layers, not the old directory.
    import shutil
    shutil.rmtree(source)
    probe = subprocess.run([
        sys.executable, '-I', '-c',
        'from pxr import Usd; import sys; stage = Usd.Stage.Open(sys.argv[1]); '
        'assert stage and not stage.GetCompositionErrors(); '
        'assert stage.GetPrimAtPath("/World/PinnedBody")',
        str(tmp_path / 'second/out/example.usda'),
    ], capture_output=True, text=True)
    assert probe.returncode == 0, probe.stderr
    copied = Usd.Stage.Open(str(tmp_path / 'second/out/example.usda'))
    assert not copied.GetCompositionErrors()
    assert copied.GetPrimAtPath('/World/PinnedBody')
    UsdGeom.Xformable(copied.GetPrimAtPath('/World/A')).GetOrderedXformOps()[0].Set(Gf.Vec3d(20, 0, 0))
    copied.GetRootLayer().Save()
    changed = reflatten(tmp_path / 'second/out/example.usda', tmp_path / 'third')
    assert Sdf.Layer.OpenAsAnonymous(str(changed)).ExportToString() != expected


def test_reflatten_preserves_prototype_order_after_b7_mutes(tmp_path):
    """Cross the prototype 9/10 identifier boundary with the B7 lifecycle."""
    source = tmp_path / 'first/out'
    source.mkdir(parents=True)
    for name, child in (('exact', 'BodyExact'), ('twins', 'Body')):
        authored = Usd.Stage.CreateNew(str(source / (name + '.usda')))
        for occurrence in 'AB':
            cls = authored.CreateClassPrim('/Sources/' + name + occurrence)
            UsdGeom.Cube.Define(authored, cls.GetPath().AppendChild('Shape'))
            prim = UsdGeom.Xform.Define(authored, f'/World/{occurrence}/{child}').GetPrim()
            prim.GetReferences().AddInternalReference(cls.GetPath())
            prim.SetInstanceable(True)
        authored.GetRootLayer().Save()
    root = Sdf.Layer.CreateNew(str(source / 'example.usda'))
    root.subLayerPaths = ['exact.usda', 'twins.usda']
    stage = Usd.Stage.Open(root)
    for _ in range(2):
        stage.MuteLayer(str(source / 'exact.usda'))
        stage.UnmuteLayer(str(source / 'exact.usda'))
    assert order_instances_for_flattening(stage) == 4
    root.Save()
    expected = stage.Flatten(False).ExportToString()
    reopened = Usd.Stage.Open(root)
    order_instances_for_flattening(reopened)
    assert reopened.Flatten(False).ExportToString() != expected
    crate = reflatten(source / 'example.usda', tmp_path / 'second')
    assert Sdf.Layer.OpenAsAnonymous(str(crate)).ExportToString() == expected
