"""Source checkout setup; never requires package installation."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
roots = [ROOT, ROOT / "tools"]
for variable, sibling in (("AECO_CORE_ROOT", "usdaeco-core"), ("TOOLCHAIN_DIR", "usdaeco-toolchain"),
                          ("AECO_IFC_ROOT", "usdaeco-ifc")):
    root = Path(os.environ.get(variable, ROOT.parent / sibling))
    roots.extend([root, root / "tools"])
for root in reversed(roots):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")
# Bound the nine CPU-rendered example views; callers can request more samples.
# This affects fresh previews only, never the geometry or committed images.
os.environ.setdefault('HDEMBREE_SAMPLES_TO_CONVERGENCE', '8')
os.environ.setdefault('AECO_EXACT_CACHE', str(ROOT / '.work/native'))

if os.environ.get('USD_SOLID_OCCT_RUNTIME') and not os.environ.get('USDRECORD'):
    from usdaeco_ifc.exact_runtime import native_renderer, RuntimeUnavailable
    try:
        os.environ['USDRECORD'] = str(native_renderer())
    except RuntimeUnavailable:
        pass  # The gate reports exact rows as NOT RUN.
if os.environ.get("USDRECORD"):
    os.environ["PATH"] = str(Path(os.environ["USDRECORD"]).resolve().parent) + os.pathsep + os.environ["PATH"]
