"""What deleting an account erases and keeps (ST-051; FR-007; deletion-and-purge.md §3.2)."""

from __future__ import annotations

# Set to NULL in the DELETE /me transaction: the address is then free, and a new magic-link
# sign-in with it creates a new, empty account (PM-1 default).
# ``age_confirmed_at`` (FR-003, 0019) is personal data of the holder, so it goes too.
ERASED: dict[str, None] = {"email": None, "email_key": None, "username": None,
                           "display_name": None, "age_confirmed_at": None}  # fmt: skip
# Kept on the tombstone until the purge deletes the row, with the reason.
KEPT: dict[str, str] = {
    "id": "the purge finds the account's matches by it (pseudonymous)",
    "created_at": "not personal; removed with the row",
    "deleted_at": "the tombstone itself",
}
