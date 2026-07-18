"""Chronicler -- the ingest/vault writer subsystem.

Deliberately OUTSIDE the l5gntools stdlib-only, read-only scanner contract (it is
a writer, with its own optional deps). Not shipped as an installable package
(see pyproject `[tool.setuptools] packages`); it is a dev-tree module run in place
on the knight. Kept a package only so `chronicler.review` imports cleanly.
"""
