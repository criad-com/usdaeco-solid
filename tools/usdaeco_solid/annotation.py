"""Small USD stroke labels: the measured value stays in the rendered scene."""
from pxr import Gf, Sdf, UsdGeom
from .paths import checked_root, scope, study_root

GLYPHS={
    '0': [[(0,0),(0,1),(.6,1),(.6,0),(0,0)]],
    '1': [[(.2,.8),(.4,1),(.4,0)]],
    '2': [[(0,1),(.6,1),(.6,.5),(0,.5),(0,0),(.6,0)]],
    '3': [[(0,1),(.6,1),(.6,0),(0,0)],[(0,.5),(.6,.5)]],
    '4': [[(0,1),(0,.5),(.6,.5)],[(.6,1),(.6,0)]],
    '5': [[(.6,1),(0,1),(0,.5),(.6,.5),(.6,0),(0,0)]],
    '6': [[(.6,1),(0,1),(0,0),(.6,0),(.6,.5),(0,.5)]],
    '7': [[(0,1),(.6,1),(0,0)]],
    '8': [[(0,.5),(0,1),(.6,1),(.6,0),(0,0),(0,.5),(.6,.5)]],
    '9': [[(.6,.5),(0,.5),(0,1),(.6,1),(.6,0),(0,0)]],
    '.': [[(.25,0),(.3,0)]],
    'm': [[(0,0),(0,.7),(.3,.7),(.3,0)],[(.3,.7),(.6,.7),(.6,0)]],
    ' ': [],
}


def mesh_strokes(stage,curves,path,radius=.002):
    """Embree's mesh-only delegate needs a visible guide companion to curves."""
    points=curves.GetPointsAttr().Get();counts=curves.GetCurveVertexCountsAttr().Get()
    vertices=[];indices=[];offset=0
    for count in counts:
        line=points[offset:offset+count];offset+=count
        for aa,bb in zip(line,line[1:]):
            a,b=Gf.Vec3d(aa),Gf.Vec3d(bb);d=b-a
            if d.GetLength()<1e-12:continue
            d.Normalize();axis=Gf.Vec3d(0,0,1) if abs(d[2])<.9 else Gf.Vec3d(0,1,0)
            u=Gf.Cross(d,axis).GetNormalized()*radius;v=Gf.Cross(d,u).GetNormalized()*radius
            start=len(vertices)
            vertices.extend(Gf.Vec3f(p+delta) for p in (a,b) for delta in (u,v,-u,-v))
            for i in range(4):indices.extend([start+i,start+(i+1)%4,start+4+(i+1)%4,start+4+i])
    mesh=UsdGeom.Mesh.Define(stage,path)
    mesh.CreatePointsAttr(vertices);mesh.CreateFaceVertexCountsAttr([4]*(len(indices)//4));mesh.CreateFaceVertexIndicesAttr(indices)
    mesh.CreateSubdivisionSchemeAttr('none');mesh.CreatePurposeAttr('guide');mesh.CreateDoubleSidedAttr(True)
    mesh.CreateDisplayColorAttr([(.65,.32,.035)])
    transform=UsdGeom.Xformable(curves).GetLocalTransformation()
    UsdGeom.Xformable(mesh).MakeMatrixXform().Set(transform)
    return mesh


def label(stage,text,position,camera,*,root=None):
    root=study_root(stage) if root is None else checked_root(root)
    parent=Sdf.Path('/Renders') if root==Sdf.Path.absoluteRootPath else root
    if root!=Sdf.Path.absoluteRootPath:scope(stage.GetEditTarget().GetLayer(),root)
    matrix=UsdGeom.Xformable(camera).GetLocalTransformation()
    right=Gf.Vec3d(*tuple(matrix[0])[:3]);up=Gf.Vec3d(*tuple(matrix[1])[:3])
    origin=Gf.Vec3d(*position);scale=.085
    lines=[]
    for i,char in enumerate(text):
        for stroke in GLYPHS[char]:
            lines.append([origin+scale*((x+.85*i)*right+y*up) for x,y in stroke])
    curves=UsdGeom.BasisCurves.Define(stage,parent.AppendChild('MeasuredClearance'))
    curves.CreateTypeAttr('linear');curves.CreateWrapAttr('nonperiodic')
    curves.CreateCurveVertexCountsAttr([len(line) for line in lines])
    curves.CreatePointsAttr([Gf.Vec3f(p) for line in lines for p in line])
    curves.CreateWidthsAttr([.004]);curves.SetWidthsInterpolation('constant')
    curves.CreateDisplayColorAttr([(.04,.13,.19)])
    curves.CreatePurposeAttr('guide')
    curves.GetPrim().SetDocumentation('Exact kernel clearance: '+text)
    mesh_strokes(stage,curves,parent.AppendChild('MeasuredClearanceDisplay'),radius=.003)
