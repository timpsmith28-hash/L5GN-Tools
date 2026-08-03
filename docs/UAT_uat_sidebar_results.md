<!-- uat: commit=b9fae8d dirty=true host=LucasGoonPC walked=2026-08-03 -->

# Results log — uat sidebar (walked 2026-08-03, LucasGoonPC)

Partner to `docs/UAT_uat_sidebar.md`.

This log records a verdict and its evidence per item -- never a computed pass. `[EVIDENCE]` walked (with evidence) · `[DEFERRED]` deferred, with a reason · `[BLOCKED]` blocked, with a reason · `[N/A]` not applicable.

---

## A · reading a sheet (Task 1)

- **A1** Open a real walk-sheet from `docs/` by stem (not this one — pick
  [EVIDENCE] ←[32mINFO←[0m:     127.0.0.1:61581 - "←[1mGET /api/uat/sheet?stem=uat_sidebar HTTP/1.1←[0m" ←[32m200 OK←[0m

- **A2** Open `doc_provenance_coverage` or `repo_tier_producers` (the two
  [EVIDENCE]
  ```
  ←[32mINFO←[0m:     127.0.0.1:61636 - "←[1mGET /api/uat/sheet?stem=UAT_repo_tier_producers.md HTTP/1.1←[0m" ←[31m404 Not Found←[0m
  ←[32mINFO←[0m:     127.0.0.1:61636 - "←[1mGET /api/uat/sheet?stem=UAT_repo_tier_producers HTTP/1.1←[0m" ←[31m404 Not Found←[0m
  ←[32mINFO←[0m:     127.0.0.1:61637 - "←[1mGET /api/uat/sheet?stem=repo_tier_producers HTTP/1.1←[0m" ←[32m200 OK←[0m
  ```

## B · recording a verdict and evidence (Task 2)

- **B3** Set an item's verdict to **deferred** and leave the evidence box
  [DEFERRED] added deferred for this box - I was blocked when trying to emit

- **B4** Same as B3, for **blocked**.
  [BLOCKED] added block for this box - I was blocked when trying to emit without a comment

---

## Not walked, and why

- **B3** [DEFERRED] Set an item's verdict to **deferred** and leave the evidence box — added deferred for this box - I was blocked when trying to emit
- **B4** [BLOCKED] Same as B3, for **blocked**. — added block for this box - I was blocked when trying to emit without a comment
