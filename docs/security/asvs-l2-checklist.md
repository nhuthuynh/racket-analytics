# OWASP ASVS 5.0 Level 2 checklist

- **Status:** v1 release review in progress (NFR-050; story ST-078). V1-V5 assessed by ST-078a (2026-11-05); V6-V10 by ST-078b (2026-11-05); V11-V17 by ST-078c. Owner: security-privacy-engineer. Skeleton v0 (2026-10-03) was generated from the ASVS 5.0 chapter files listed under "Sources" with `scratchpad/asvs/gen.py` (not part of the repo), then annotated by hand.
- **Date:** 2026-11-05 (V1-V10); 2026-10-03 (skeleton, V11-V17 until their ticket merges)
- **Scope:** API, worker and PWA client, ASVS 5.0 **L1 + L2** [AQS/SEC-01], plus the L3 items we adopt: 5.2.4 and 5.2.6 (AQS Implications [AQS/SEC-02]) and 14.2.7 (NFR-066 [AQS/SEC-05]). Rows: 256.
- **Release gate:** at each release review, every applicable L2 row is either passing with evidence, or covered by an accepted-risk ADR with a human decider (NFR-050). The PO decides the `Fail` rows in the P19 residual-risk ADR (ST-078c drafts it).

## How to read this

- **Requirement text** is abridged from the fetched chapter, with "Verify that" removed. Read the full text in the source before you claim a pass.
- **Applies:** `Yes`; `N/A` (with the reason in Verification); `S1` and `TBD` are skeleton values that mean "not decided".
- **Status after the release review** (what `docs/security/tools/asvs_status.py` accepts):
  - `Pass`: the control is in place, and Verification names the evidence: a test id (`test_...`, a test file, `IT-nn-nn`) or a command in backticks with its result. Commands run from the repository root.
  - `Fail`: the control is missing or unproven. Owner names the fix ticket id or the residual-risk owner (`P19`, or the ADR id once it exists) and the finding id; the PO decides it (NFR-050.4).
  - `N/A`: only with Applies `N/A` and the reason.
- **Skeleton statuses** (`S0 planned`, `S0 partial`, `S0 documented`, `S1`, `Later`, `Open (F-n)`, `Not assessed`) are planning notes from Sprint 0. The tool counts every one of them as **not assessed**, so a chapter passes only when none is left.
- **Evidence run for V1-V5:** every named backend test passed against local Postgres 16 and SeaweedFS (and Mailpit for the sign-in tests) at `bf0afb16`; the E2E specs passed in CI run 41929624496 (E2E chromium job) at the same commit; the commands were run on that tree. Details and the exact commands: `docs/sprints/05/decisions/ST-078a.md`.
- **Evidence run for V6-V10:** every named backend test passed against local Postgres 16, SeaweedFS and Mailpit at `734d4832` (186 passed, 0 skipped); `web/e2e/sprint-01/sign-out.spec.ts` passed in CI run 41975999573 (E2E chromium job) at the same commit; every command in the rows was run on that tree. Details: `docs/sprints/05/decisions/ST-078b.md`.

### Status counts

The counts are printed by the tool, so they cannot drift from the rows (the hand-kept summary of the skeleton did):

```
python3 docs/security/tools/asvs_status.py docs/security/asvs-l2-checklist.md --level 2 \
  --fail-on not-assessed,fail-without-owner,pass-without-evidence --chapters V1-V10
```

## Sources

The verified research registered only V2, V5, V8, V13, V14 and V16 (AQS/SEC-02 to SEC-07). To cite item IDs from every chapter, the security-privacy-engineer's session fetched all 17 ASVS 5.0 chapter files from the publisher's repository on 2026-10-03 (`curl` → HTTP 200 each). These are the same repository and branch as [AQS/SEC-01]. Request for the PE or BA: add V1, V3, V4, V6, V7, V9, V10, V11, V12, V15 and V17 to the AQS source register as SEC-13 onward.

| Chapter | URL | sha256 (prefix) of the fetched file |
|---|---|---|
| V1 Encoding and Sanitization | https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x10-V1-Encoding-and-Sanitization.md | `8c0e36a42c3cbf71…` |
| V2 Validation and Business Logic | https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x11-V2-Validation-and-Business-Logic.md | `70ad0f68df22ddd8…` |
| V3 Web Frontend Security | https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x12-V3-Web-Frontend-Security.md | `0284ec2ed96614aa…` |
| V4 API and Web Service | https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x13-V4-API-and-Web-Service.md | `efcadbf5ad78fb97…` |
| V5 File Handling | https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x14-V5-File-Handling.md | `079a51123e5156a5…` |
| V6 Authentication | https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x15-V6-Authentication.md | `e1e0aaa15e48f794…` |
| V7 Session Management | https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x16-V7-Session-Management.md | `4aec329f2642ae75…` |
| V8 Authorization | https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x17-V8-Authorization.md | `60c188b1703cab20…` |
| V9 Self-contained Tokens | https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x18-V9-Self-contained-Tokens.md | `5ae72b67555045ae…` |
| V10 OAuth and OIDC | https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x19-V10-OAuth-and-OIDC.md | `2da443986ba40987…` |
| V11 Cryptography | https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x20-V11-Cryptography.md | `a64f3f2dc6f53565…` |
| V12 Secure Communication | https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x21-V12-Secure-Communication.md | `6c8407229aa12349…` |
| V13 Configuration | https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x22-V13-Configuration.md | `f66ef1306eba07e0…` |
| V14 Data Protection | https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x23-V14-Data-Protection.md | `a9ba33b7c77379fe…` |
| V15 Secure Coding and Architecture | https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x24-V15-Secure-Coding-and-Architecture.md | `4c068e82b157159e…` |
| V16 Security Logging and Error Handling | https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x25-V16-Security-Logging-and-Error-Handling.md | `23b0c0d4a54cc62a…` |
| V17 WebRTC | https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x26-V17-WebRTC.md | `29a55aed304efc92…` |

## Checklist

### V1 Encoding and Sanitization

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 1.1.1 | 2 | input is decoded or unescaped into a canonical form only once, it is only decoded when encoded data in that form is e… | Yes | Pass | BE | no hand decoding of request data; Starlette decodes once. `grep -rn unquote backend/src web/src` → no match |
| 1.1.2 | 2 | the application performs output encoding and escaping either as a final step before being used by the interpreter for… | Yes | Pass | BE, FE | encoding at the last step only: React escapes at render, FastAPI serialises JSON at the response; `grep -rn dangerouslySetInnerHTML web/src` → no match; `web/e2e/sprint-01/threat-controls.spec.ts` T-UV-10 |
| 1.2.1 | 1 | output encoding for an HTTP response, HTML document, or XML document is relevant for the context required, such as en… | Yes | Pass | FE ST-010 | `web/e2e/sprint-01/threat-controls.spec.ts` T-UV-10 (markup in a nickname and a file name renders as text); `grep -rn dangerouslySetInnerHTML web/src` → no match |
| 1.2.2 | 1 | when dynamically building URLs, untrusted data is encoded according to its context (e.g., URL encoding or base64url e… | Yes | Pass | FE | ids enter paths only after `isPublicId`/`METRIC_ID_RE` checks, cursors through `encodeURIComponent` (`web/src/lib/api/client.ts` `matchPath`, `metricPath`); `grep -rn encodeURIComponent web/src/lib` → cursor and session ids |
| 1.2.3 | 1 | output encoding or escaping is used when dynamically building JavaScript content (including JSON), to avoid changing … | Yes | Pass | FE ST-010 | no script built from data; CSP nonce and no `unsafe-inline`/`unsafe-eval` in production: `web/tests/unit/csp.test.ts`; `grep -rnE "<script" web/src` → no match |
| 1.2.4 | 1 | data selection or database queries (e.g., SQL, HQL, NoSQL, Cypher) use parameterized queries, ORMs, entity frameworks… | Yes | Pass | BE ST-005/006 | bound parameters only: `grep -rnE "(text|execute)\(\s*f[\"']" backend/src --exclude-dir=migrations` → no match (migration f-strings interpolate module constants, no input); `test_it_02_10_every_generated_value_is_still_bad_where_the_server_reads_it` |
| 1.2.5 | 1 | the application protects against OS command injection and that operating system calls use parameterized OS queries or… | Yes | Pass | ML ST-009 | `test_a_probe_gets_only_the_fixed_argv` (`backend/tests/integration/video_ingest/test_probe_sandbox.py`); `grep -rn "shell=True\|os.system\|os.popen" backend/src` → no match |
| 1.2.6 | 2 | the application protects against LDAP injection vulnerabilities, or that specific security controls to prevent LDAP i… | N/A | N/A | — | no LDAP |
| 1.2.7 | 2 | the application is protected against XPath injection attacks by using query parameterization or precompiled queries. | N/A | N/A | — | no XPath |
| 1.2.8 | 2 | LaTeX processors are configured securely (such as not using the "--shell-escape" flag) and an allowlist of commands i… | N/A | N/A | — | no LaTeX |
| 1.2.9 | 2 | the application escapes special characters in regular expressions (typically using a backslash) to prevent them from … | Yes | Pass | BE, FE | no pattern is built from user input: `grep -rnE "new RegExp\(" web/src` → no match; the one dynamic Python pattern (`coaching/drills/schema_check.py:92`) comes from the repo's drill schema |
| 1.3.1 | 1 | all untrusted HTML input from WYSIWYG editors or similar is sanitized using a well-known and secure HTML sanitization… | N/A | N/A | — | no rich-text or HTML input anywhere; every user string is rendered as text (1.2.1) |
| 1.3.2 | 1 | the application avoids the use of eval() or other dynamic code execution features such as Spring Expression Language … | Yes | Pass | BE, FE | `grep -rnE "(^|[^.A-Za-z0-9_])(eval|exec)\(|new Function\(" backend/src web/src` → no match; production CSP forbids `unsafe-eval` (`web/tests/unit/csp.test.ts`) |
| 1.3.3 | 2 | data being passed to a potentially dangerous context is sanitized beforehand to enforce safety measures, such as only… | Yes | Pass | BE | object keys and stored text are checked before use: `test_it_02_10_bad_characters_in_an_object_key_are_a_4xx_and_write_nothing`; `test_normalise_email_never_raises_and_output_is_well_formed` |
| 1.3.4 | 2 | user-supplied Scalable Vector Graphics (SVG) scriptable content is validated or sanitized to contain only tags and at… | N/A | N/A | — | no SVG upload |
| 1.3.5 | 2 | the application sanitizes or disables user-supplied scriptable or expression template language content, such as Markd… | N/A | N/A | — | no user-supplied Markdown or template content; drill and guide text is repository content (`content/drills/`), not user input |
| 1.3.6 | 2 | the application protects against Server-side Request Forgery (SSRF) attacks, by validating untrusted data against an … | Yes | Pass | ML ST-009 | F-2 closed (SEC-R1-01): `test_a_manifest_disguised_as_a_video_fetches_nothing`, `test_the_input_format_allowlist_is_exactly_the_mp4_family`, `test_public_internet_is_blocked_from_the_worker` |
| 1.3.7 | 2 | the application protects against template injection attacks by not allowing templates to be built based on untrusted … | Yes | Pass | BE | no template engine; mail bodies are fixed strings: `grep -rniE "jinja|string\.Template" backend/src` → no match |
| 1.3.8 | 2 | the application appropriately sanitizes untrusted input before use in Java Naming and Directory Interface (JNDI) quer… | N/A | N/A | — | no JNDI |
| 1.3.9 | 2 | the application sanitizes content before it is sent to memcache to prevent injection attacks. | N/A | N/A | — | no memcache |
| 1.3.10 | 2 | format strings which might resolve in an unexpected or malicious way when used are sanitized before being processed. | Yes | Pass | BE | no format string from input; logging uses `%`-arguments: `grep -rn "\.format(" backend/src` → no match |
| 1.3.11 | 2 | the application sanitizes user input before passing to mail systems to protect against SMTP or IMAP injection. | Yes | Pass | BE (magic links) | `To` is the normalised address (no control or line-separator character), subject fixed, built with `EmailMessage`: `test_normalise_email_never_raises_and_output_is_well_formed`, `test_malformed_addresses_are_refused` |
| 1.4.1 | 2 | the application uses memory-safe string, safer memory copy and pointer arithmetic to detect or prevent stack, buffer,… | N/A | N/A | — | no unmanaged code of ours (Python, TypeScript); the C parser we run (ffprobe) is a dependency, sandboxed under rlimits (ADR 0020) and covered by V15 dependency rows |
| 1.4.2 | 2 | sign, range, and input validation techniques are used to prevent integer overflows. | Yes | Pass | BE | numbers are range-checked before they reach bigint columns: `test_last_modified_out_of_bigint_range_is_a_400_and_stores_nothing`, `test_non_integer_offset_is_400` |
| 1.4.3 | 2 | dynamically allocated memory and resources are released, and that references or pointers to freed memory are removed … | N/A | N/A | — | garbage-collected runtimes only (as 1.4.1); ffprobe processes are killed and reaped (`test_a_hanging_probe_is_killed_at_the_wall_clock_limit`) |
| 1.5.1 | 1 | the application configures XML parsers to use a restrictive configuration and that unsafe features such as resolving … | N/A | N/A | — | no XML parsing (ffprobe JSON output) |
| 1.5.2 | 2 | deserialization of untrusted data enforces safe input handling, such as using an allowlist of object types or restric… | Yes | Pass | BE | JSON into closed Pydantic schemas only: `grep -rnE "import (pickle|marshal|shelve)|yaml\.load|jsonpickle" backend/src` → no match; `test_unknown_request_field_is_rejected` |

### V2 Validation and Business Logic

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 2.1.1 | 1 | the application's documentation defines input validation rules for how to check the validity of data items against an… | Yes | Pass | PE | field rules documented: `grep -n "^### 5.3 Validation paths" docs/architecture/api-sprint-01.md` → line 162; api-sprint-00 §5-§6 |
| 2.1.2 | 2 | the application's documentation defines how to validate the logical and contextual consistency of combined data items… | Yes | Pass | PE, BA | combined-item rules (format × participants × `is_me`) documented in api-sprint-01 §5.3 and FR scenarios; `backend/tests/features/test_match_setup.py` (`test_wrong_participants_for_the_format`) |
| 2.1.3 | 2 | expectations for business logic limits and validations are documented, including both per-user and globally across th… | Yes | Fail | P19 (residual, SEC-S5-ASVS-01) | per-account and per-IP limits are documented (api-sprint-01 §2.4, api-sprint-02 §3 Limits, api-sprint-04 §7); no application-wide (global) limit is documented, e.g. total storage or daily probe jobs: `grep -rniE "global (limit|quota|cap)" docs/architecture` → no match |
| 2.2.1 | 1 | input is validated to enforce business or functional expectations for that input. This should either use positive val… | Yes | Pass | BE ST-006/008 | `test_unknown_request_field_is_rejected`, `test_unknown_or_server_owned_fields_are_refused_without_echo`, `test_bad_creation_headers_are_refused` |
| 2.2.2 | 1 | the application is designed to enforce input validation at a trusted service layer. While client-side validation impr… | Yes | Pass | BE | the API checks every rule itself (the tests call the API, not the client): `test_unknown_request_field_is_rejected`, `test_it_02_10_every_generated_value_is_still_bad_where_the_server_reads_it` |
| 2.2.3 | 2 | the application ensures that combinations of related data items are reasonable according to the pre-defined rules. | Yes | Pass | BE ST-016 | `backend/tests/features/test_match_setup.py` (`test_wrong_participants_for_the_format`, 3 combinations) |
| 2.3.1 | 1 | the application will only process business logic flows for the same user in the expected sequential step order and wi… | Yes | Pass | BE ST-008 | IT-00-08: `test_probe_enqueued_only_after_last_byte`; `test_it_01_07_patch_after_expiry_is_refused_and_others_still_get_404` |
| 2.3.2 | 2 | business logic limits are implemented per the application's documentation to avoid business logic flaws being exploit… | Yes | Pass | BE ST-072a | F-3 closed: `test_it_04_09_a_burst_of_50_match_creations_accepts_exactly_10`, `test_it_04_09_a_burst_of_50_uploads_never_passes_the_storage_quota`, `test_it_02_13_parallel_commands_never_pass_the_per_account_rate` |
| 2.3.3 | 2 | transactions are being used at the business logic level such that either a business logic operation succeeds in its e… | Yes | Pass | BE ST-007/008 | `test_a_failure_after_the_lock_rolls_everything_back`, `test_it_01_06_corrupted_chunk_is_refused_and_the_offset_is_unchanged` |
| 2.3.4 | 2 | business logic level locking mechanisms are used to ensure that limited quantity resources (such as theater seats or … | Yes | Pass | BE ST-008 | T-UP-3: `test_patch_while_another_patch_holds_the_row_is_409_and_unchanged`; `test_it_02_11_parallel_upload_creations_never_pass_the_open_upload_quota` |
| 2.4.1 | 2 | anti-automation controls are in place to protect against excessive calls to application functions that could lead to … | Yes | Pass | BE + SRE | F-3 closed: `test_it_01_02_sixth_link_in_ten_minutes_is_rate_limited_with_a_retry_time`, `test_guessing_tokens_is_rate_limited`, `test_it_04_09_the_61st_create_from_one_ip_is_refused_and_a_forged_xff_does_not_rotate_it` |

### V3 Web Frontend Security

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 3.2.1 | 1 | security controls are in place to prevent browsers from rendering content or functionality in HTTP responses in an in… | Yes | Pass | BE, FE, SRE | typed bodies plus `nosniff` everywhere, media with `CSP: sandbox`: IT-00-14 (`backend/tests/integration/test_it_00_14_security_headers.py`), `test_it_02_15_the_match_video_is_served_as_video_mp4`, `test_presigned_media_sets_safe_response_header` |
| 3.2.2 | 1 | content intended to be displayed as text, rather than rendered as HTML, is handled using safe rendering functions (su… | Yes | Pass | FE ST-010 | `web/e2e/sprint-01/threat-controls.spec.ts` T-UV-10; `grep -rn dangerouslySetInnerHTML web/src` → no match |
| 3.3.1 | 1 | cookies have the 'Secure' attribute set, and if the '\__Host-' prefix is not used for the cookie name, the '__Secure-… | Yes | Pass | BE ST-006 | `test_no_setting_drops_secure_outside_test` (`backend/tests/unit/players/test_session_cookie_policy.py`) |
| 3.3.2 | 2 | each cookie's 'SameSite' attribute value is set according to the purpose of the cookie, to limit exposure to user int… | Yes | Pass | BE ST-006 | `SameSite=Lax`: `test_outside_test_the_cookie_meets_the_host_prefix_rules` |
| 3.3.3 | 2 | cookies have the '__Host-' prefix for the cookie name unless they are explicitly designed to be shared with other hos… | Yes | Pass | BE ST-006 | `__Host-racket_session`, `Path=/`, no `Domain`: `test_outside_test_the_cookie_meets_the_host_prefix_rules` |
| 3.3.4 | 2 | if the value of a cookie is not meant to be accessible to client-side scripts (such as a session token), the cookie m… | Yes | Pass | BE ST-006 | `HttpOnly`: `test_outside_test_the_cookie_meets_the_host_prefix_rules` |
| 3.4.1 | 1 | a Strict-Transport-Security header field is included on all responses to enforce an HTTP Strict Transport Security (H… | Yes | Fail | P19 (residual: no public origin exists; ADR 0034 E1 is the fix at the first deployment) | dev `web-tls` sends no HSTS on purpose: `test_dev_proxy_sends_no_hsts`; the criterion exists only on paper: `test_deployment_edge_adr_has_an_hsts_criterion_with_at_least_one_year` |
| 3.4.2 | 1 | the Cross-Origin Resource Sharing (CORS) Access-Control-Allow-Origin header field is a fixed value by the application… | Yes | Pass | PE/BE, SRE | no CORS: one origin with the `/api` rewrite; the media route adds no `Access-Control-*`: `test_media_route_adds_no_cross_origin_access`; `grep -rni "access-control-allow-origin" backend/src web/src` → no match |
| 3.4.3 | 2 | HTTP responses include a Content-Security-Policy response header field which defines directives to ensure the browser… | Yes | Pass | FE ST-010 | `web/e2e/security-headers.spec.ts` (`default-src 'self'`; CI run 41929624496 E2E chromium job, success at `bf0afb16`); `web/tests/unit/csp.test.ts` |
| 3.4.4 | 2 | all HTTP responses contain an 'X-Content-Type-Options: nosniff' header field. This instructs browsers not to use cont… | Yes | Pass | BE ST-005, FE ST-010 | IT-00-14 (`test_health_json_has_baseline_headers`, `test_error_response_has_baseline_headers`); `web/e2e/security-headers.spec.ts` |
| 3.4.5 | 2 | the application sets a referrer policy to prevent leakage of technically sensitive data to third-party services via t… | Yes | Pass | BE ST-005, FE ST-010 | `Referrer-Policy: no-referrer` on API and web: `grep -n "referrer-policy" -i backend/src/racket/platform/http.py web/next.config.ts` → one line each. No test pins it yet (SEC-S5-ASVS-03, asked of ST-078e's header IT) |
| 3.4.6 | 2 | the web application uses the frame-ancestors directive of the Content-Security-Policy header field for every HTTP res… | Yes | Pass | FE ST-010 | `frame-ancestors 'none'`: `web/e2e/security-headers.spec.ts`, `web/tests/unit/csp.test.ts`; API `X-Frame-Options: DENY` in IT-00-14 |
| 3.5.1 | 1 | Verify that, if the application does not rely on the CORS preflight mechanism to prevent disallowed cross-origin requ… | Yes | Pass | BE ST-006 | Origin allowlist on state-changing methods plus SameSite: `test_foreign_origin_cannot_change_state`, `test_t_ml_12_a_foreign_origin_cannot_request_a_link_or_sign_in` |
| 3.5.2 | 1 | Verify that, if the application relies on the CORS preflight mechanism to prevent disallowed cross-origin use of sens… | N/A | N/A | — | the application does not rely on CORS preflight; it uses the Origin allowlist of 3.5.1 (`backend/src/racket/platform/http.py` `ForbiddenOrigin`) |
| 3.5.3 | 1 | HTTP requests to sensitive functionality use appropriate HTTP methods such as POST, PUT, PATCH, or DELETE, and not me… | Yes | Pass | BE | changes use POST/PATCH/PUT/DELETE, and those are the methods the Origin check guards: `test_foreign_origin_cannot_change_state`; `grep -rn "_STATE_CHANGING =" backend/src/racket/platform/http.py` → POST, PUT, PATCH, DELETE. A GET that regenerates a stale plan only re-derives the caller's own read model (judgment) |
| 3.5.4 | 2 | separate applications are hosted on different hostnames to leverage the restrictions provided by same-origin policy, … | Yes | Pass | SRE | one application on one origin (web + `/api`); user media is not a separate app but bytes served with `nosniff`, `CSP: sandbox` and no cookies to the store: `test_presigned_media_sets_safe_response_header`, `test_media_route_never_sends_credentials_to_the_store` |
| 3.5.5 | 2 | messages received by the postMessage interface are discarded if the origin of the message is not trusted, or if the s… | N/A | N/A | — | no `postMessage` use: `grep -rnE "postMessage|addEventListener\(['\"]message" web/src web/public` → no match (re-check if added) |
| 3.7.1 | 2 | the application only uses client-side technologies which are still supported and considered secure. Examples of techn… | Yes | Pass | FE | no plugin technology: `grep -rnE "<object|<embed|<applet|<iframe" web/src` → no match; browsers per NFR-024 run in CI (E2E chromium and webkit jobs, run 41929624496) |
| 3.7.2 | 2 | the application will only automatically redirect the user to a different hostname or domain (which is not controlled … | Yes | Pass | FE/BE | no redirect target comes from input: `grep -rnE "location\.(assign|replace)\(|router\.(push|replace)\(|redirect\(" web/src` → literal app paths or `/matches/${id}`; `test_link_points_at_the_configured_origin_not_the_host_header` |

### V4 API and Web Service

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 4.1.1 | 1 | every HTTP response with a message body contains a Content-Type header field that matches the actual content of the r… | Yes | Pass | BE ST-005 | `test_it_02_15_the_match_video_is_served_as_video_mp4`, `test_a_multipart_original_is_created_with_a_video_content_type`; JSON bodies through `JSONResponse` (IT-00-14) |
| 4.1.2 | 2 | only user-facing endpoints (intended for manual web-browser access) automatically redirect from HTTP to HTTPS, while … | Yes | Fail | P19 (residual, SEC-S5-ASVS-02; fix in ADR 0034 E2 before the first deployment) | no public origin exists; ADR 0034 E2 redirects all plain http to https, which would include `/api` (4.1.2 wants API calls refused, not redirected): `grep -n "^| E2" docs/decisions/0034-deployment-edge-acceptance-criteria.md` |
| 4.1.3 | 2 | any HTTP header field used by the application and set by an intermediary layer, such as a load balancer, a web proxy,… | Yes | Pass | SRE, BE | the edge replaces `X-Forwarded-For` and the API counts trusted hops: `test_client_ip_counts_trusted_hops_from_the_right`, `test_spoofed_forwarded_for_does_not_reset_the_ip_limit`, `test_it_04_09_the_61st_create_from_one_ip_is_refused_and_a_forged_xff_does_not_rotate_it` |
| 4.2.1 | 2 | all application components (including load balancers, firewalls, and application servers) determine boundaries of inc… | Yes | Fail | P19 (residual, SEC-S5-ASVS-04; criterion to add to ADR 0034) | no test sends ambiguous framing (`Content-Length` with `Transfer-Encoding`) through `web-tls` to uvicorn, and ADR 0034 has no framing criterion: `grep -niE "transfer-encoding|smuggl" docs/decisions/0034-deployment-edge-acceptance-criteria.md infra/tests/*.py` → no match |
| 4.3.1 | 2 | a query allowlist, depth limiting, amount limiting, or query cost analysis is used to prevent GraphQL or data layer e… | N/A | N/A | — | no GraphQL: `grep -rniE "graphql" backend/src web/src` → no match |
| 4.3.2 | 2 | GraphQL introspection queries are disabled in the production environment unless the GraphQL API is meant to be used b… | N/A | N/A | — | no GraphQL (4.3.1) |
| 4.4.1 | 1 | WebSocket over TLS (WSS) is used for all WebSocket connections. | N/A | N/A | — | no WebSockets: `grep -rniE "websocket" backend/src web/src` → no match |
| 4.4.2 | 2 | Verify that, during the initial HTTP WebSocket handshake, the Origin header field is checked against a list of origin… | N/A | N/A | — | no WebSockets (4.4.1) |
| 4.4.3 | 2 | Verify that, if the application's standard session management cannot be used, dedicated tokens are being used for thi… | N/A | N/A | — | no WebSockets (4.4.1) |
| 4.4.4 | 2 | dedicated WebSocket session management tokens are initially obtained or validated through the previously authenticate… | N/A | N/A | — | no WebSockets (4.4.1) |

### V5 File Handling

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 5.1.1 | 2 | the documentation defines the permitted file types, expected file extensions, and maximum size (including unpacked si… | Yes | Pass | PE/BA | FR-023 and `GET /upload-policy` document MP4/MOV, H.264/HEVC, size and duration caps: `grep -n "^#### FR-023" docs/requirements/functional-requirements.md`; `test_discovery_lists_version_extension_and_max_size` |
| 5.2.1 | 1 | the application will only accept files of a size which it can process without causing a loss of performance or a deni… | Yes | Pass | BE ST-008 | `test_bad_creation_headers_are_refused` (`Upload-Length` over the cap → 413), `test_chunk_above_the_chunk_limit_is_413` |
| 5.2.2 | 1 | when the application accepts a file, either on its own or within an archive such as a zip file, it checks if the file… | Yes | Pass | BE/ML FR-023 | first-chunk atom check and probe of the stored object: `test_content_that_is_not_mp4_or_mov_is_not_a_video`, `test_other_containers_codecs_or_huge_frames_are_unsupported` |
| 5.2.3 | 2 | the application checks compressed files (e.g., zip, gz, docx, odt) against maximum allowed uncompressed size and agai… | N/A | N/A | — | no compressed archives accepted |
| 5.2.4 | 3 (L3 adopted) | a file size quota and maximum number of files per user are enforced to ensure that a single user cannot fill up the s… | Yes | Pass | BE ST-072a | F-3 closed: `test_a_fourth_open_upload_is_refused_by_the_quota`, `test_it_04_09_a_burst_of_50_uploads_never_passes_the_storage_quota` |
| 5.2.6 | 3 (L3 adopted) | the application rejects uploaded images with a pixel size larger than the maximum allowed, to prevent pixel flood att… | Yes | Pass | ML | `test_frame_pixel_cap_boundaries` (`backend/tests/unit/video_ingest/test_upload_policy.py`) |
| 5.3.1 | 1 | files uploaded or generated by untrusted input and stored in a public folder, are not executed as server-side program… | Yes | Pass | BE/SRE | private bucket, served only as presigned GET/HEAD with `nosniff` and `CSP: sandbox`: `test_media_route_forwards_only_presigned_get_and_head`, `test_presigned_media_sets_safe_response_header` |
| 5.3.2 | 1 | when the application creates file paths for file operations, instead of user-submitted filenames, it uses internally … | Yes | Pass | BE ST-008 | `test_t_uv_9_the_file_name_is_in_no_log_line_and_no_object_key` |
| 5.4.1 | 2 | the application validates or ignores user-submitted filenames, including in a JSON, JSONP, or URL parameter and speci… | Yes | Pass | BE | the user's file name is ignored, never stored or used: `test_t_uv_9_the_file_name_is_in_no_log_line_and_no_object_key` |
| 5.4.2 | 2 | file names served (e.g., in HTTP response header fields or email attachments) are encoded or sanitized (e.g., followi… | Yes | Pass | BE | the only served file name is generated from a UUID: `grep -n "Content-Disposition" backend/src/racket/dataset/api.py` → `labels-{match_id}.json`; media is served inline with no name |
| 5.4.3 | 2 | files obtained from untrusted sources are scanned by antivirus scanners to prevent serving of known malicious content. | Yes | Fail | P19 (residual, threat-model-v0 "AV scanning"; PO decides tool or acceptance before beta) | no antivirus scan of uploads: `grep -rniE "clamav|antivirus" backend/src infra` → no match. Mitigations today: MP4/MOV only, probe in a sandbox, never executed, served with `nosniff` and `CSP: sandbox` (5.3.1) |

### V6 Authentication

Passwords are never used (FR-001), so 6.2.x is N/A. R1 has one production pathway, the emailed single-use link (ADR 0025), plus the dev identity provider in dev and test only. Assessed 2026-11-05 (ST-078b).

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 6.1.1 | 1 | application documentation defines how controls such as rate limiting, anti-automation, and adaptive response, are use… | Yes | Fail | P19 (residual, SEC-S5-ASVS-07) | the limits and their configuration are documented (`grep -n "^### 2.4 Rate limits" docs/architecture/api-sprint-01.md` → line 74; ADR 0025 "Rate limits"), but nothing says how they avoid malicious lockout of an address (the per-address limit of 5 per 10 min can be spent by anyone who knows it): `grep -rniE "lockout|locked out|lock out" docs/architecture docs/decisions` → no match |
| 6.1.2 | 2 | a list of context-specific words is documented in order to prevent their use in passwords. The list could include per… | N/A | N/A | — | no passwords (FR-001): `grep -rniE "webauthn|passkey|password" backend/src/racket/players` → no match |
| 6.1.3 | 2 | Verify that, if the application includes multiple authentication pathways, these are all documented together with the… | Yes | Pass | PE, security | two pathways, both documented with their controls: magic link (api-sprint-01 §2, ADR 0025) and the dev provider, dev/test only (api-sprint-00 §2): `grep -n "^| Availability" docs/architecture/api-sprint-00.md` → line 42; passkeys are not built (ADR 0031) |
| 6.2.1 | 1 | user set passwords are at least 8 characters in length although a minimum of 15 characters is strongly recommended. | N/A | N/A | — | no passwords (FR-001) |
| 6.2.2 | 1 | users can change their password. | N/A | N/A | — | no passwords (FR-001) |
| 6.2.3 | 1 | password change functionality requires the user's current and new password. | N/A | N/A | — | no passwords (FR-001) |
| 6.2.4 | 1 | passwords submitted during account registration or password change are checked against an available set of, at least,… | N/A | N/A | — | no passwords (FR-001) |
| 6.2.5 | 1 | passwords of any composition can be used, without rules limiting the type of characters permitted. There must be no r… | N/A | N/A | — | no passwords (FR-001) |
| 6.2.6 | 1 | password input fields use type=password to mask the entry. Applications may allow the user to temporarily view the en… | N/A | N/A | — | no passwords (FR-001) |
| 6.2.7 | 1 | "paste" functionality, browser password helpers, and external password managers are permitted. | N/A | N/A | — | no passwords (FR-001) |
| 6.2.8 | 1 | the application verifies the user's password exactly as received from the user, without any modifications such as tru… | N/A | N/A | — | no passwords (FR-001) |
| 6.2.9 | 2 | passwords of at least 64 characters are permitted. | N/A | N/A | — | no passwords (FR-001) |
| 6.2.10 | 2 | a user's password stays valid until it is discovered to be compromised or the user rotates it. The application must n… | N/A | N/A | — | no passwords (FR-001) |
| 6.2.11 | 2 | the documented list of context specific words is used to prevent easy to guess passwords being created. | N/A | N/A | — | no passwords (FR-001) |
| 6.2.12 | 2 | passwords submitted during account registration or password changes are checked against a set of breached passwords. | N/A | N/A | — | no passwords (FR-001) |
| 6.3.1 | 1 | controls to prevent attacks such as credential stuffing and password brute force are implemented according to the app… | Yes | Pass | BE ST-013/014 | per-address, per-IP and exchange limits as documented in api-sprint-01 §2.4: `test_it_01_02_sixth_link_in_ten_minutes_is_rate_limited_with_a_retry_time`, `test_guessing_tokens_is_rate_limited`, `test_spoofed_forwarded_for_does_not_reset_the_ip_limit` |
| 6.3.2 | 1 | default user accounts (e.g., "root", "admin", or "sa") are not present in the application or are disabled. | Yes | Pass | BE ST-006 | seeded users exist only with the dev provider, which is refused outside dev/test: `test_prod_with_dev_identity_is_refused`, `test_dev_identity_is_refused_outside_dev_and_test`, `test_staging_starts_with_dev_identity_off`, `test_dev_routes_do_not_exist_when_the_dev_provider_is_off` |
| 6.3.3 | 2 | either a multi-factor authentication mechanism or a combination of single-factor authentication mechanisms, must be u… | Yes | Fail | ADR 0031 (accepted residual risk, PO 2026-10-06; re-review before any real-user beta) | one factor only (the emailed link); passkeys are not built: `grep -rniE "webauthn|passkey" backend/src/racket/players` → no match. Mitigations are ADR 0031's conditions (single-use link, 30 d / 7 d session limits, sign-out) |
| 6.3.4 | 2 | Verify that, if the application includes multiple authentication pathways, there are no undocumented pathways and tha… | Yes | Pass | BE, security | every session is set by one helper with three callers, all documented: `grep -rn "set_session_cookie(" backend/src` → `api.py:172` exchange, `:203` dev sign-in, `:293` age confirmation of a pending link sign-in (FR-003); the dev route is absent unless enabled: `test_dev_routes_do_not_exist_when_the_dev_provider_is_off`, `test_dev_identity_is_refused_outside_dev_and_test` |
| 6.4.1 | 1 | system generated initial passwords or activation codes are securely randomly generated, follow the existing password … | Yes | Pass | BE ST-013 | the link token is 32 CSPRNG bytes and expires or is spent at first use: `test_the_token_is_43_base64url_characters_and_only_its_hash_is_kept`, `test_a_link_at_or_past_its_lifetime_is_refused`, `test_it_01_01_link_signs_in_once_and_reuse_fails`; it never becomes a long-term secret (the session is a new token, 7.2.4) |
| 6.4.2 | 1 | password hints or knowledge-based authentication (so-called "secret questions") are not present. | Yes | Pass | BE, FE | no hints or secret questions: `grep -rniE "secret.?question|password.?hint|security.?question" backend/src web/src` → no match |
| 6.4.3 | 2 | a secure process for resetting a forgotten password is implemented, that does not bypass any enabled multi-factor aut… | N/A | N/A | — | no passwords and no MFA: a forgotten sign-in is a new link request, the normal pathway (6.3.1) |
| 6.4.4 | 2 | if a multi-factor authentication factor is lost, evidence of identity proofing is performed at the same level as duri… | N/A | N/A | — | no MFA factor to lose (6.3.3) |
| 6.5.1 | 2 | lookup secrets, out-of-band authentication requests or codes, and time-based one-time passwords (TOTPs) are only succ… | Yes | Pass | BE ST-013 | `test_it_01_01_link_signs_in_once_and_reuse_fails`, `test_two_concurrent_exchanges_of_one_link_give_one_session`, `test_a_link_used_by_someone_else_in_between_is_refused`, `test_a_used_link_is_refused` |
| 6.5.2 | 2 | Verify that, when being stored in the application's backend, lookup secrets with less than 112 bits of entropy (19 ra… | N/A | N/A | — | no lookup secrets (recovery codes); the out-of-band link token has 256 bits and only its SHA-256 is stored (`test_the_token_is_43_base64url_characters_and_only_its_hash_is_kept`) |
| 6.5.3 | 2 | lookup secrets, out-of-band authentication code, and time-based one-time password seeds, are generated using a Crypto… | Yes | Pass | BE ST-013 | `secrets.token_urlsafe` (CSPRNG): `grep -n "token_urlsafe(TOKEN_BYTES)" backend/src/racket/players/domain.py` → line 94; `test_the_token_is_43_base64url_characters_and_only_its_hash_is_kept` |
| 6.5.4 | 2 | lookup secrets and out-of-band authentication codes have a minimum of 20 bits of entropy (typically 4 random alphanum… | Yes | Pass | BE ST-013 | 256 bits (43 base64url characters): `test_the_token_is_43_base64url_characters_and_only_its_hash_is_kept` |
| 6.5.5 | 2 | out-of-band authentication requests, codes, or tokens, as well as time-based one-time passwords (TOTPs) have a define… | Yes | Fail | P19 (residual, SEC-S5-ASVS-05; fix: `MAGIC_LINK_TTL_SECONDS=600` and the FR-001 text, PO decides) | the lifetime is defined but is 15 min, over the 10 min maximum of 6.5.5: `grep -n "magic_link_ttl_seconds" backend/src/racket/platform/settings.py` → `900`; FR-001 "expires after 15 min (judgment)"; `test_a_link_at_or_past_its_lifetime_is_refused` |
| 6.6.1 | 2 | authentication mechanisms using the Public Switched Telephone Network (PSTN) to deliver One-time Passwords (OTPs) via… | N/A | N/A | — | no SMS/phone OTP |
| 6.6.2 | 2 | out-of-band authentication requests, codes, or tokens are bound to the original authentication request for which they… | Yes | Pass | BE ST-013 | a token is one `sign_in_links` row for one address and works once: `test_a_link_signs_in_only_the_address_it_was_sent_to`, `test_it_01_01_link_signs_in_once_and_reuse_fails` (ADR 0025: bound to its request and address, no device binding) |
| 6.6.3 | 2 | a code based out-of-band authentication mechanism is protected against brute force attacks by using rate limiting. Co… | Yes | Pass | BE ST-013 | exchange attempts limited per IP (30 per 10 min) and the token has 256 bits (over 64): `test_guessing_tokens_is_rate_limited`, `test_the_token_is_43_base64url_characters_and_only_its_hash_is_kept` |
| 6.8.1 | 2 | Verify that, if the application supports multiple identity providers (IdPs), the user's identity cannot be spoofed vi… | N/A | N/A | — | no external IdP: `grep -rniE "oauth|oidc|openid" backend/src web/src` → no match |
| 6.8.2 | 2 | the presence and integrity of digital signatures on authentication assertions (for example on JWTs or SAML assertions… | N/A | N/A | — | no authentication assertions (JWT or SAML): `grep -rniE "jwt|jose|jwk" backend/src web/src` → no match; `grep -rniE "saml" backend/src web/src` → no match |
| 6.8.3 | 2 | SAML assertions are uniquely processed and used only once within the validity period to prevent replay attacks. | N/A | N/A | — | no SAML |
| 6.8.4 | 2 | Verify that, if an application uses a separate Identity Provider (IdP) and expects specific authentication strength, … | N/A | N/A | — | no separate IdP (6.8.1) |

### V7 Session Management

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 7.1.1 | 2 | the user's session inactivity timeout and absolute maximum session lifetime are documented, are appropriate in combin… | Yes | Fail | P19 (residual, SEC-S5-ASVS-06) | 30 d absolute / 7 d idle are documented (api-sprint-01 §2.3, ADR 0025 "Session") as judgment, with no justification against NIST SP 800-63B re-authentication: `grep -rnwiE "nist|800-63|800-63b" docs/decisions/0025-magic-link-sign-in-design.md docs/architecture` → no match |
| 7.1.2 | 2 | the documentation defines how many concurrent (parallel) sessions are allowed for one account as well as the intended… | Yes | Pass | PE, BE ST-014 | at most 10 per account, the 11th sign-in deletes the oldest (api-sprint-01 §2.3, ADR 0025): `test_the_eleventh_sign_in_evicts_the_oldest_session`, `test_ten_sessions_are_all_kept` |
| 7.1.3 | 2 | all systems that create and manage user sessions as part of a federated identity management ecosystem (such as SSO sy… | N/A | N/A | — | no federated SSO in R1 |
| 7.2.1 | 1 | the application performs all session token verification using a trusted, backend service. | Yes | Pass | BE ST-006 | the API looks up the hashed token on every request (`current_account`): `test_anonymous_caller_is_refused_on_every_id_route`, `test_sign_in_rotates_and_sign_out_ends_the_session` |
| 7.2.2 | 1 | the application uses either self-contained or reference tokens that are dynamically generated for session management,… | Yes | Pass | BE ST-006 | a new reference token per sign-in, no static key: `test_sign_in_rotates_and_sign_out_ends_the_session`, `test_exchange_replaces_a_session_already_presented` |
| 7.2.3 | 1 | if reference tokens are used to represent user sessions, they are unique and generated using a cryptographically secu… | Yes | Pass | BE ST-006 | 256 bits from `secrets.token_urlsafe(32)`, unique as the primary key `token_sha256`: `grep -n "token_urlsafe(32)" backend/src/racket/players/service.py` → lines 127, 217; api-sprint-00 §2 "Token". No test pins it yet (SEC-S5-ASVS-10, T-AU-2) |
| 7.2.4 | 1 | the application generates a new session token on user authentication, including re-authentication, and terminates the… | Yes | Pass | BE ST-006/013 | `test_exchange_replaces_a_session_already_presented`, `test_sign_in_rotates_and_sign_out_ends_the_session` |
| 7.3.1 | 2 | there is an inactivity timeout such that re-authentication is enforced according to risk analysis and documented secu… | Yes | Pass | BE ST-014 | 7 d idle (ADR 0025): `test_a_session_idle_for_longer_than_seven_days_is_refused`, `test_a_session_idle_for_just_under_seven_days_still_works_and_is_touched`, `test_a_session_idle_for_seven_days_is_over` |
| 7.3.2 | 2 | there is an absolute maximum session lifetime such that re-authentication is enforced according to risk analysis and … | Yes | Pass | BE ST-014 | 30 d absolute (ADR 0025): `test_a_session_older_than_thirty_days_is_over_even_when_active`; the cookie's `Max-Age` is the same value (`grep -n "session_absolute_seconds)" backend/src/racket/players/api.py` → lines 172, 293) |
| 7.4.1 | 1 | when session termination is triggered (such as logout or expiration), the application disallows any further use of th… | Yes | Pass | BE ST-006/014 | sign-out deletes the server row: `test_sign_out_ends_the_session_and_clears_the_browser_cache`, `test_sign_in_rotates_and_sign_out_ends_the_session` |
| 7.4.2 | 1 | the application terminates all active sessions when a user account is disabled or deleted (such as an employee leavin… | Yes | Pass | BE ST-051 | account deletion deletes every session (there is no "disabled" state): `test_it_03_08_both_sessions_end_and_the_purge_leaves_nothing` |
| 7.4.3 | 2 | the application gives the option to terminate all other active sessions after a successful change or removal of any a… | N/A | N/A | — | no authentication factor can be changed or removed: the address is the only factor and no route edits it (`grep -rnE "router\.(put|patch|post|delete)\(\"/me" backend/src/racket` → the 4 identity routes `DELETE /me`, age confirmation, retention and training consent; none sets a new address; deletion only erases it) |
| 7.4.4 | 2 | all pages that require authentication have easy and visible access to logout functionality. | Yes | Pass | FE ST-014 | the root layout renders the account menu with "Sign out" on every signed-in page: `grep -n "AccountMenu" web/src/app/layout.tsx` → line 48; `web/e2e/sprint-01/sign-out.spec.ts` (3 tests passed in CI run 41975999573, E2E chromium job, at `734d4832`) |
| 7.4.5 | 2 | application administrators are able to terminate active sessions for an individual user or for all users. | Yes | Fail | P19 (residual, SEC-S5-ASVS-08) | no administrator control ends a user's or all sessions; the only admin CLI grants roles and consent: `grep -n "add_parser" backend/src/racket/dataset/admin.py` → `grant-labeller`, `revoke-labeller`, `consent` |
| 7.5.1 | 2 | the application requires full re-authentication before allowing modifications to sensitive account attributes which m… | N/A | N/A | — | no route modifies an attribute used for authentication or recovery; the address cannot be changed (same command as 7.4.3) |
| 7.5.2 | 2 | users are able to view and (having authenticated again with at least one factor) terminate any or all currently activ… | Yes | Fail | P19 (residual, SEC-S5-ASVS-09) | users cannot list or end their other sessions (only the current one, by sign-out): `grep -rnE "/me/sessions|/auth/sessions" backend/src/racket --include=*.py` → no match |
| 7.6.1 | 2 | session lifetime and termination between Relying Parties (RPs) and Identity Providers (IdPs) behave as documented, re… | N/A | N/A | — | no external IdP |
| 7.6.2 | 2 | creation of a session requires either the user's consent or an explicit action, preventing the creation of new applic… | N/A | N/A | — | no external IdP |

### V8 Authorization

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 8.1.1 | 1 | authorization documentation defines rules for restricting function-level and data-specific access based on consumer p… | Yes | Pass | PE, security | owner-only and deny by default, per route: `grep -n "^## 7. Status codes per route" docs/architecture/api-sprint-00.md` → line 267 (and the §7 tables of api-sprint-01 to -04); the labeller role in api-sprint-03 §5.5 |
| 8.1.2 | 2 | authorization documentation defines rules for field-level access restrictions (both read and write) based on consumer… | Yes | Pass | PE | read: the "never returned" list (`grep -n -i "never returned" docs/architecture/api-sprint-00.md` → line 164); write: server-owned fields are refused (api-sprint-01 §5.3) |
| 8.2.1 | 1 | the application ensures that function-level access is restricted to consumers with explicit permissions. | Yes | Pass | BE ST-006/055 | every route is in the BOLA inventory, anonymous → 401, label routes only for the labeller role: `test_anonymous_caller_is_refused_on_every_id_route`, `test_endpoint_inventory_has_no_route_missing_from_the_matrix`, `test_it_03_11_a_player_gets_404_on_every_label_route` |
| 8.2.2 | 1 | the application ensures that data-specific access is restricted to consumers with explicit permissions to specific da… | Yes | Pass | BE ST-006 | `test_other_user_gets_the_same_404_as_for_a_missing_resource` (`backend/tests/regression/test_bola_matrix.py`), `test_it_04_03_another_account_gets_the_404_of_an_unknown_id`, `test_it_03_11_a_labeller_gets_404_on_another_accounts_match` |
| 8.2.3 | 2 | the application ensures that field-level access is restricted to consumers with explicit permissions to specific fiel… | Yes | Pass | BE ST-006 | read allowlist and write refusal: `test_response_is_an_allowlist_without_owner_internals`, `test_unknown_or_server_owned_fields_are_refused_without_echo` |
| 8.3.1 | 1 | the application enforces authorization rules at a trusted service layer and doesn't rely on controls that an untruste… | Yes | Pass | BE | the rules run in API dependencies and the tests call the API directly, with no client: `test_other_user_gets_the_same_404_as_for_a_missing_resource`, `test_it_03_11_a_labeller_is_refused_a_match_without_consent` |
| 8.4.1 | 2 | multi-tenant applications use cross-tenant controls to ensure consumer operations will never affect tenants with whic… | Yes | Pass | BE | no tenants; the boundary is the account, and no operation reaches another account: `test_other_user_gets_the_same_404_as_for_a_missing_resource`, `test_it_03_11_a_labeller_gets_404_on_another_accounts_match` |

### V9 Self-contained Tokens

**N/A for R1:** sessions use opaque reference tokens (api-sprint-00 §2), not self-contained tokens: `grep -rniE "jwt|jose|jwk" backend/src web/src` → no match (2026-11-05, ST-078b). The presigned media URLs are signed and checked by the object store, not by the application, and are covered by V5 and V14 rows (judgment). Re-assess if JWTs are adopted.

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 9.1.1 | 1 | self-contained tokens are validated using their digital signature or MAC to protect against tampering before acceptin… | N/A | N/A | — | no self-contained tokens |
| 9.1.2 | 1 | only algorithms on an allowlist can be used to create and verify self-contained tokens, for a given context. The allo… | N/A | N/A | — | no self-contained tokens |
| 9.1.3 | 1 | key material that is used to validate self-contained tokens is from trusted pre-configured sources for the token issu… | N/A | N/A | — | no self-contained tokens |
| 9.2.1 | 1 | Verify that, if a validity time span is present in the token data, the token and its content are accepted only if the… | N/A | N/A | — | no self-contained tokens |
| 9.2.2 | 2 | the service receiving a token validates the token to be the correct type and is meant for the intended purpose before… | N/A | N/A | — | no self-contained tokens |
| 9.2.3 | 2 | the service only accepts tokens which are intended for use with that service (audience). For JWTs, this can be achiev… | N/A | N/A | — | no self-contained tokens |
| 9.2.4 | 2 | Verify that, if a token issuer uses the same private key for issuing tokens to different audiences, the issued tokens… | N/A | N/A | — | no self-contained tokens |

### V10 OAuth and OIDC

**N/A for R1:** no OAuth/OIDC client or server: `grep -rniE "oauth|oidc|openid" backend/src web/src` → no match (2026-11-05, ST-078b). The upstream V10 file changed after the 2026-10-03 fetch (sha256 `003021eb05f75240…` on 2026-11-05); its L1/L2 ids are still the 29 rows below. Re-assess if an external IdP is adopted for sign-in.

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 10.1.1 | 2 | tokens are only sent to components that strictly need them. For example, when using a backend-for-frontend pattern fo… | N/A | N/A | — | no OAuth/OIDC |
| 10.1.2 | 2 | the client only accepts values from the authorization server (such as the authorization code or ID Token) if these va… | N/A | N/A | — | no OAuth/OIDC |
| 10.2.1 | 2 | Verify that, if the code flow is used, the OAuth client has protection against browser-based request forgery attacks,… | N/A | N/A | — | no OAuth/OIDC |
| 10.2.2 | 2 | Verify that, if the OAuth client can interact with more than one authorization server, it has a defense against mix-u… | N/A | N/A | — | no OAuth/OIDC |
| 10.3.1 | 2 | the resource server only accepts access tokens that are intended for use with that service (audience). The audience m… | N/A | N/A | — | no OAuth/OIDC |
| 10.3.2 | 2 | the resource server enforces authorization decisions based on claims from the access token that define delegated auth… | N/A | N/A | — | no OAuth/OIDC |
| 10.3.3 | 2 | if an access control decision requires identifying a unique user from an access token (JWT or related token introspec… | N/A | N/A | — | no OAuth/OIDC |
| 10.3.4 | 2 | Verify that, if the resource server requires specific authentication strength, methods, or recentness, it verifies th… | N/A | N/A | — | no OAuth/OIDC |
| 10.4.1 | 1 | the authorization server validates redirect URIs based on a client-specific allowlist of pre-registered URIs using ex… | N/A | N/A | — | no OAuth/OIDC |
| 10.4.2 | 1 | Verify that, if the authorization server returns the authorization code in the authorization response, it can be used… | N/A | N/A | — | no OAuth/OIDC |
| 10.4.3 | 1 | the authorization code is short-lived. The maximum lifetime can be up to 10 minutes for L1 and L2 applications and up… | N/A | N/A | — | no OAuth/OIDC |
| 10.4.4 | 1 | for a given client, the authorization server only allows the usage of grants that this client needs to use. Note that… | N/A | N/A | — | no OAuth/OIDC |
| 10.4.5 | 1 | the authorization server mitigates refresh token replay attacks for public clients, preferably using sender-constrain… | N/A | N/A | — | no OAuth/OIDC |
| 10.4.6 | 2 | Verify that, if the code grant is used, the authorization server mitigates authorization code interception attacks by… | N/A | N/A | — | no OAuth/OIDC |
| 10.4.7 | 2 | if the authorization server supports unauthenticated dynamic client registration, it mitigates the risk of malicious … | N/A | N/A | — | no OAuth/OIDC |
| 10.4.8 | 2 | refresh tokens have an absolute expiration, including if sliding refresh token expiration is applied. | N/A | N/A | — | no OAuth/OIDC |
| 10.4.9 | 2 | refresh tokens and reference access tokens can be revoked by an authorized user using the authorization server user i… | N/A | N/A | — | no OAuth/OIDC |
| 10.4.10 | 2 | confidential client is authenticated for client-to-authorized server backchannel requests such as token requests, pus… | N/A | N/A | — | no OAuth/OIDC |
| 10.4.11 | 2 | the authorization server configuration only assigns the required scopes to the OAuth client. | N/A | N/A | — | no OAuth/OIDC |
| 10.5.1 | 2 | the client (as the relying party) mitigates ID Token replay attacks. For example, by ensuring that the 'nonce' claim … | N/A | N/A | — | no OAuth/OIDC |
| 10.5.2 | 2 | the client uniquely identifies the user from ID Token claims, usually the 'sub' claim, which cannot be reassigned to … | N/A | N/A | — | no OAuth/OIDC |
| 10.5.3 | 2 | the client rejects attempts by a malicious authorization server to impersonate another authorization server through a… | N/A | N/A | — | no OAuth/OIDC |
| 10.5.4 | 2 | the client validates that the ID Token is intended to be used for that client (audience) by checking that the 'aud' c… | N/A | N/A | — | no OAuth/OIDC |
| 10.5.5 | 2 | Verify that, when using OIDC back-channel logout, the relying party mitigates denial of service through forced logout… | N/A | N/A | — | no OAuth/OIDC |
| 10.6.1 | 2 | the OpenID Provider only allows values 'code', 'ciba', 'id_token', or 'id_token code' for response mode. Note that 'c… | N/A | N/A | — | no OAuth/OIDC |
| 10.6.2 | 2 | the OpenID Provider mitigates denial of service through forced logout. By obtaining explicit confirmation from the en… | N/A | N/A | — | no OAuth/OIDC |
| 10.7.1 | 2 | the authorization server ensures that the user consents to each authorization request. If the identity of the client … | N/A | N/A | — | no OAuth/OIDC |
| 10.7.2 | 2 | when the authorization server prompts for user consent, it presents sufficient and clear information about what is be… | N/A | N/A | — | no OAuth/OIDC |
| 10.7.3 | 2 | the user can review, modify, and revoke consents which the user has granted through the authorization server. | N/A | N/A | — | no OAuth/OIDC |

### V11 Cryptography

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 11.1.1 | 2 | there is a documented policy for management of cryptographic keys and a cryptographic key lifecycle that follows a ke… | TBD | Not assessed | security | — |
| 11.1.2 | 2 | a cryptographic inventory is performed, maintained, regularly updated, and includes all cryptographic keys, algorithm… | TBD | Not assessed | security | — |
| 11.2.1 | 2 | industry-validated implementations (including libraries and hardware-accelerated implementations) are used for crypto… | TBD | Not assessed | security | — |
| 11.2.2 | 2 | the application is designed with crypto agility such that random number, authenticated encryption, MAC, or hashing al… | TBD | Not assessed | security | — |
| 11.2.3 | 2 | all cryptographic primitives utilize a minimum of 128-bits of security based on the algorithm, key size, and configur… | TBD | Not assessed | security | — |
| 11.3.1 | 1 | insecure block modes (e.g., ECB) and weak padding schemes (e.g., PKCS#1 v1.5) are not used. | TBD | Not assessed | security | — |
| 11.3.2 | 1 | only approved ciphers and modes such as AES with GCM are used. | TBD | Not assessed | security | — |
| 11.3.3 | 2 | encrypted data is protected against unauthorized modification preferably by using an approved authenticated encryptio… | TBD | Not assessed | security | — |
| 11.4.1 | 1 | only approved hash functions are used for general cryptographic use cases, including digital signatures, HMAC, KDF, a… | TBD | Not assessed | security | — |
| 11.4.2 | 2 | passwords are stored using an approved, computationally intensive, key derivation function (also known as a "password… | N/A | N/A | — | no passwords (FR-001) |
| 11.4.3 | 2 | hash functions used in digital signatures, as part of data authentication or data integrity are collision resistant a… | TBD | Not assessed | security | — |
| 11.4.4 | 2 | the application uses approved key derivation functions with key stretching parameters when deriving secret keys from … | TBD | Not assessed | security | — |
| 11.5.1 | 2 | all random numbers and strings which are intended to be non-guessable must be generated using a cryptographically sec… | Yes | S0 planned | BE | `secrets` module for tokens, `uuid4` for IDs |
| 11.6.1 | 2 | only approved cryptographic algorithms and modes of operation are used for key generation and seeding, and digital si… | TBD | Not assessed | security | — |

### V12 Secure Communication

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 12.1.1 | 1 | only the latest recommended versions of the TLS protocol are enabled, such as TLS 1.2 and TLS 1.3. The latest version… | Yes | Later (first deploy) | SRE | TLS 1.2+/1.3 at edge |
| 12.1.2 | 2 | only recommended cipher suites are enabled, with the strongest cipher suites set as preferred. L3 applications must o… | TBD | Not assessed | security | — |
| 12.1.3 | 2 | the application validates that mTLS client certificates are trusted before using the certificate identity for authent… | N/A | N/A | — | no mTLS |
| 12.2.1 | 1 | TLS is used for all connectivity between a client and external facing, HTTP-based services, and does not fall back to… | Yes | S0 partial | SRE/FE | HTTPS web in dev (ST-010); edge in prod |
| 12.2.2 | 1 | external facing services use publicly trusted TLS certificates. | TBD | Not assessed | security | — |
| 12.3.1 | 2 | an encrypted protocol such as TLS is used for all inbound and outbound connections to and from the application, inclu… | Yes | Later | SRE | TLS to managed Postgres / object store in prod |
| 12.3.2 | 2 | TLS clients validate certificates received before communicating with a TLS server. | TBD | Not assessed | security | — |
| 12.3.3 | 2 | TLS or another appropriate transport encryption mechanism used for all connectivity between internal, HTTP-based serv… | Yes | Later | SRE | internal TLS decision at first deploy |
| 12.3.4 | 2 | TLS connections between internal services use trusted certificates. Where internally generated or self-signed certifi… | TBD | Not assessed | security | — |

### V13 Configuration

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 13.1.1 | 2 | all communication needs for the application are documented. This must include external services which the application… | Yes | S0 partial | SRE/PE | communication needs: threat model §3, compose networks |
| 13.2.1 | 2 | communications between backend application components that don't support the application's standard user session mech… | Yes | Later | SRE | service accounts per component |
| 13.2.2 | 2 | communications between backend application components, including local or operating system services, APIs, middleware… | Yes | Open (F-1) | SRE ST-001 follow-up | separate least-privilege DB roles and S3 keys for api/worker |
| 13.2.3 | 2 | if a credential has to be used for service authentication, the credential being used by the consumer is not a default… | Yes | S0 planned | SRE | no default credentials; compose requires vars |
| 13.2.4 | 2 | an allowlist is used to define the external resources or systems with which the application is permitted to communica… | Yes | S0 partial | SRE/ML ST-009 | worker `sandbox` internal network; IT-00-10 (CI) |
| 13.2.5 | 2 | the web or application server is configured with an allowlist of resources or systems to which the server can send re… | Yes | S0 partial | SRE | outbound allowlist for API (object store, DB, OTLP) |
| 13.3.1 | 2 | a secrets management solution, such as a key vault, is used to securely create, store, control access to, and destroy… | Yes | Later (first deploy) | SRE | secret store in prod; env in dev; gitleaks in CI |
| 13.3.2 | 2 | access to secret assets adheres to the principle of least privilege. | Yes | Open (F-1) | SRE | least privilege on secrets |
| 13.4.1 | 1 | the application is deployed either without any source control metadata, including the .git or .svn folders, or in a w… | Yes | S0 planned | SRE | `.dockerignore` excludes `.git` |
| 13.4.2 | 2 | debug modes are disabled for all components in production environments to prevent exposure of debugging features and … | Yes | S0 planned | BE ST-005 | debug off outside dev; dev provider refused in prod |
| 13.4.3 | 2 | web servers do not expose directory listings to clients unless explicitly intended. | Yes | S0 partial | SRE | no listings: private bucket, anonymous GET test to add (T-MU-4) |
| 13.4.4 | 2 | using the HTTP TRACE method is not supported in production environments, to avoid potential information leakage. | Yes | S0 planned | BE | TRACE not routed → 405 |
| 13.4.5 | 2 | documentation (such as for internal APIs) and monitoring endpoints are not exposed unless explicitly intended. | Yes | S0 partial | BE/SRE | `/docs`, `/openapi.json` off in staging/prod; `/readyz` internal (T-INF-2) |

### V14 Data Protection

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 14.1.1 | 2 | all sensitive data created and processed by the application has been identified and classified into protection levels… | Yes | S0 partial | security | threat model §1 classes; full map before beta (NFR-063) |
| 14.1.2 | 2 | all sensitive data protection levels have a documented set of protection requirements. This must include (but not be … | Yes | S1 | security + PO | per-class protection requirements (ADR 0006) |
| 14.2.1 | 1 | sensitive data is only sent to the server in the HTTP message body or header fields, and that the URL and query strin… | Yes | S0 planned | BE | no tokens in URLs; tus upload URL carries no credential |
| 14.2.2 | 2 | the application prevents sensitive data from being cached in server components, such as load balancers and applicatio… | Yes | S0 planned | BE | `Cache-Control: no-store` |
| 14.2.3 | 2 | defined sensitive data is not sent to untrusted parties (e.g., user trackers) to prevent unwanted collection of data … | Yes | S0 planned | FE | no third-party trackers |
| 14.2.4 | 2 | controls around sensitive data related to encryption, integrity verification, retention, how the data is to be logged… | Yes | S1 | security | encryption at rest and integrity per class |
| 14.2.7 | 3 (L3 adopted) | sensitive information is subject to data retention classification, ensuring that outdated or unnecessary data is dele… | Yes | S1 | BE/SRE | 24 h abandoned-upload expiry; retention jobs (ADR 0006) |
| 14.3.1 | 1 | authenticated data is cleared from client storage, such as the browser DOM, after the client or session is terminated… | Yes | S0 planned | FE ST-010 | clear stored upload URLs and caches on sign-out |
| 14.3.2 | 2 | the application sets sufficient anti-caching HTTP response header fields (i.e., Cache-Control: no-store) so that sens… | Yes | S0 planned | BE ST-005 | IT-00-14 `test_authenticated_json_is_no_store` |
| 14.3.3 | 2 | data stored in browser storage (such as localStorage, sessionStorage, IndexedDB, or cookies) does not contain sensiti… | Yes | S0 planned | FE | only upload URLs (no credential, no PII) in localStorage |

### V15 Secure Coding and Architecture

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 15.1.1 | 1 | application documentation defines risk based remediation time frames for 3rd party component versions with vulnerabil… | Yes | S0 partial | SRE/security | remediation timeframes in ci-cd.md; dependency audit gate |
| 15.1.2 | 2 | an inventory catalog, such as software bill of materials (SBOM), is maintained of all third-party libraries in use, i… | Yes | S0 planned | SRE ST-002 | CycloneDX SBOM in CI (ADR 0014) |
| 15.1.3 | 2 | the application documentation identifies functionality which is time-consuming or resource-demanding. This must inclu… | Yes | S0 documented | PE | resource-heavy: upload PATCH, probe (ADR 0011, threat model T-UP-5..7) |
| 15.2.1 | 1 | the application only contains components which have not breached the documented update and remediation time frames. | Yes | S0 planned | SRE | pip-audit / npm audit gate |
| 15.2.2 | 2 | the application has implemented defenses against loss of availability due to functionality which is time-consuming or… | Yes | S0 partial | BE/SRE | worker limits; upload caps; rate limits S1 |
| 15.2.3 | 2 | the production environment only includes functionality that is required for the application to function, and does not… | Yes | S0 planned | BE | fault injection inert outside APP_ENV=test (`test_fault_injection_is_ignored_outside_test_env`) |
| 15.3.1 | 1 | the application only returns the required subset of fields from a data object. For example, it should not return an e… | Yes | S0 planned | BE | allowlist response schemas |
| 15.3.2 | 2 | where the application backend makes calls to external URLs, it is configured to not follow redirects unless it is int… | Yes | S0 partial | ML | ffprobe: no redirects / protocol allowlist (F-2) |
| 15.3.3 | 2 | the application has countermeasures to protect against mass assignment attacks by limiting allowed fields per control… | Yes | S0 planned | BE | closed request schemas |
| 15.3.4 | 2 | all proxying and middleware components transfer the user's original IP address correctly using trusted data fields th… | Yes | Later (first deploy) | SRE | trusted forwarded-for from ingress only |
| 15.3.5 | 2 | the application explicitly ensures that variables are of the correct type and performs strict equality and comparator… | Yes | S0 planned | BE/FE | mypy strict on domain; TS strict |
| 15.3.6 | 2 | JavaScript code is written in a way that prevents prototype pollution, for example, by using Set() or Map() instead o… | Yes | S0 planned | FE | lint rules; no untrusted object merge |
| 15.3.7 | 2 | the application has defenses against HTTP parameter pollution attacks, particularly if the application framework make… | Yes | S0 planned | BE | single-valued query params (`limit`) |

### V16 Security Logging and Error Handling

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 16.1.1 | 2 | an inventory exists documenting the logging performed at each layer of the application's technology stack, what event… | Yes | S0 partial | SRE/BE | log inventory: api, worker → stdout → collector |
| 16.2.1 | 2 | each log entry includes necessary metadata (such as when, where, who, what) that would allow for a detailed investiga… | Yes | S0 planned | BE ST-005 | JSON logs with UTC time, request_id, trace_id, account_id |
| 16.2.2 | 2 | time sources for all logging components are synchronized, and that timestamps in security event metadata use UTC or i… | Yes | S0 planned | BE | UTC timestamps |
| 16.2.3 | 2 | the application only stores or broadcasts logs to the files and services that are documented in the log inventory. | TBD | Not assessed | security | — |
| 16.2.4 | 2 | logs can be read and correlated by the log processor that is in use, preferably by using a common logging format. | TBD | Not assessed | security | — |
| 16.2.5 | 2 | when logging sensitive data, the application enforces logging based on the data's protection level. For example, it m… | Yes | S0 planned | BE | no tokens, emails or signed URLs (IT-00-15) |
| 16.3.1 | 2 | all authentication operations are logged, including successful and unsuccessful attempts. Additional metadata, such a… | Yes | S0 planned | BE ST-006 | `auth.sign_in` success/failure |
| 16.3.2 | 2 | failed authorization attempts are logged. For L3, this must include logging all authorization decisions, including lo… | Yes | S0 planned | BE ST-006 | `authz.denied` on `racket.security` |
| 16.3.3 | 2 | the application logs the security events that are defined in the documentation and also logs attempts to bypass the s… | Yes | S1 | BE | log validation and rate-limit bypass attempts |
| 16.3.4 | 2 | the application logs unexpected errors and security control failures such as backend TLS failures. | Yes | S0 planned | BE | unexpected errors logged with support_ref |
| 16.4.1 | 2 | all logging components appropriately encode data to prevent log injection. | Yes | S0 planned | BE | JSON encoding; request-id allowlist |
| 16.4.2 | 2 | logs are protected from unauthorized access and cannot be modified. | Yes | Later (first deploy) | SRE | log store access control |
| 16.4.3 | 2 | logs are securely transmitted to a logically separate system for analysis, detection, alerting, and escalation. The a… | Yes | Later (first deploy) | SRE | ship logs off-host |
| 16.5.1 | 2 | a generic message is returned to the consumer when an unexpected or security-sensitive error occurs, ensuring no expo… | Yes | S0 planned | BE ST-005 | `test_error_bodies.py` |
| 16.5.2 | 2 | the application continues to operate securely when external resource access fails, for example, by using patterns suc… | Yes | S0 partial | BE | `/readyz` reports; dependency failures → 503 generic |
| 16.5.3 | 2 | the application fails gracefully and securely, including when an exception occurs, preventing fail-open conditions su… | Yes | S0 planned | BE ST-007 | fail closed (`test_fail_closed.py`) |

### V17 WebRTC

**N/A:** no WebRTC.

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 17.1.1 | 2 | the Traversal Using Relays around NAT (TURN) service only allows access to IP addresses that are not reserved for spe… | N/A | N/A | — | no WebRTC |
| 17.2.1 | 2 | the key for the Datagram Transport Layer Security (DTLS) certificate is managed and protected based on the documented… | N/A | N/A | — | no WebRTC |
| 17.2.2 | 2 | the media server is configured to use and support approved Datagram Transport Layer Security (DTLS) cipher suites and… | N/A | N/A | — | no WebRTC |
| 17.2.3 | 2 | Secure Real-time Transport Protocol (SRTP) authentication is checked at the media server to prevent Real-time Transpo… | N/A | N/A | — | no WebRTC |
| 17.2.4 | 2 | the media server is able to continue processing incoming media traffic when encountering malformed Secure Real-time T… | N/A | N/A | — | no WebRTC |
| 17.3.1 | 2 | the signaling server is able to continue processing legitimate incoming signaling messages during a flood attack. Thi… | N/A | N/A | — | no WebRTC |
| 17.3.2 | 2 | the signaling server is able to continue processing legitimate signaling messages when encountering malformed signali… | N/A | N/A | — | no WebRTC |
