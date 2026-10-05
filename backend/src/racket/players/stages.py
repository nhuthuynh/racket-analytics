"""The ``send_sign_in_link`` job stage (ST-013; ADR 0025; api-sprint-01 §2.1).

``POST /auth/links`` answers 202 at once and leaves the address in the ``sign_in_requests``
outbox; this stage issues the link (only its SHA-256 is stored) and deletes the outbox row in
the runner's transaction, and sends the email once that transaction has committed (C-07). A
request already handled is a no-op (idempotent). It needs SMTP, so it runs in a worker outside
the media sandbox (``WORKER_STAGES``).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa

from racket.analysis_jobs.stage import StageContext
from racket.players.domain import MagicLinkToken, SignInEmail, sign_in_link_url
from racket.players.mailer import Mailer, SmtpMailer
from racket.players.models import sign_in_links, sign_in_requests
from racket.players.service import SEND_SIGN_IN_LINK

log = logging.getLogger("racket.players")


class SendSignInLinkStage:
    name = SEND_SIGN_IN_LINK
    failure_reason = "mail_failed"

    def __init__(self, mailer: Mailer | None = None) -> None:
        self._mailer = mailer

    def run(self, ctx: StageContext) -> None:
        request = ctx.session.execute(
            sa.select(sign_in_requests)
            .where(sign_in_requests.c.id == ctx.key.match_id)
            .with_for_update()
        ).one_or_none()
        if request is None:
            return  # already sent (a re-run after the commit), or the request was dropped
        ttl = timedelta(seconds=ctx.settings.magic_link_ttl_seconds)
        link, token = MagicLinkToken.issue(
            email_key=request.email_key, now=datetime.now(UTC), ttl=ttl
        )
        ctx.session.execute(
            sa.insert(sign_in_links).values(
                token_sha256=link.token_sha256,
                email_key=link.email_key,
                email=request.email,  # ADR 0032: carried to the exchange, nulled there
                created_at=link.created_at,
                expires_at=link.expires_at,
            )
        )
        ctx.session.execute(sa.delete(sign_in_requests).where(sign_in_requests.c.id == request.id))
        message = SignInEmail.compose(sign_in_link_url(ctx.settings.public_web_origin, token), ttl)
        mailer = self._mailer or SmtpMailer(ctx.settings.mail_smtp_url, ctx.settings.mail_from)
        address, key = request.email, link.email_key

        def send() -> None:
            """After the commit (C-07, PE-R3R-02): never mail a link whose row was rolled
            back. At-most-once: a send that fails after the runner's retries is logged
            (``job.after_commit_failed``) and the player asks for a new link."""
            mailer.send(address, message)
            log.info("sign-in email sent", extra={"event": "mail.sent", "email_key": key})

        ctx.after_commit.append(send)

    def on_failure(self, ctx: StageContext) -> None:
        """Drop the address: the player asks for a new link (data minimisation, judgment)."""
        ctx.session.execute(
            sa.delete(sign_in_requests).where(sign_in_requests.c.id == ctx.key.match_id)
        )
