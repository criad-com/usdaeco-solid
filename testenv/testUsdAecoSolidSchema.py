#!/pxrpythonsubst
"""Route S uses core and UsdSolid; it adds no geometry or kind schema."""
from pathlib import Path
import unittest
from pxr import Plug, Usd, UsdGeom
ROOT = Path(__file__).resolve().parents[1]


class TestSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        core = Path(os.environ.get('AECO_CORE_ROOT', ROOT.parent/'usdaeco-core'))
        Plug.Registry().RegisterPlugins(str(core/'out/plugins/usdAeco/resources'))

    def test_core_mark_is_the_only_api(self):
        stage=Usd.Stage.Open(str(ROOT/'usdAecoSolid/examples/minimal.usda'))
        for prim in stage.Traverse():
            self.assertFalse(any(str(a).startswith('AecoSolid') for a in prim.GetAppliedSchemas()))
        exact=stage.GetPrimAtPath('/World/Wall/BodyExact')
        self.assertTrue(exact.HasAPI('AecoDerivedGeometryAPI'))
        self.assertEqual(exact.GetAttribute('aeco:derived:approx').Get(),'exact')
        twin=UsdGeom.Mesh(stage.GetPrimAtPath('/World/Wall/Body'))
        self.assertEqual(twin.GetPurposeAttr().Get(),'proxy')
        self.assertEqual(twin.GetPrim().GetRelationship('aeco:derived:from').GetTargets(),[exact.GetPath()])

    def test_core_derived_metadata_and_applicability(self):
        definition=Usd.SchemaRegistry().FindAppliedAPIPrimDefinition('AecoDerivedGeometryAPI')
        self.assertIn('aeco:derived:tolerance', definition.GetPropertyNames())
        stage=Usd.Stage.CreateInMemory()
        self.assertTrue(stage.DefinePrim('/M','Mesh').CanApplyAPI('AecoDerivedGeometryAPI'))
        self.assertFalse(stage.DefinePrim('/Material','Material').CanApplyAPI('AecoDerivedGeometryAPI'))

if __name__=='__main__':unittest.main()
