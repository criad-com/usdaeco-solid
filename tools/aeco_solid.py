#!/usr/bin/env python3
"""Source-checkout entry point; installed users can run aeco-solid."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bootstrap
from usdaeco_solid.cli import main
raise SystemExit(main())
