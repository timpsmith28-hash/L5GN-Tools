"""The witness layer (DECISIONS 0031, COWORK_BRIEF_ui_witness.md).

A witness asserts rendered/observed state against an expected state. It
emits findings, never a verdict, and it never gates a commit.

**Never imported by `verify.py`, never on the stdlib-core path.** Nothing in
`verify.py`'s `AUDITORS`/`TESTERS` lists may name a module under this
package, and nothing `verify.py` imports may import this package either --
the gate must stay installable and fast on a bare producer with no browser
dependency, however indirect.
"""
