"""Plain-text checks shared by every context at the API boundary (C-01, SEC-R6-S1-01).

Pure Python. A JSON string may carry characters that Postgres ``text`` cannot store (NUL) or
that UTF-8 cannot encode (lone surrogates); either one used to reach the driver and give a 500.
Testing-strategy rule L11: every free-text field is checked with this before it is stored.
"""

from __future__ import annotations

import unicodedata

# Cc: C0/C1 controls incl. NUL, tab and newline; Cs: lone surrogates; Zl/Zp: line and
# paragraph separators (sprint-02 §14.3.1 "line separator"). None belong in a one-line field.
REFUSED_CATEGORIES = frozenset({"Cc", "Cs", "Zl", "Zp"})


def is_plain_line(text: str) -> bool:
    """True when ``text`` holds no control, surrogate or line-separator character."""
    return not any(unicodedata.category(ch) in REFUSED_CATEGORIES for ch in text)
