# Close-out prompt

Paste this at the end of a thread you can't export via API (e.g. admin-gated
work-account Claude). The model emits a transcript in the intake convention; save
its output as a `.md` and drop it into
`CHRONICLER_HOME/chat_threads/raw_md_transcripts/` — the next `run.py ingest`
picks it up. Best-effort self-report, not a byte-exact export, so it's most
faithful on shorter threads.

---

Close out this thread: produce a complete markdown transcript of our entire
conversation for my archive, and nothing else. Use exactly this format:

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
