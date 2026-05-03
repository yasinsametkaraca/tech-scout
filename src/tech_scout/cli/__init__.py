"""CLI entry points for tech-scout helper commands.

Each module in this package implements one ``ts-*`` console command
listed in ``[project.scripts]``. The same modules are also re-invoked by
the legacy ``scripts/ts_*.py`` shims so the repo continues to work
without ``pip install -e .``.

Public surface:

* :func:`tech_scout.cli._common.run_script` — wraps a ``main()`` that
  returns a dict into the standard JSON envelope flow (success or error).
* ``ts_<name>`` modules each expose ``main()`` (the command's logic) and
  ``entry_point()`` (the console-script callable).
"""

from __future__ import annotations
