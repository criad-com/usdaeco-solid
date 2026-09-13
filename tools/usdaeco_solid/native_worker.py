"""OCCT measurements in the ABI-matched process, independent of IFC intent."""
import json
from pathlib import Path
import sys
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, UsdSolid, UsdSolidOcct as Bridge
import _exact_native as Native
from usdaeco_ifc.exact_common import comparison, mesh_measures
from usdaeco_ifc.exact_worker import author_twin, author_edges


def dimensions(shape):
    data = Native.Inspect(shape)
    planes = [p for p in data["faces"] if p["type"] == "plane"]
    candidates = []
    for i,a in enumerate(planes):
        for b in planes[i+1:]:
            n, other = Gf.Vec3d(*a["normal"]), Gf.Vec3d(*b["normal"])
            if abs(Gf.Dot(n, other)) < 1-1e-10:
                continue
            distance = abs(Gf.Dot(n, Gf.Vec3d(*a["origin"])-Gf.Vec3d(*b["origin"])))
            if distance > data["tolerance"]:
                candidates.append((min(a["area"], b["area"]), distance))
    candidates.sort(key=lambda x:(-x[0],x[1]))
    radii = [p["radius"] for p in data["faces"] if p["type"] == "cylinder"]
    return dict(thickness=candidates[0][1] if candidates else None,
                outsideDiameter=2*max(radii) if radii else None,
                tolerance=data["tolerance"], planarPairs=len(candidates), cylindricalFaces=len(radii))


def world_shape(prim, shape, transforms):
    matrix = transforms.GetLocalToWorldTransform(prim)
    rows = [Gf.Vec3d(*tuple(matrix[i])[:3]) for i in range(3)]
    lengths = [r.GetLength() for r in rows]
    if min(lengths) <= 0 or max(lengths)-min(lengths) > 1e-10 or any(abs(Gf.Dot(rows[i],rows[j])) > 1e-10 for i,j in ((0,1),(0,2),(1,2))):
        raise ValueError("Exact operations require a rigid or uniformly scaled transform")
    return Native.Transform(shape, [float(v) for r in matrix for v in r])


def main(request_path):
    request = json.loads(Path(request_path).read_text())
    stage = Usd.Stage.Open(request["stage"])
    if not stage or stage.GetCompositionErrors():
        raise ValueError("Stage does not compose")
    if UsdGeom.GetStageMetersPerUnit(stage) != 1:
        raise ValueError("Measurements require metres")
    prims = [stage.GetPrimAtPath(request["prim"])] if request["prim"] else [p for p in stage.Traverse() if p.GetTypeName() == "BrepArray"]
    if not prims or any(not p or p.GetTypeName() != "BrepArray" for p in prims):
        raise ValueError("No BrepArray selected")
    result = dict(bodies=[], pairs=[])
    operation = request["operation"]
    transforms = UsdGeom.XformCache()
    world_shapes = {}

    def in_world(prim, shape=None):
        path = prim.GetPath()
        if path not in world_shapes:
            if shape is None:
                shape = Bridge.Build(UsdSolid.BrepArray(prim))
            world_shapes[path] = world_shape(prim, shape, transforms)
        return world_shapes[path]

    if operation == "tessellate":
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from usdaeco_solid.paths import ROOT_KEY, ROOT_MARKER, copy_material, scope
        source_layer = stage.Flatten(addSourceFileComment=False)
        layer = Sdf.Layer.CreateNew(request["output"])
        stage.GetSessionLayer().subLayerPaths.append(layer.identifier)
        stage.SetEditTarget(layer)
        root = Sdf.Path(request['studyRoot'])
        if root != Sdf.Path.absoluteRootPath:
            scope(layer, root)
            layer.GetPrimAtPath(root).customData = {ROOT_MARKER: True}
            layer.customLayerData = {ROOT_KEY: str(root)}
    for prim in prims:
        row = dict(path=str(prim.GetPath()))
        try:
            shape = Bridge.Build(UsdSolid.BrepArray(prim))
            row.update(valid=Bridge.IsValid(shape), solidCount=Bridge.SolidCount(shape))
            if not row["valid"] or not row["solidCount"]:
                raise ValueError("Exact body is not a valid solid")
            if operation == "validate":
                result["bodies"].append(row)
                continue
            if operation == "tessellate":
                transform = UsdGeom.Xformable(prim).GetLocalTransformation()
                twin, tess = author_twin(stage, prim, shape, request["deflection"], transform)
                twin.GetPrim().SetInstanceable(False)
                subsets=[p for p in Usd.PrimRange(prim,Usd.TraverseInstanceProxies()) if p.IsA(UsdGeom.Subset)]
                for child in subsets:
                    source=UsdGeom.Subset(child)
                    faces=set(source.GetIndicesAttr().Get())
                    subset=UsdGeom.Subset.Define(stage,twin.GetPath().AppendChild(child.GetName()))
                    subset.CreateElementTypeAttr('face')
                    subset.CreateFamilyNameAttr(source.GetFamilyNameAttr().Get())
                    subset.CreateIndicesAttr([i for i,face in enumerate(tess.sourceFaceIndices) if face in faces])
                    material,_=UsdShade.MaterialBindingAPI(child).ComputeBoundMaterial()
                    if material:
                        own = copy_material(stage, material, root, source_layer)
                        UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(own)
                material,_=UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
                if material:
                    own = copy_material(stage, material, root, source_layer)
                    UsdShade.MaterialBindingAPI.Apply(twin.GetPrim()).Bind(own)
                if subsets:UsdGeom.Subset.SetFamilyType(UsdGeom.Imageable(twin.GetPrim()),'materialBind','partition')
                twin.GetPrim().GetAttribute("aeco:derived:stamp").Set(
                    twin.GetPrim().GetAttribute("aeco:derived:stamp").Get().replace("aeco-ifc-exact 0.2.0", "aeco-solid 0.1.0"))
                if request["edges"]:
                    author_edges(stage, prim, shape, request["deflection"], transform)
                row.update(twin=str(twin.GetPath()), deflection=request["deflection"])
            else:
                measured = in_world(prim, shape)
                row.update(volume=Bridge.Volume(measured), area=Bridge.Area(measured), **dimensions(measured))
                if operation == "compare":
                    twin = UsdGeom.Mesh(prim.GetParent().GetChild("Body"))
                    if not twin:
                        raise ValueError("Exact body has no Mesh twin")
                    transform = transforms.GetLocalToWorldTransform(twin.GetPrim())
                    row.update(comparison(row['volume'], row['area'], *mesh_measures(twin, transform),
                                          twin.GetPrim().GetAttribute("aeco:derived:tolerance").Get()))
        except Exception as error:
            row["error"] = str(error)
        result["bodies"].append(row)
    for pair in request["pairs"]:
        a,b = [in_world(stage.GetPrimAtPath(p)) for p in pair["paths"]]
        result["pairs"].append(dict(id=pair["id"], distance=Bridge.Distance(a,b), commonVolume=Bridge.Volume(Bridge.Common(a,b))))
    if operation == "tessellate":
        layer.Save()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1])
