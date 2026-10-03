"""``python -m racket.platform.migrate``: apply the Alembic migrations to ``DATABASE_URL``.

CI, Compose and production run this as a step before the API starts; only ``APP_ENV=dev``
also migrates at API startup. Safe to run concurrently (advisory lock in ``upgrade_to_head``).
"""

from __future__ import annotations

import os
import sys

from racket.platform.db import upgrade_to_head


def main() -> int:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("migrate: DATABASE_URL is not set", file=sys.stderr)
        return 2
    upgrade_to_head(url)
    print("migrate: database is at head")
    return 0


if __name__ == "__main__":
    sys.exit(main())
