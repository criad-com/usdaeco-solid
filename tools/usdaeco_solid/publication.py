"""Stable instance allocation and relocation of already-authored examples."""
from pathlib import Path
import shutil
from pxr import Sdf, Usd


def relocate_composition(source, target):
    """Copy own layers and relocate the root's pinned source arcs.

    The composition root lives in out/ beside the authored geometry. Its
    sibling inputs/ and out/ layers keep their bytes; external pinned layers
    remain read-only dependencies. No exported crate or kernel is used.
    """
    source, target = Path(source).resolve(), Path(target).resolve()
    source_example, target_example = source.parents[1], target.parents[1]
    stage = Usd.Stage.Open(str(source))
    if not stage or stage.GetCompositionErrors():
        raise ValueError('Authored example does not compose')
    for layer in stage.GetUsedLayers():
        if not layer.realPath or layer == stage.GetRootLayer():
            continue
        path = Path(layer.realPath).resolve()
        if path.is_relative_to(source_example):
            copied = target_example / path.relative_to(source_example)
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, copied)
    target.parent.mkdir(parents=True, exist_ok=True)
    root = Sdf.Layer.CreateNew(str(target))
    root.TransferContent(stage.GetRootLayer())
    root.subLayerPaths = [
        relative if Path(Sdf.ComputeAssetPathRelativeToLayer(stage.GetRootLayer(), relative)).resolve().is_relative_to(source_example)
        # The runtime inputs/source alias disappears with the source example.
        else str(Path(Sdf.ComputeAssetPathRelativeToLayer(stage.GetRootLayer(), relative)).resolve())
        for relative in root.subLayerPaths]
    root.Save()
    return target


def reflatten(source, target):
    """Independently compose and normalize the own layers in another root."""
    target = Path(target)
    stage = Usd.Stage.Open(str(relocate_composition(source, target / 'out/example.usda')))
    if not stage or stage.GetCompositionErrors():
        raise ValueError('Relocated example does not compose')
    # Flatten names prototypes in lexical identifier order. USD's allocator
    # keeps counting after retired prototypes disappear, so reproduce the
    # publisher's two B7 mute/unmute cycles before its final sorted allocation.
    # This is composition only; no kernel, tessellation or measurements run.
    exact_layer = (target / 'out/exact.usda').resolve()
    if exact_layer.is_file():
        for _ in range(2):
            stage.MuteLayer(str(exact_layer))
            stage.UnmuteLayer(str(exact_layer))
    order_instances_for_flattening(stage)
    output = target / 'example.usdc'
    if not stage.Flatten(addSourceFileComment=False).Export(str(output)):
        raise ValueError('Re-flattening failed')
    return output


def order_instances_for_flattening(stage):
    """Recreate flat mapped instances in occurrence-path order before Flatten.

    USD allocates prototype names during composition. Content-identical
    prototypes can exchange names between runs, changing flattened references
    even though their geometry agrees. Retire every current prototype, then
    enable instances one at a time so composition allocates them in a stable
    order. Do not batch the enabling edits in an Sdf.ChangeBlock.

    Only the transient composition root gets redundant instanceable opinions;
    authored source layers, per-occurrence properties and sharing are retained.
    The office example has no nested instances.
    """
    paths = sorted(p.GetPath() for p in stage.TraverseAll() if p.IsInstance())
    with Usd.EditContext(stage, stage.GetRootLayer()):
        for path in paths:
            stage.GetPrimAtPath(path).SetInstanceable(False)
        if stage.GetPrototypes():
            raise ValueError('Publication requires flat mapped instances')
        for path in paths:
            stage.GetPrimAtPath(path).SetInstanceable(True)
    return len(paths)
