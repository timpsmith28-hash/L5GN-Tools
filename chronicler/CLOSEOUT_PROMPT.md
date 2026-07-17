# Close-out prompt

Paste this at the end of a thread you can't export via API (e.g. admin-gated
work-account Claude). The model emits a transcript in the intake convention; save
its output as a `.md` and drop it into
`CHRONICLER_HOME/chat_threads/raw_md_transcripts/` — the next `run.py ingest`
picks it up.

## Reality check — a backup option, not a routine one

This is a **self-report, not an export**: the model reconstructs the transcript by
re-reasoning through every turn in its context, which is (a) token-expensive and
(b) lossy — it can paraphrase, compress, or drop turns, and on a long thread it
may hit the output limit before finishing. Practical guidance:

- Best on **short threads**; fidelity and cost both degrade with length.
- Reserve it for when a thread genuinely must be captured and you have budget to
  spare. For routine archiving under a session budget, keeping threads short and
  hand-saving is often the better trade.
- It asks for a **file** output where the model can create one; otherwise it
  prints inline for copy-paste.

---

Close out this thread: produce a complete markdown transcript of our entire
conversation for my archive, and nothing else. If you can write files, save it as
a `.md` file; otherwise output it inline. Use exactly this format:

```
---
source: claude
account: claude-work-manual
title: <a concise title for this thread>
created_at: <today's date, YYYY-MM-DD>
---
**User:**
<my first message, verbatim>

**Assistant:**
<your first reply, verbatim>

**User:**
<... and so on, in order ...>
```

Rules: one block per turn, in order; each block starts with a line that is exactly
`**User:**` or `**Assistant:**`; reproduce every turn verbatim without
summarising, truncating, or adding commentary, and keep code blocks intact. Output
only the transcript (the frontmatter block followed by the turns) — no preamble,
no closing remarks.
