"""Literal plugin, validator and ProperCase error tokens."""
KEYWORD = "UsdAecoSolidValidators"
EXACT_BODY_WITHOUT_TOLERANCE = "ExactBodyWithoutTolerance"
EXACT_BODY_WITHOUT_TOLERANCE_CHECKER = "usdAecoSolidValidators:ExactBodyWithoutToleranceChecker"
TWIN_WITHOUT_FROM = "TwinWithoutFrom"
TWIN_WITHOUT_FROM_CHECKER = "usdAecoSolidValidators:TwinWithoutFromChecker"
TWIN_STALE = "TwinStale"
TWIN_STALE_CHECKER = "usdAecoSolidValidators:TwinStaleChecker"
EXACT_BODY_NOT_SOLID = "ExactBodyNotSolid"
EXACT_BODY_NOT_SOLID_CHECKER = "usdAecoSolidValidators:ExactBodyNotSolidChecker"
PROXY_TWIN_MISSING = "ProxyTwinMissing"
PROXY_TWIN_MISSING_CHECKER = "usdAecoSolidValidators:ProxyTwinMissingChecker"
ERROR_NAMES = (EXACT_BODY_WITHOUT_TOLERANCE, TWIN_WITHOUT_FROM, TWIN_STALE, EXACT_BODY_NOT_SOLID, PROXY_TWIN_MISSING,)
VALIDATORS = (EXACT_BODY_WITHOUT_TOLERANCE_CHECKER, TWIN_WITHOUT_FROM_CHECKER, TWIN_STALE_CHECKER, EXACT_BODY_NOT_SOLID_CHECKER, PROXY_TWIN_MISSING_CHECKER,)
