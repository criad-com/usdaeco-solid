"""Route S validation, registered through the Python UsdValidation plugin API."""
import math
from pathlib import Path
import tempfile
from pxr import Sdf, Usd, UsdGeom, UsdValidation
from usdaeco_ifc.exact_common import fingerprint
from . import validatorTokens as tokens


def error(prim, name, message):
    return UsdValidation.ValidationError(name, UsdValidation.ValidationErrorType.Error,
        [UsdValidation.ValidationErrorSite(prim.GetStage(), prim.GetPath())], message)


def exact(prim):
    return prim.GetTypeName() == 'BrepArray' and prim.GetAttribute('aeco:derived:approx').Get() == 'exact'


def tolerance_task(prim, time_range):
    value = prim.GetAttribute('aeco:derived:tolerance').Get()
    if exact(prim) and (value is None or not math.isfinite(value) or value <= 0):
        return [error(prim, tokens.EXACT_BODY_WITHOUT_TOLERANCE, 'An exact body needs its positive finite kernel tolerance in metres.')]
    return []


def is_twin(prim):
    return prim.IsA(UsdGeom.Mesh) and bool(prim.GetParent().GetChild('BodyExact')) and prim.GetName() == 'Body'


def from_task(prim, time_range):
    if not is_twin(prim):
        return []
    targets = prim.GetRelationship('aeco:derived:from').GetTargets()
    if targets != [prim.GetParent().GetPath().AppendChild('BodyExact')]:
        return [error(prim, tokens.TWIN_WITHOUT_FROM, 'The proxy twin must link its exact source through aeco:derived:from.')]
    return []


def stale_task(stage, time_range):
    errors = []
    for prim in stage.Traverse():
        if not is_twin(prim):
            continue
        source = prim.GetParent().GetChild('BodyExact')
        if not exact(source):
            continue
        stamp = prim.GetAttribute('aeco:derived:stamp').Get() or ''
        if 'source=' + fingerprint(source) not in stamp.split():
            errors.append(error(prim, tokens.TWIN_STALE, 'The twin was generated from different exact content or a different producer stamp; tessellate again.'))
    return errors


def proxy_task(stage, time_range):
    errors = []
    for prim in stage.Traverse():
        if not exact(prim):
            continue
        targets = prim.GetRelationship('proxyPrim').GetTargets()
        twin = UsdGeom.Mesh(stage.GetPrimAtPath(targets[0])) if len(targets) == 1 else None
        if not twin or not twin.GetPointsAttr().Get() or UsdGeom.Imageable(twin).ComputePurpose() != 'proxy':
            errors.append(error(prim, tokens.PROXY_TWIN_MISSING, 'A render-purpose exact body needs a renderable proxy Mesh twin for stock USD.'))
    return errors


def solid_task(stage, time_range):
    bodies = [p for p in stage.Traverse() if exact(p)]
    if not bodies:
        return []
    from usdaeco_solid.cli import execute
    with tempfile.TemporaryDirectory(prefix='aeco-solid-validation-') as directory:
        path = Path(directory) / 'stage.usdc'
        stage.Flatten(addSourceFileComment=False).Export(str(path))
        report = execute('validate', path)
    return [error(stage.GetPrimAtPath(row['path']), tokens.EXACT_BODY_NOT_SOLID,
                  row.get('error') or 'The bridge found invalid topology or zero solids.')
            for row in report['bodies'] if row.get('error') or not row.get('valid') or not row.get('solidCount')]


registry = UsdValidation.ValidationRegistry()
registry.RegisterPluginPrimValidator(tokens.EXACT_BODY_WITHOUT_TOLERANCE_CHECKER, tolerance_task)
registry.RegisterPluginPrimValidator(tokens.TWIN_WITHOUT_FROM_CHECKER, from_task)
registry.RegisterPluginStageValidator(tokens.TWIN_STALE_CHECKER, stale_task)
registry.RegisterPluginStageValidator(tokens.EXACT_BODY_NOT_SOLID_CHECKER, solid_task)
registry.RegisterPluginStageValidator(tokens.PROXY_TWIN_MISSING_CHECKER, proxy_task)
