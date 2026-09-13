"""Library-owned study paths; the legacy exporter layout is an input format."""
import os
from pathlib import Path
from pxr import Sdf, Vt

ROOT_KEY = 'aeco:solid:studyRoot'
ROOT_MARKER = 'aecoSolidStudy'
LEGACY = {'__ExactPrototypes': 'ExactPrototypes', 'ExactMaterials': 'ExactMaterials'}


def study_root(stage=None):
    """Prefer solid's persisted root, including sublayers, over the setting."""
    if stage is not None:
        for layer in stage.GetLayerStack():
            value = layer.customLayerData.get(ROOT_KEY)
            if value is not None:
                return checked_root(value)
        # Prim metadata survives flattening and identifies solid among libraries.
        roots = {p.GetPath() for p in stage.TraverseAll() if p.GetCustomData().get(ROOT_MARKER)}
        if len(roots) == 1:
            return checked_root(roots.pop())
        if len(roots) > 1:
            raise ValueError('Stage contains multiple solid study roots')
    return checked_root(os.environ.get('AECO_STUDY_ROOT', '/'))


def checked_root(value):
    path = Sdf.Path(value)
    if (not path.IsAbsolutePath() or path.ContainsPrimVariantSelection()
            or not (path.IsPrimPath() or path == Sdf.Path.absoluteRootPath)):
        raise ValueError('AECO_STUDY_ROOT must be an absolute prim path or /')
    return path


def scope(layer, path):
    for prefix in Sdf.Path(path).GetPrefixes():
        prim = Sdf.CreatePrimInLayer(layer, prefix)
        prim.specifier = Sdf.SpecifierDef
        prim.typeName = 'Scope'


def remap_paths(layer, mappings):
    """Update authored arcs without composing or flattening exact instances."""
    def mapped(path):
        for old, new in mappings:
            if path.HasPrefix(old):
                return path.ReplacePrefix(old, new)
        return path

    def metadata(value):
        if isinstance(value, dict):
            return {key: metadata(item) for key, item in value.items()}
        if isinstance(value, Sdf.Path):
            return mapped(value)
        if isinstance(value, str) and value.startswith('/') and Sdf.Path.IsValidPathString(value):
            return str(mapped(Sdf.Path(value)))
        if isinstance(value, (list, tuple, Vt.StringArray)):
            return type(value)([metadata(item) for item in value])
        return value

    paths = []
    layer.Traverse(Sdf.Path.absoluteRootPath, paths.append)
    for path in paths:
        spec = layer.GetObjectAtPath(path)
        if spec is None:
            continue
        for field, editor in (('targetPaths', 'targetPathList'), ('connectionPaths', 'connectionPathList'),
                              ('references', 'referenceList'), ('inheritPaths', 'inheritPathList'),
                              ('specializes', 'specializesList')):
            if not spec.HasInfo(field):
                continue
            operation = spec.GetInfo(field)

            def item(value):
                if isinstance(value, Sdf.Reference):
                    return Sdf.Reference(value.assetPath, mapped(value.primPath) if not value.assetPath else value.primPath,
                                         value.layerOffset, value.customData)
                return mapped(value)

            for name in (('explicitItems',) if operation.isExplicit else
                         ('addedItems', 'prependedItems', 'appendedItems', 'deletedItems', 'orderedItems')):
                setattr(getattr(spec, editor), name, [item(v) for v in getattr(operation, name)])
        if spec.HasInfo('customData'):
            spec.SetInfo('customData', metadata(spec.GetInfo('customData')))
    layer.customLayerData = metadata(layer.customLayerData)


def scope_layer(layer, root):
    """Adapt one writable IFC-exported layer; / is a byte-preserving no-op."""
    root = checked_root(root)
    if root == Sdf.Path.absoluteRootPath:
        return
    scope(layer, root)
    layer.GetPrimAtPath(root).customData = {**layer.GetPrimAtPath(root).customData, ROOT_MARKER: True}
    mappings = [(Sdf.Path('/' + old), root.AppendChild(new)) for old, new in LEGACY.items()]
    for old, new in mappings:
        if layer.GetPrimAtPath(old):
            if layer.GetPrimAtPath(new):
                raise ValueError('Study destination already exists: ' + str(new))
            scope(layer, new.GetParentPath())
            edit = Sdf.BatchNamespaceEdit()
            edit.Add(old, new)
            if not layer.Apply(edit):
                raise ValueError('Cannot relocate exact study: ' + str(old))
            container = layer.GetPrimAtPath(new)
            container.specifier = Sdf.SpecifierDef
            container.typeName = 'Scope'
    remap_paths(layer, mappings)
    layer.customLayerData = {**layer.customLayerData, ROOT_KEY: str(root)}


def scope_export(output, root=None):
    """Keep exact bodies at their element paths and scope shared resources."""
    root = study_root() if root is None else checked_root(root)
    if root == Sdf.Path.absoluteRootPath:
        return
    for name in ('exact.usda', 'twins.usda'):
        layer = Sdf.Layer.FindOrOpen(str(Path(output) / name))
        if not layer:
            raise ValueError('Missing exact export layer: ' + name)
        scope_layer(layer, root)
        layer.Save()


def copy_material(stage, material, root, source_layer):
    """A newly tessellated twin binds to this producer's own material copy."""
    from pxr import UsdShade
    target = checked_root(root).AppendPath('ExactMaterials/' + material.GetPrim().GetName())
    layer = stage.GetEditTarget().GetLayer()
    if not layer.GetPrimAtPath(target):
        scope(layer, target.GetParentPath())
        Sdf.CopySpec(source_layer, material.GetPath(), layer, target)
        remap_paths(layer, [(material.GetPath(), target)])
    return UsdShade.Material(stage.GetPrimAtPath(target))


def scope_cameras(layer):
    """Move the standalone input's cameras into the solid camera namespace."""
    renders = layer.GetPrimAtPath('/Renders')
    if not renders:
        return
    mappings = [(p.path, Sdf.Path('/Renders/solid').AppendChild(p.name))
                for p in renders.nameChildren if p.typeName == 'Camera']
    if not mappings:
        return
    scope(layer, '/Renders/solid')
    edit = Sdf.BatchNamespaceEdit()
    for old, new in mappings:
        edit.Add(old, new)
    if not layer.Apply(edit):
        raise ValueError('Cannot scope solid cameras')
    remap_paths(layer, mappings)
