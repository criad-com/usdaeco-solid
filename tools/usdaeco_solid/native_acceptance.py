"""Native schema and representation checks, using the bridge runtime only."""
import json
import sys
from pxr import Usd, UsdGeom, UsdShade, UsdSolid, UsdSolidOcct as Bridge, UsdValidation

stage = Usd.Stage.Open(sys.argv[1])
registry = UsdValidation.ValidationRegistry()
metadata = registry.GetValidatorMetadataForKeyword('UsdSolidValidators')
validators = registry.GetOrLoadValidatorsByName([m.name for m in metadata])
if len(validators) != 20 or not all(validators):
    raise RuntimeError('All 20 native UsdSolid validators must load')
errors = UsdValidation.ValidationContext(validators).Validate(stage)
result = dict(validators=len(validators), findings=[dict(name=e.GetName(), message=e.GetMessage()) for e in errors],
              materialBodies=0, materialPartitionsValid=True, mappedProducts=0, prototypes=0)
prototypes = set()
for prim in stage.Traverse():
    if prim.GetTypeName() != 'BrepArray':
        continue
    twin = prim.GetParent().GetChild('Body')
    shape = Bridge.Build(UsdSolid.BrepArray(prim))
    tess = Bridge.Tessellate(shape, twin.GetAttribute('aeco:derived:tolerance').Get(), 0.1)
    exact_groups = {p.GetName(): UsdGeom.Subset(p) for p in Usd.PrimRange(prim, Usd.TraverseInstanceProxies()) if p.IsA(UsdGeom.Subset)}
    twin_groups = {p.GetName(): UsdGeom.Subset(p) for p in Usd.PrimRange(twin, Usd.TraverseInstanceProxies()) if p.IsA(UsdGeom.Subset)}
    valid = bool(exact_groups) and exact_groups.keys() == twin_groups.keys()
    faces = []
    triangles = []
    for name, subset in exact_groups.items():
        group = list(subset.GetIndicesAttr().Get())
        peer = twin_groups.get(name)
        indices = list(peer.GetIndicesAttr().Get()) if peer else []
        valid &= indices == [i for i,face in enumerate(tess.sourceFaceIndices) if face in group]
        material, _ = UsdShade.MaterialBindingAPI(subset.GetPrim()).ComputeBoundMaterial()
        other, _ = UsdShade.MaterialBindingAPI(peer.GetPrim()).ComputeBoundMaterial() if peer else (None, None)
        valid &= bool(material) and bool(other) and material.GetPath() == other.GetPath()
        faces += group
        triangles += indices
    valid &= sorted(faces) == list(range(Bridge.FaceCount(shape)))
    valid &= sorted(triangles) == list(range(len(tess.sourceFaceIndices)))
    result['materialBodies'] += bool(exact_groups)
    result['materialPartitionsValid'] &= valid
    if prim.IsInstance():
        result['mappedProducts'] += 1
        prototypes.add(str(prim.GetPrototype().GetPath()))
        if not twin.IsInstance():
            raise ValueError('Mapped exact body must also have an instanced twin')
result['prototypes'] = len(prototypes)
print(json.dumps(result, sort_keys=True))
