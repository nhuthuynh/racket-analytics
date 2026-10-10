"""API binding of tests/features/labeller_admin.feature (ST-052b; FR-150, NFR-078;
api-sprint-03 §5.5). The operator CLI ``python -m racket.dataset.admin`` runs in-process
(``st.LABELLER_ADMIN``) against the real, committed Postgres; negative scenarios first."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
import sqlalchemy as sa
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

scenarios("labeller_admin.feature")


@pytest.fixture
def ctx(api: ApiDriver, committed_db: Any) -> dict[str, Any]:
    return {"api": api, "db": committed_db}


def _admin(*argv: str) -> int:
    rc: int = st.LABELLER_ADMIN.load()(list(argv))
    return rc


def _scalar(ctx: dict[str, Any], sql: str, **params: Any) -> Any:
    with ctx["db"].connect() as conn:
        return conn.execute(sa.text(sql), params).scalar_one()


def _roles(ctx: dict[str, Any], account_id: str) -> int:
    return int(_scalar(ctx, "SELECT count(*) FROM account_roles WHERE account_id = :a",
                       a=account_id))  # fmt: skip


def _is_labeller(ctx: dict[str, Any], account_id: str) -> bool:
    from racket.players import public as players

    with ctx["db"].connect() as conn:
        from sqlalchemy.orm import Session

        with Session(bind=conn) as session:
            return players.has_role(session, uuid.UUID(account_id), "labeller")


def _received(ctx: dict[str, Any], user: str) -> str:
    api = ctx["api"]
    match_id = api.run(sb.create_doubles(api.as_user(user), "ST-052b"))
    api.run(sb.receive_video(api.as_user(user), match_id))
    return str(match_id)


@given("Dana has a received match")
def received_match(ctx: dict[str, Any]) -> None:
    ctx["match"] = _received(ctx, "dana")


@given("Dana has deleted a received match")
def deleted_match(ctx: dict[str, Any]) -> None:
    ctx["match"] = _received(ctx, "dana")
    response = st.delete_match(ctx["api"], "dana", ctx["match"])
    assert response.status_code in st.statscontract.DELETE_OK, response.text


@given("an account id that belongs to no account")
def unknown_account(ctx: dict[str, Any]) -> None:
    ctx["account"] = str(uuid.uuid4())


@given("Dana has a received match with a consent record and a label session")
def match_with_label_rows(ctx: dict[str, Any]) -> None:
    from sqlalchemy.orm import Session

    from racket.dataset.repository import LabelRepository

    ctx["match"] = st.tagged_example(ctx["api"], "dana", "ST-052b purge")
    assert _admin("consent", "--match", ctx["match"], "--record", "CONSENT-TEAM-001") == 0
    with Session(bind=ctx["db"]) as session:
        LabelRepository(session).lock_or_create(
            uuid.UUID(ctx["match"]), uuid.UUID(st.me_id(ctx["api"], "dana")), datetime.now(UTC)
        )
        session.commit()
    assert _label_rows(ctx) == 2


@given("Ivy has deleted her account")
def deleted_account(ctx: dict[str, Any]) -> None:
    ctx["account"] = st.me_id(ctx["api"], "ivy")
    assert st.delete_account(ctx["api"], "ivy").status_code in st.statscontract.DELETE_OK


@given("Dana has a normal player account")
def normal_account(ctx: dict[str, Any]) -> None:
    ctx["account"] = st.me_id(ctx["api"], "dana")
    assert not _is_labeller(ctx, ctx["account"])


@when(parsers.parse('the operator records consent for it as "{reference}"'))
@when(parsers.parse('the operator records consent for it again as "{reference}"'))
def record_consent(ctx: dict[str, Any], reference: str) -> None:
    ctx["rc"] = _admin("consent", "--match", ctx["match"], "--record", reference)


@when(parsers.re(r"the operator grants (?:Ivy|Dana) the labeller role"))
def grant(ctx: dict[str, Any]) -> None:
    ctx["rc"] = _admin("grant-labeller", "--account", ctx["account"])


@when("the operator revokes Dana's labeller role")
def revoke(ctx: dict[str, Any]) -> None:
    assert _admin("revoke-labeller", "--account", ctx["account"]) == 0


@when("the operator revokes the labeller role of that account")
def revoke_unknown(ctx: dict[str, Any]) -> None:
    ctx["rc"] = _admin("revoke-labeller", "--account", ctx["account"])


@when("Dana deletes the match and the clean-up runs")
def delete_and_purge(ctx: dict[str, Any]) -> None:
    response = st.delete_match(ctx["api"], "dana", ctx["match"])
    assert response.status_code in st.statscontract.DELETE_OK, response.text
    st.run_purge_once()


@then("the operator is told the input was refused")
def refused(ctx: dict[str, Any]) -> None:
    assert ctx["rc"] == 1


@then("the match has no consent record")
def no_consent(ctx: dict[str, Any]) -> None:
    assert _scalar(ctx, "SELECT count(*) FROM label_consents WHERE match_id = :m",
                   m=ctx["match"]) == 0  # fmt: skip


@then(parsers.parse('the match has one consent record with reference "{reference}"'))
def one_consent(ctx: dict[str, Any], reference: str) -> None:
    assert ctx["rc"] == 0
    with ctx["db"].connect() as conn:
        rows = conn.execute(
            sa.text("SELECT reference FROM label_consents WHERE match_id = :m"), {"m": ctx["match"]}
        ).scalars().all()  # fmt: skip
    assert rows == [reference]


@then("Ivy holds no role")
def ivy_no_role(ctx: dict[str, Any]) -> None:
    assert _roles(ctx, ctx["account"]) == 0


@then("Dana is a labeller")
def is_labeller(ctx: dict[str, Any]) -> None:
    assert ctx["rc"] == 0
    assert _is_labeller(ctx, ctx["account"])


@then("Dana is not a labeller")
def is_not_labeller(ctx: dict[str, Any]) -> None:
    assert not _is_labeller(ctx, ctx["account"])
    assert _roles(ctx, ctx["account"]) == 0


def _label_rows(ctx: dict[str, Any]) -> int:
    return int(_scalar(
        ctx,
        "SELECT (SELECT count(*) FROM label_consents WHERE match_id = :m)"
        " + (SELECT count(*) FROM label_sessions WHERE match_id = :m)",
        m=ctx["match"],
    ))  # fmt: skip


@then("no consent record or label session of the match is left")
def nothing_left(ctx: dict[str, Any]) -> None:
    assert _label_rows(ctx) == 0
