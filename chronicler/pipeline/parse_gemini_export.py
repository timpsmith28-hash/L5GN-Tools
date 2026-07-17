"""
parse_gemini_export.py — decoder for raw_gem_files/ (Gemini "share individual
chat" export, work account), build spec item 4b.

BACKGROUND (read before touching this file):
This format is genuinely undocumented — there is no .proto schema anywhere
in this repo or its history. An earlier session's pipeline/STATUS.md
correctly flagged these 110 files as "binary/protobuf-style, not JSON" and
deferred them. This module was reverse-engineered from scratch this session
by walking the raw protobuf wire format (varint tag/length framing) across
sample files spanning the full size range (7.6KB to ~13MB) and confirming
the same structure holds corpus-wide across all 110 files. It is NOT a
generalization of pre-existing proven code — no such code existed.

CONFIRMED STRUCTURE (stable across all 110 files):
  field 2 (string, len=32)      -> conversation id: a 32-char lowercase hex
                                    hash (NOT a dashed RFC-4122 UUID, but the
                                    only native, stable per-conversation
                                    identifier this format carries — used
                                    as-is for thread_id, per spec: reuse,
                                    don't synthesize).
  field 3 (submessage)          -> conversation container
    field 3.1 (submessage)      -> chat body
      field 3.1.1 (string)      -> conversation title
      field 3.1.2 (submessage, REPEATED) -> one per turn-pair, in order
        field 3.1.2.1 (string, optional) -> user turn text (occasionally
                                    empty/absent for media-only turns)
        field 3.1.2.2 (string, optional) -> model turn text (occasionally
                                    absent, e.g. a final unanswered turn)
        field 3.1.2.3 (submessage, rare) -> tool/code-artifact metadata,
                                    not a distinct message; ignored here
    field 3.2 (bytes)           -> large opaque high-entropy blob (~7 bits/
                                    byte, no image magic bytes, doesn't
                                    inflate as zlib/gzip/brotli/zstd) —
                                    almost certainly internal model-state /
                                    continuation-token data, not an
                                    attachment. Not surfaced by this parser.

NOT PRESENT in this format (confirmed by scanning every sample for wire-type
0 varints and for filename/hash-like leaf strings):
  - No per-turn timestamp of any kind.
  - No dedicated attachment/file-reference field. Any attachment (uploaded
    image, generated-image URL, linked Doc/Sheet/Script) shows up only as
    plain text/URL *inside* the turn's own text field, not as structured
    metadata. Per the task's explicit scope, no new extraction is built for
    this — flagging it here, as instructed, rather than reverse-engineering
    field 3.2 to guess at attachment content.

This module only decodes structure; it does not touch chronicler.db or the
filesystem beyond reading the source file. See normalize_gemini_work.py for
the DB-writing side.

Usage (library):
    from parse_gemini_export import parse_export_file, GeminiExportParseError
    result = parse_export_file(path)
    # result = {"conversation_id": "...", "title": "...", "turns": [
    #     {"user": "..." or None, "model": "..." or None}, ...]}

Usage (standalone smoke test):
    python3 pipeline/parse_gemini_export.py <path> [<path> ...]
"""
from __future__ import annotations

import sys
from pathlib import Path


class GeminiExportParseError(Exception):
    """Raised when a raw_gem_files export doesn't match the confirmed
    structure closely enough to trust — callers should flag, not skip."""


def _read_varint(buf: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    start = pos
    while True:
        if pos >= len(buf):
            raise GeminiExportParseError(f"truncated varint starting at byte {start}")
        b = buf[pos]
        result |= (b & 0x7F) << shift
        pos += 1
        if not (b & 0x80):
            return result, pos
        shift += 7
        if shift > 70:
            raise GeminiExportParseError(f"runaway varint starting at byte {start}")


def _parse_fields(buf: bytes) -> list[tuple[int, int, object]]:
    """Parse one level of protobuf wire-format framing. Returns a list of
    (field_number, wire_type, value) tuples in file order. wire_type 2
    (length-delimited) values are returned as raw bytes — callers recurse
    explicitly into the specific sub-paths they know about, rather than
    this function guessing which byte strings are submessages (guessing
    generically caused false-positive nested parses during exploration)."""
    fields = []
    pos = 0
    n = len(buf)
    while pos < n:
        tag, pos = _read_varint(buf, pos)
        field_num = tag >> 3
        wire_type = tag & 0x7
        if wire_type == 0:  # varint
            value, pos = _read_varint(buf, pos)
        elif wire_type == 1:  # 64-bit fixed
            if pos + 8 > n:
                raise GeminiExportParseError("truncated 64-bit field")
            value = buf[pos:pos + 8]
            pos += 8
        elif wire_type == 2:  # length-delimited
            length, pos = _read_varint(buf, pos)
            if pos + length > n:
                raise GeminiExportParseError("length-delimited field overruns buffer")
            value = buf[pos:pos + length]
            pos += length
        elif wire_type == 5:  # 32-bit fixed
            if pos + 4 > n:
                raise GeminiExportParseError("truncated 32-bit field")
            value = buf[pos:pos + 4]
            pos += 4
        else:
            raise GeminiExportParseError(f"unsupported wire type {wire_type} for field {field_num}")
        fields.append((field_num, wire_type, value))
    return fields


def _get_first(fields: list, field_num: int):
    for fn, wt, val in fields:
        if fn == field_num:
            return wt, val
    return None, None


def _decode_str(raw: bytes, context: str) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise GeminiExportParseError(f"{context}: not valid utf-8 ({e})")


def parse_export_file(path: Path) -> dict:
    """Parse one raw_gem_files export file. Raises GeminiExportParseError
    (with a descriptive message) on any structural mismatch — callers must
    catch this per-file and flag it, never silently skip."""
    raw = path.read_bytes()
    if not raw:
        raise GeminiExportParseError("empty file")

    top = _parse_fields(raw)

    wt, id_bytes = _get_first(top, 2)
    if wt != 2 or id_bytes is None:
        raise GeminiExportParseError("missing top-level field 2 (conversation id)")
    conversation_id = _decode_str(id_bytes, "field 2 (conversation id)")
    if len(conversation_id) != 32 or any(c not in "0123456789abcdef" for c in conversation_id):
        raise GeminiExportParseError(
            f"field 2 does not look like a 32-char hex id: {conversation_id!r}"
        )

    wt, container_bytes = _get_first(top, 3)
    if wt != 2 or container_bytes is None:
        raise GeminiExportParseError("missing top-level field 3 (conversation container)")
    container_fields = _parse_fields(container_bytes)

    wt, chat_bytes = _get_first(container_fields, 1)
    if wt != 2 or chat_bytes is None:
        raise GeminiExportParseError("missing field 3.1 (chat body)")
    chat_fields = _parse_fields(chat_bytes)

    wt, title_bytes = _get_first(chat_fields, 1)
    if wt != 2 or title_bytes is None:
        raise GeminiExportParseError("missing field 3.1.1 (title)")
    title = _decode_str(title_bytes, "field 3.1.1 (title)")

    turns = []
    for fn, wt, val in chat_fields:
        if fn != 2:
            continue
        if wt != 2:
            raise GeminiExportParseError(f"field 3.1.2 has unexpected wire type {wt}")
        turn_fields = _parse_fields(val)
        _, user_bytes = _get_first(turn_fields, 1)
        _, model_bytes = _get_first(turn_fields, 2)
        user_text = _decode_str(user_bytes, "turn field 1 (user text)") if user_bytes is not None else None
        model_text = _decode_str(model_bytes, "turn field 2 (model text)") if model_bytes is not None else None
        if user_text is None and model_text is None:
            raise GeminiExportParseError("turn has neither user nor model text")
        turns.append({"user": user_text, "model": model_text})

    if not turns:
        raise GeminiExportParseError("no turns found (field 3.1.2 repeated group empty)")

    return {
        "conversation_id": conversation_id,
        "title": title,
        "turns": turns,
        "raw_size": len(raw),
    }


def _smoke_test(paths: list[str]) -> None:
    for p in paths:
        path = Path(p)
        try:
            result = parse_export_file(path)
            print(
                f"OK   {path.name[:70]:<70} id={result['conversation_id']} "
                f"turns={len(result['turns'])} size={result['raw_size']}"
            )
        except GeminiExportParseError as e:
            print(f"FAIL {path.name[:70]:<70} {e}")


if __name__ == "__main__":
    _smoke_test(sys.argv[1:])
