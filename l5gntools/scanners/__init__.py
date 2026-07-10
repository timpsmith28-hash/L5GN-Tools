"""Scanner modules. Each exposes:

* ``NAME`` (str), ``DESCRIPTION`` (str), ``ESTATE_LEVEL`` (bool)
* per-project scanners define ``scan(target: Path) -> dict``
* estate-level scanners define ``scan_estate(projects: list[Path]) -> dict``

Scanners are pure and read-only: they return data and never write to disk.
"""
