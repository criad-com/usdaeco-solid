#!/pxrpythonsubst
"""Each registered rule sees a healthy stage before its defect is seeded."""
import os
from pathlib import Path
import unittest
from pxr import Plug, Sdf, Usd, UsdValidation
ROOT = Path(__file__).resolve().parents[1]


class TestValidators(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        core = Path(os.environ.get('AECO_CORE_ROOT',ROOT.parent/'usdaeco-core'))
        Plug.Registry().RegisterPlugins(str(core/'out/plugins/usdAeco/resources'))
        Plug.Registry().RegisterPlugins(str(ROOT/'usdAecoSolidValidators'))
        import usdAecoSolidValidators
        cls.registry=UsdValidation.ValidationRegistry()

    def setUp(self):
        source=Sdf.Layer.FindOrOpen(str(ROOT/'usdAecoSolid/examples/minimal.usda'))
        layer=Sdf.Layer.CreateAnonymous();layer.TransferContent(source)
        self.stage=Usd.Stage.Open(layer)
        self.exact=self.stage.GetPrimAtPath('/World/Wall/BodyExact')
        self.twin=self.stage.GetPrimAtPath('/World/Wall/Body')

    def validate(self,name):
        rule=self.registry.GetOrLoadValidatorByName('usdAecoSolidValidators:'+name+'Checker')
        self.assertTrue(rule)
        return list(UsdValidation.ValidationContext([rule]).Validate(self.stage))

    def defect(self,name,mutate):
        self.assertEqual(self.validate(name),[])
        mutate()
        errors=self.validate(name)
        self.assertTrue(errors)
        self.assertTrue(all(e.GetName()==name for e in errors))

    def test_ExactBodyWithoutTolerance(self):
        self.defect('ExactBodyWithoutTolerance',lambda:self.exact.GetAttribute('aeco:derived:tolerance').Set(0))

    def test_TwinWithoutFrom(self):
        self.defect('TwinWithoutFrom',lambda:self.twin.GetRelationship('aeco:derived:from').SetTargets([]))

    def test_TwinStale(self):
        self.defect('TwinStale',lambda:self.exact.GetAttribute('aeco:derived:stamp').Set('new exact generation'))

    def test_ExactBodyNotSolid(self):
        if not os.environ.get('USD_SOLID_OCCT_RUNTIME'):
            self.skipTest('Native solid validation NOT RUN without the optional runtime')
        self.defect('ExactBodyNotSolid',lambda:self.exact.GetAttribute('region:type').Set(['voidRegion','voidRegion']))

    def test_ProxyTwinMissing(self):
        self.defect('ProxyTwinMissing',lambda:self.stage.RemovePrim(self.twin.GetPath()))

    def test_nonfinite_tolerance(self):
        self.defect('ExactBodyWithoutTolerance',lambda:self.exact.GetAttribute('aeco:derived:tolerance').Set(float('nan')))

    def test_wrong_source(self):
        self.defect('TwinWithoutFrom',lambda:self.twin.GetRelationship('aeco:derived:from').SetTargets(['/World/Pipe/BodyExact']))

    def test_empty_proxy(self):
        self.defect('ProxyTwinMissing',lambda:self.twin.GetAttribute('points').Set([]))

    def test_material_partition_does_not_stale_geometry(self):
        self.assertEqual(self.validate('TwinStale'),[])
        self.exact.CreateAttribute('subsetFamily:materialBind:familyType',Sdf.ValueTypeNames.Token).Set('partition')
        self.assertEqual(self.validate('TwinStale'),[])

    def test_fingerprint_survives_serialized_negative_zero(self):
        from usdaeco_ifc.exact_common import fingerprint
        from pxr import Gf,UsdGeom
        matrix=Gf.Matrix4d(1);matrix[0,1]=-0.0
        UsdGeom.Xformable(self.exact).MakeMatrixXform().Set(matrix)
        before=fingerprint(self.exact)
        layer=Sdf.Layer.CreateAnonymous();layer.ImportFromString(self.stage.GetRootLayer().ExportToString())
        reopened=Usd.Stage.Open(layer)
        self.assertEqual(before,fingerprint(reopened.GetPrimAtPath(self.exact.GetPath())))

if __name__=='__main__':unittest.main()
