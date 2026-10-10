"""Labeller administration CLI: ``python -m racket.dataset.admin`` (ST-052b; api-sprint-03
§5.5). Run by an operator in the ``api`` container with the app identity.

* ``grant-labeller --account <id>`` / ``revoke-labeller --account <id>``
* ``consent --match <id> --record <reference> [--by <operator account id>]``

Exit 0 done, 1 refused (unknown or deleted account or match, invalid id or reference), 2
usage. The consent is written under the live match row's ``FOR SHARE`` lock. Every input
is checked before the database is opened. Logs ids only, never the reference (NFR-057).
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from datetime import UTC, datetime
from typing import Any

from racket.dataset.full_tag import ConsentRecord, InvalidConsent
from racket.dataset.repository import LabelRepository
from racket.matches import public as matches
from racket.players import public as players

log = logging.getLogger("racket.dataset.admin")
OPERATOR = "operator-cli"  # recorded_by when no operator account id is given


def _session() -> Any:
    from racket.platform.db import engine_for, session_factory
    from racket.platform.logs import configure_logging
    from racket.platform.settings import Settings

    settings = Settings.from_env()
    configure_logging(settings.log_level)
    return session_factory(engine_for(settings.database_url))()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m racket.dataset.admin", exit_on_error=False)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("grant-labeller", "revoke-labeller"):
        commands.add_parser(name, exit_on_error=False).add_argument("--account", required=True)
    consent = commands.add_parser("consent", exit_on_error=False)
    consent.add_argument("--match", required=True)
    consent.add_argument("--record", required=True)
    consent.add_argument("--by", default=None)
    return parser


def _uuid(raw: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(sys.argv[1:] if argv is None else argv)
    except (argparse.ArgumentError, SystemExit):
        return 2
    now = datetime.now(UTC)
    if args.command == "consent":
        match_id = _uuid(args.match)
        by = args.by if args.by is not None else OPERATOR
        if args.by is not None and _uuid(args.by) is None:
            return 1
        try:
            record = ConsentRecord.create(str(match_id or ""), args.record, by, now)
        except InvalidConsent:
            return 1
        if match_id is None:
            return 1
        with _session() as session:
            if not matches.lock_live_match(session, match_id):  # held to the commit
                session.rollback()
                return 1
            LabelRepository(session).save_consent(record)
            session.commit()
        log.info("consent recorded", extra={"event": "label.consent_recorded",
                                            "match_id": str(match_id)})  # fmt: skip
        return 0
    account_id = _uuid(args.account)
    if account_id is None:
        return 1
    with _session() as session:
        if args.command == "grant-labeller":
            done = players.grant_role(session, account_id, "labeller", now)
        else:
            done = players.revoke_role(session, account_id, "labeller")
        if not done:
            session.rollback()
            return 1
        session.commit()
    log.info("role changed", extra={"event": f"label.{args.command.replace('-', '_')}",
                                     "account_id": str(account_id)})  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
