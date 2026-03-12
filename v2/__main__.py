from __future__ import annotations

import importlib

cli_module = importlib.import_module("v2.cli")
main = cli_module.main

raise SystemExit(main())
