"""PDF-related text normalization utilities."""

from __future__ import annotations


def normalize_text_for_pdf(text: str, mode: str) -> str:
    """Normalize text for better PDF rendering.

    - Remove soft hyphens and non-breaking hyphens.
    - De-hyphenate line-wrapped words.
    - Optionally merge lines into paragraphs (para mode).

    Returns:
        str: Normalized text
    """
    # Remove soft hyphen and non-breaking hyphen
    text = text.replace("\u00ad", "").replace("\u2011", "-")

    # Work line by line
    lines = text.splitlines()

    # First pass: join hyphenated line breaks (word-\nnext -> wordnext)
    joined: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if line.endswith("-") and i + 1 < len(lines):
            nxt = lines[i + 1].lstrip()
            # Avoid joining when the hyphen is likely meaningful (e.g., bullets)
            if nxt and nxt[0].islower():
                line = line[:-1] + nxt
                i += 1
            else:
                joined.append(line)
                i += 1
                continue
        joined.append(line)
        i += 1

    if mode == "pre":
        return "\n".join(joined)

    # Paragraph mode: heuristically merge lines into paragraphs
    paras: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            paras.append(" ".join(buf).strip())
            buf.clear()

    for ln in joined:
        if not ln.strip():
            flush()
            continue
        if not buf:
            buf.append(ln.strip())
            continue
        prev = buf[-1]
        # If previous line ends with sentence punctuation, start a new sentence
        if prev.endswith((".", "!", "?", ":")):
            buf.append(ln.strip())
        else:
            # If next line starts lowercase/alphanumeric, consider it a wrapped
            # continuation
            first = ln.lstrip()[:1]
            if first and (first.islower() or first.isdigit()):
                buf[-1] = prev + " " + ln.strip()
            else:
                buf.append(ln.strip())
    flush()

    return "\n\n".join(paras)


# Backwards-compatible alias for older imports
_normalize_text_for_pdf = normalize_text_for_pdf
