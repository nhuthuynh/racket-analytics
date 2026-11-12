"""ST-082 (T5-RB-2, docs/security/threat-notes-sprint-05.md; ASVS 5.0 13.3.x): the build context of
every release image leaves out secrets and dev data. `.dockerignore` must keep each pinned entry so
a later edit cannot drop one; the negative cases prove the check fails when an entry goes."""

from __future__ import annotations

import pytest
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

DOCKERIGNORE = REPO_ROOT / ".dockerignore"

# The T5-RB-2 list, in the form `.dockerignore` writes it (`**/` reaches every directory).
PINNED = (
    "**/.git",
    "**/.env",
    "**/.env.*",
    "**/*.pem",
    "**/*.key",
    "infra/secrets",
    ".local",
    "fixtures",
    "docs",
)


def missing_entries(text: str) -> list[str]:
    """Pinned entries that `text` (a `.dockerignore`) does not hold as an exact, active line.

    A commented-out line (`# .local`) or a re-include (`!.local`) does not count: Docker would
    send the path. A pattern that only resembles an entry (`.local/cache`) does not count either."""
    raise NotImplementedError("ST-082: missing_entries (T5-RB-2)")


def test_the_dockerignore_holds_every_pinned_entry() -> None:
    assert missing_entries(DOCKERIGNORE.read_text()) == []


@pytest.mark.parametrize("entry", PINNED)
def test_a_copy_without_an_entry_fails(entry: str) -> None:
    lines = [line for line in DOCKERIGNORE.read_text().splitlines() if line.strip() != entry]
    assert missing_entries("\n".join(lines)) == [entry]


@pytest.mark.parametrize("replacement", ["# .local", ".local/cache", "  # .local  "])
def test_a_commented_or_narrowed_entry_fails(replacement: str) -> None:
    text = DOCKERIGNORE.read_text().replace("\n.local\n", f"\n{replacement}\n")
    assert missing_entries(text) == [".local"]


def test_a_re_include_after_the_entry_fails() -> None:
    """`!` lines are read in order: a later `!.local` sends `.local` again."""
    assert missing_entries(DOCKERIGNORE.read_text() + "\n!.local\n") == [".local"]


def test_surrounding_whitespace_still_counts_as_the_entry() -> None:
    text = DOCKERIGNORE.read_text().replace("\n.local\n", "\n  .local  \n")
    assert missing_entries(text) == []
