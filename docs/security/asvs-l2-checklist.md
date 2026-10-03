# OWASP ASVS 5.0 Level 2 checklist (skeleton)

- **Status:** Skeleton v0 (NFR-050). Owner: security-privacy-engineer. Written into `docs/` by the principal-engineer's session, because the security role is read-only. Generated from the ASVS 5.0 chapter files listed under "Sources" with `scratchpad/asvs/gen.py` (the generator is not part of the repo), then annotated by hand.
- **Date:** 2026-10-03
- **Scope:** API, worker and PWA client, ASVS 5.0 **L1 + L2** [AQS/SEC-01], plus the L3 items we adopt: 5.2.4 and 5.2.6 (AQS Implications [AQS/SEC-02]) and 14.2.7 (NFR-066 [AQS/SEC-05]). Rows: 256.
- **Release gate:** at each release review, every applicable L2 row is either passing with evidence, or covered by an accepted-risk ADR with a human decider (NFR-050).

## How to read this

- **Requirement text** is abridged from the fetched chapter, with "Verify that" removed. Read the full text in the source before you claim a pass.
- **Applies:**
  - `Yes`;
  - `N/A` (with the reason in Verification);
  - `S1` (applies once Sprint 1 introduces the feature);
  - `TBD` (not yet assessed).
- **Status:**
  - `S0 planned`: the control is specified (API contract, ADR 0011, threat model) and a Sprint 0 story builds it. Where a test is named, it already exists as a red-first test (ADR 0012).
  - `S0 partial`: part of the control lands in Sprint 0.
  - `S0 documented`: a documentation requirement is satisfied by a named doc.
  - `S1` or `Later`: a future sprint or the first deployment.
  - `Open (F-n)`: a finding in `threat-model-v0.md` §5.
  - `N/A`.
  - `Not assessed`.
- **No row says "Pass" yet.** Sprint 0 code is still being written. A row moves to `Pass` only with a command and its result, or a CI link (working agreement: evidence for every success claim).

### Status summary

| Status | Rows |
|---|---|
| N/A | 77 |
| S0 planned | 65 |
| Not assessed | 48 |
| S1 | 28 |
| S0 partial | 14 |
| Later (first deploy) | 9 |
| S0 documented | 4 |
| Later | 3 |
| Open (F-3) | 2 |
| Later (playback) | 2 |
| Open (F-1) | 2 |
| Open (F-2) | 1 |
| Open | 1 |

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
| 1.1.1 | 2 | input is decoded or unescaped into a canonical form only once, it is only decoded when encoded data in that form is e… | TBD | Not assessed | security | — |
| 1.1.2 | 2 | the application performs output encoding and escaping either as a final step before being used by the interpreter for… | TBD | Not assessed | security | — |
| 1.2.1 | 1 | output encoding for an HTTP response, HTML document, or XML document is relevant for the context required, such as en… | TBD | Not assessed | security | — |
| 1.2.2 | 1 | when dynamically building URLs, untrusted data is encoded according to its context (e.g., URL encoding or base64url e… | TBD | Not assessed | security | — |
| 1.2.3 | 1 | output encoding or escaping is used when dynamically building JavaScript content (including JSON), to avoid changing … | TBD | Not assessed | security | — |
| 1.2.4 | 1 | data selection or database queries (e.g., SQL, HQL, NoSQL, Cypher) use parameterized queries, ORMs, entity frameworks… | Yes | S0 planned | BE ST-005/006 | SQLAlchemy bound parameters only; code review |
| 1.2.5 | 1 | the application protects against OS command injection and that operating system calls use parameterized OS queries or… | Yes | S0 planned | ML ST-009 | ffprobe argv without shell; unit test on argv (T-WS-3) |
| 1.2.6 | 2 | the application protects against LDAP injection vulnerabilities, or that specific security controls to prevent LDAP i… | N/A | N/A | — | no LDAP |
| 1.2.7 | 2 | the application is protected against XPath injection attacks by using query parameterization or precompiled queries. | N/A | N/A | — | no XPath |
| 1.2.8 | 2 | LaTeX processors are configured securely (such as not using the "--shell-escape" flag) and an allowlist of commands i… | N/A | N/A | — | no LaTeX |
| 1.2.9 | 2 | the application escapes special characters in regular expressions (typically using a backslash) to prevent them from … | TBD | Not assessed | security | — |
| 1.3.1 | 1 | all untrusted HTML input from WYSIWYG editors or similar is sanitized using a well-known and secure HTML sanitization… | TBD | Not assessed | security | — |
| 1.3.2 | 1 | the application avoids the use of eval() or other dynamic code execution features such as Spring Expression Language … | TBD | Not assessed | security | — |
| 1.3.3 | 2 | data being passed to a potentially dangerous context is sanitized beforehand to enforce safety measures, such as only… | TBD | Not assessed | security | — |
| 1.3.4 | 2 | user-supplied Scalable Vector Graphics (SVG) scriptable content is validated or sanitized to contain only tags and at… | N/A | N/A | — | no SVG upload |
| 1.3.5 | 2 | the application sanitizes or disables user-supplied scriptable or expression template language content, such as Markd… | TBD | Not assessed | security | — |
| 1.3.6 | 2 | the application protects against Server-side Request Forgery (SSRF) attacks, by validating untrusted data against an … | Yes | Open (F-2) | ML ST-009 | ffprobe protocol/format allowlist; SSRF/LFI fixture test (T-WS-2) |
| 1.3.7 | 2 | the application protects against template injection attacks by not allowing templates to be built based on untrusted … | TBD | Not assessed | security | — |
| 1.3.8 | 2 | the application appropriately sanitizes untrusted input before use in Java Naming and Directory Interface (JNDI) quer… | N/A | N/A | — | no JNDI |
| 1.3.9 | 2 | the application sanitizes content before it is sent to memcache to prevent injection attacks. | N/A | N/A | — | no memcache |
| 1.3.10 | 2 | format strings which might resolve in an unexpected or malicious way when used are sanitized before being processed. | TBD | Not assessed | security | — |
| 1.3.11 | 2 | the application sanitizes user input before passing to mail systems to protect against SMTP or IMAP injection. | S1 | S1 | BE (magic links) | mail headers built by library; no user input in headers |
| 1.4.1 | 2 | the application uses memory-safe string, safer memory copy and pointer arithmetic to detect or prevent stack, buffer,… | TBD | Not assessed | security | — |
| 1.4.2 | 2 | sign, range, and input validation techniques are used to prevent integer overflows. | TBD | Not assessed | security | — |
| 1.4.3 | 2 | dynamically allocated memory and resources are released, and that references or pointers to freed memory are removed … | TBD | Not assessed | security | — |
| 1.5.1 | 1 | the application configures XML parsers to use a restrictive configuration and that unsafe features such as resolving … | N/A | N/A | — | no XML parsing (ffprobe JSON output) |
| 1.5.2 | 2 | deserialization of untrusted data enforces safe input handling, such as using an allowlist of object types or restric… | TBD | Not assessed | security | — |

### V2 Validation and Business Logic

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 2.1.1 | 1 | the application's documentation defines input validation rules for how to check the validity of data items against an… | Yes | S0 documented | PE | api-sprint-00 §5-§6 field rules |
| 2.1.2 | 2 | the application's documentation defines how to validate the logical and contextual consistency of combined data items… | TBD | Not assessed | security | — |
| 2.1.3 | 2 | expectations for business logic limits and validations are documented, including both per-user and globally across th… | Yes | S1 | BA + security | document per-user/global limits (F-3) |
| 2.2.1 | 1 | input is validated to enforce business or functional expectations for that input. This should either use positive val… | Yes | S0 planned | BE ST-006/008 | closed Pydantic schemas; `test_unknown_request_field_is_rejected`, `test_validation_error_is_generic…` |
| 2.2.2 | 1 | the application is designed to enforce input validation at a trusted service layer. While client-side validation impr… | Yes | S0 planned | BE | server-side validation; FE validation is UX only |
| 2.2.3 | 2 | the application ensures that combinations of related data items are reasonable according to the pre-defined rules. | TBD | Not assessed | security | — |
| 2.3.1 | 1 | the application will only process business logic flows for the same user in the expected sequential step order and wi… | Yes | S0 planned | BE ST-008 | IT-00-08 probe only after final byte (NFR-060) |
| 2.3.2 | 2 | business logic limits are implemented per the application's documentation to avoid business logic flaws being exploit… | Yes | S1 | BE | quotas (F-3) |
| 2.3.3 | 2 | transactions are being used at the business logic level such that either a business logic operation succeeds in its e… | Yes | S0 planned | BE ST-007/008 | completion transaction (ADR 0011); `test_fail_closed.py` |
| 2.3.4 | 2 | business logic level locking mechanisms are used to ensure that limited quantity resources (such as theater seats or … | Yes | S0 planned | BE ST-008 | upload row lock `FOR UPDATE NOWAIT`; concurrent PATCH test to add (T-UP-3) |
| 2.4.1 | 2 | anti-automation controls are in place to protect against excessive calls to application functions that could lead to … | Yes | Open (F-3) | BE + SRE S1 | rate limits on sign-in, match create, upload create/PATCH |

### V3 Web Frontend Security

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 3.2.1 | 1 | security controls are in place to prevent browsers from rendering content or functionality in HTTP responses in an in… | TBD | Not assessed | security | — |
| 3.2.2 | 1 | content intended to be displayed as text, rather than rendered as HTML, is handled using safe rendering functions (su… | Yes | S0 planned | FE ST-010 | render titles as text (React escaping) |
| 3.3.1 | 1 | cookies have the 'Secure' attribute set, and if the '\__Host-' prefix is not used for the cookie name, the '__Secure-… | Yes | S0 planned | BE ST-006 | `Secure` outside APP_ENV=test (api §2) |
| 3.3.2 | 2 | each cookie's 'SameSite' attribute value is set according to the purpose of the cookie, to limit exposure to user int… | Yes | S0 planned | BE ST-006 | SameSite=Lax |
| 3.3.3 | 2 | cookies have the '__Host-' prefix for the cookie name unless they are explicitly designed to be shared with other hos… | Yes | S0 planned | BE ST-006 | `__Host-` prefix outside APP_ENV=test |
| 3.3.4 | 2 | if the value of a cookie is not meant to be accessible to client-side scripts (such as a session token), the cookie m… | Yes | S0 planned | BE ST-006 | HttpOnly session cookie |
| 3.4.1 | 1 | a Strict-Transport-Security header field is included on all responses to enforce an HTTP Strict Transport Security (H… | Yes | Later (first deploy) | SRE | HSTS at TLS terminator |
| 3.4.2 | 1 | the Cross-Origin Resource Sharing (CORS) Access-Control-Allow-Origin header field is a fixed value by the application… | Yes | S0 planned | PE/BE | no CORS: same-origin `/api` rewrite (api §1); fixed allowlist if ever enabled |
| 3.4.3 | 2 | HTTP responses include a Content-Security-Policy response header field which defines directives to ensure the browser… | Yes | S0 planned | FE ST-010 | CSP `default-src 'self'` (`security-headers.spec.ts`) |
| 3.4.4 | 2 | all HTTP responses contain an 'X-Content-Type-Options: nosniff' header field. This instructs browsers not to use cont… | Yes | S0 planned | BE ST-005, FE ST-010 | IT-00-14; `security-headers.spec.ts` |
| 3.4.5 | 2 | the application sets a referrer policy to prevent leakage of technically sensitive data to third-party services via t… | Yes | S0 planned | BE ST-005, FE ST-010 | `Referrer-Policy: no-referrer` (api §1.1); test to add |
| 3.4.6 | 2 | the web application uses the frame-ancestors directive of the Content-Security-Policy header field for every HTTP res… | Yes | S0 planned | FE ST-010 | CSP `frame-ancestors 'none'` (`security-headers.spec.ts`) |
| 3.5.1 | 1 | Verify that, if the application does not rely on the CORS preflight mechanism to prevent disallowed cross-origin requ… | Yes | S0 planned | BE ST-006 | Origin allowlist + SameSite + non-simple requests (T-AU-4) |
| 3.5.2 | 1 | Verify that, if the application relies on the CORS preflight mechanism to prevent disallowed cross-origin use of sens… | Yes | S0 planned | BE | state change never via GET/HEAD; no simple-request side effects |
| 3.5.3 | 1 | HTTP requests to sensitive functionality use appropriate HTTP methods such as POST, PUT, PATCH, or DELETE, and not me… | Yes | S0 planned | BE | POST/PATCH for changes (api §5-§6) |
| 3.5.4 | 2 | separate applications are hosted on different hostnames to leverage the restrictions provided by same-origin policy, … | Yes | S0 planned | SRE | web and API separated by path on one origin; review at first deploy |
| 3.5.5 | 2 | messages received by the postMessage interface are discarded if the origin of the message is not trusted, or if the s… | N/A | N/A | — | no postMessage use (re-check if added) |
| 3.7.1 | 2 | the application only uses client-side technologies which are still supported and considered secure. Examples of techn… | Yes | S0 planned | FE | supported browsers only (NFR-024) |
| 3.7.2 | 2 | the application will only automatically redirect the user to a different hostname or domain (which is not controlled … | Yes | S1 | FE/BE | no open redirects (magic-link return URL allowlist, S1) |

### V4 API and Web Service

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 4.1.1 | 1 | every HTTP response with a message body contains a Content-Type header field that matches the actual content of the r… | Yes | S0 planned | BE ST-005 | JSON content type on bodies; tus PATCH content type 415 |
| 4.1.2 | 2 | only user-facing endpoints (intended for manual web-browser access) automatically redirect from HTTP to HTTPS, while … | Yes | Later (first deploy) | SRE | API does not redirect HTTP→HTTPS; refuses plain HTTP at edge |
| 4.1.3 | 2 | any HTTP header field used by the application and set by an intermediary layer, such as a load balancer, a web proxy,… | Yes | Later (first deploy) | SRE | trusted proxy headers only from ingress |
| 4.2.1 | 2 | all application components (including load balancers, firewalls, and application servers) determine boundaries of inc… | Yes | Later (first deploy) | SRE | consistent message framing ingress ↔ uvicorn |
| 4.3.1 | 2 | a query allowlist, depth limiting, amount limiting, or query cost analysis is used to prevent GraphQL or data layer e… | N/A | N/A | — | no GraphQL |
| 4.3.2 | 2 | GraphQL introspection queries are disabled in the production environment unless the GraphQL API is meant to be used b… | N/A | N/A | — | no GraphQL |
| 4.4.1 | 1 | WebSocket over TLS (WSS) is used for all WebSocket connections. | N/A | N/A | — | no WebSockets |
| 4.4.2 | 2 | Verify that, during the initial HTTP WebSocket handshake, the Origin header field is checked against a list of origin… | N/A | N/A | — | no WebSockets |
| 4.4.3 | 2 | Verify that, if the application's standard session management cannot be used, dedicated tokens are being used for thi… | N/A | N/A | — | no WebSockets |
| 4.4.4 | 2 | dedicated WebSocket session management tokens are initially obtained or validated through the previously authenticate… | N/A | N/A | — | no WebSockets |

### V5 File Handling

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 5.1.1 | 2 | the documentation defines the permitted file types, expected file extensions, and maximum size (including unpacked si… | Yes | S1 | PE/BA | document: MP4/MOV, H.264/HEVC, ≤10 GB, ≤150 min (FR-023, K12) |
| 5.2.1 | 1 | the application will only accept files of a size which it can process without causing a loss of performance or a deni… | Yes | S0 partial | BE ST-008 | `Upload-Length` ≤ UPLOAD_MAX_BYTES, chunk ≤ 64 MiB (413) |
| 5.2.2 | 1 | when the application accepts a file, either on its own or within an archive such as a zip file, it checks if the file… | Yes | S1 | BE/ML FR-023 | magic bytes / container via ffprobe on stored object |
| 5.2.3 | 2 | the application checks compressed files (e.g., zip, gz, docx, odt) against maximum allowed uncompressed size and agai… | N/A | N/A | — | no compressed archives accepted |
| 5.2.4 | 3 (L3 adopted) | a file size quota and maximum number of files per user are enforced to ensure that a single user cannot fill up the s… | Yes | Open (F-3) | BE S1 | per-user byte and session quota |
| 5.2.6 | 3 (L3 adopted) | the application rejects uploaded images with a pixel size larger than the maximum allowed, to prevent pixel flood att… | Yes | S1 | ML | reject frame size above cap via probe facts |
| 5.3.1 | 1 | files uploaded or generated by untrusted input and stored in a public folder, are not executed as server-side program… | Yes | S0 planned | BE/SRE | objects in private bucket; never served as code |
| 5.3.2 | 1 | when the application creates file paths for file operations, instead of user-submitted filenames, it uses internally … | Yes | S0 planned | BE ST-008 | `ObjectKeyPolicy`; scenario 'Stored names never come from the user's file name' |
| 5.4.1 | 2 | the application validates or ignores user-submitted filenames, including in a JSON, JSONP, or URL parameter and speci… | Yes | Later (playback) | BE | Content-Disposition with generated name |
| 5.4.2 | 2 | file names served (e.g., in HTTP response header fields or email attachments) are encoded or sanitized (e.g., followi… | Yes | Later (playback) | BE | RFC 6266 encoding of served names |
| 5.4.3 | 2 | files obtained from untrusted sources are scanned by antivirus scanners to prevent serving of known malicious content. | Yes | Open | security + PO | AV scanning of video: decide risk acceptance or tool before beta |

### V6 Authentication

Passwords are never used (FR-001), so 6.2.x is N/A. Sign-in arrives in Sprint 1.

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 6.1.1 | 1 | application documentation defines how controls such as rate limiting, anti-automation, and adaptive response, are use… | Yes | S1 | security | document rate limiting for sign-in |
| 6.1.2 | 2 | a list of context-specific words is documented in order to prevent their use in passwords. The list could include per… | TBD | Not assessed | security | — |
| 6.1.3 | 2 | Verify that, if the application includes multiple authentication pathways, these are all documented together with the… | Yes | S1 | security | document pathways: magic link, passkey, dev (dev/test only) |
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
| 6.3.1 | 1 | controls to prevent attacks such as credential stuffing and password brute force are implemented according to the app… | Yes | S1 | BE | rate limits on magic-link requests |
| 6.3.2 | 1 | default user accounts (e.g., "root", "admin", or "sa") are not present in the application or are disabled. | Yes | S0 planned | BE ST-006 | dev users seeded only in dev/test; prod refuses dev provider |
| 6.3.3 | 2 | either a multi-factor authentication mechanism or a combination of single-factor authentication mechanisms, must be u… | Yes | S1 | security + PO | passkey or magic link as single factor: assess vs L2 MFA requirement |
| 6.3.4 | 2 | Verify that, if the application includes multiple authentication pathways, there are no undocumented pathways and tha… | Yes | S1 | security | no undocumented pathways; dev provider absent in prod |
| 6.4.1 | 1 | system generated initial passwords or activation codes are securely randomly generated, follow the existing password … | Yes | S1 | BE | magic-link codes CSPRNG + expiry 15 min |
| 6.4.2 | 1 | password hints or knowledge-based authentication (so-called "secret questions") are not present. | Yes | S1 | BE | no hints / secret questions |
| 6.4.3 | 2 | a secure process for resetting a forgotten password is implemented, that does not bypass any enabled multi-factor aut… | TBD | Not assessed | security | — |
| 6.4.4 | 2 | if a multi-factor authentication factor is lost, evidence of identity proofing is performed at the same level as duri… | TBD | Not assessed | security | — |
| 6.5.1 | 2 | lookup secrets, out-of-band authentication requests or codes, and time-based one-time passwords (TOTPs) are only succ… | Yes | S1 | BE | magic link single use (FR-001) |
| 6.5.2 | 2 | Verify that, when being stored in the application's backend, lookup secrets with less than 112 bits of entropy (19 ra… | TBD | Not assessed | security | — |
| 6.5.3 | 2 | lookup secrets, out-of-band authentication code, and time-based one-time password seeds, are generated using a Crypto… | Yes | S1 | BE | CSPRNG for magic links |
| 6.5.4 | 2 | lookup secrets and out-of-band authentication codes have a minimum of 20 bits of entropy (typically 4 random alphanum… | Yes | S1 | BE | entropy of magic-link token |
| 6.5.5 | 2 | out-of-band authentication requests, codes, or tokens, as well as time-based one-time passwords (TOTPs) have a define… | Yes | S1 | BE | 15 min lifetime (FR-001) |
| 6.6.1 | 2 | authentication mechanisms using the Public Switched Telephone Network (PSTN) to deliver One-time Passwords (OTPs) via… | N/A | N/A | — | no SMS/phone OTP |
| 6.6.2 | 2 | out-of-band authentication requests, codes, or tokens are bound to the original authentication request for which they… | Yes | S1 | BE | link bound to the originating request |
| 6.6.3 | 2 | a code based out-of-band authentication mechanism is protected against brute force attacks by using rate limiting. Co… | Yes | S1 | BE | rate limit on code-based OOB |
| 6.8.1 | 2 | Verify that, if the application supports multiple identity providers (IdPs), the user's identity cannot be spoofed vi… | TBD | Not assessed | security | — |
| 6.8.2 | 2 | the presence and integrity of digital signatures on authentication assertions (for example on JWTs or SAML assertions… | TBD | Not assessed | security | — |
| 6.8.3 | 2 | SAML assertions are uniquely processed and used only once within the validity period to prevent replay attacks. | N/A | N/A | — | no SAML |
| 6.8.4 | 2 | Verify that, if an application uses a separate Identity Provider (IdP) and expects specific authentication strength, … | TBD | Not assessed | security | — |

### V7 Session Management

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 7.1.1 | 2 | the user's session inactivity timeout and absolute maximum session lifetime are documented, are appropriate in combin… | Yes | S1 | security | dev: 12 h absolute; real sign-in lifetimes to document |
| 7.1.2 | 2 | the documentation defines how many concurrent (parallel) sessions are allowed for one account as well as the intended… | Yes | S1 | security | concurrent sessions policy |
| 7.1.3 | 2 | all systems that create and manage user sessions as part of a federated identity management ecosystem (such as SSO sy… | N/A | N/A | — | no federated SSO in R1 |
| 7.2.1 | 1 | the application performs all session token verification using a trusted, backend service. | Yes | S0 planned | BE ST-006 | server-side session lookup |
| 7.2.2 | 1 | the application uses either self-contained or reference tokens that are dynamically generated for session management,… | Yes | S0 planned | BE ST-006 | dynamic reference tokens |
| 7.2.3 | 1 | if reference tokens are used to represent user sessions, they are unique and generated using a cryptographically secu… | Yes | S0 planned | BE ST-006 | 256-bit CSPRNG, stored hashed; unit test to add (T-AU-2) |
| 7.2.4 | 1 | the application generates a new session token on user authentication, including re-authentication, and terminates the… | Yes | S0 planned | BE ST-006 | new token per sign-in, old session deleted |
| 7.3.1 | 2 | there is an inactivity timeout such that re-authentication is enforced according to risk analysis and documented secu… | Yes | S1 | BE | inactivity timeout for real sign-in |
| 7.3.2 | 2 | there is an absolute maximum session lifetime such that re-authentication is enforced according to risk analysis and … | Yes | S0 partial | BE | absolute lifetime (dev 12 h); real values S1 |
| 7.4.1 | 1 | when session termination is triggered (such as logout or expiration), the application disallows any further use of th… | Yes | S0 planned | BE ST-006 | `POST /auth/sign-out` deletes the session |
| 7.4.2 | 1 | the application terminates all active sessions when a user account is disabled or deleted (such as an employee leavin… | Yes | S1 | BE | sessions purged on account deletion (FR-007) |
| 7.4.3 | 2 | the application gives the option to terminate all other active sessions after a successful change or removal of any a… | TBD | Not assessed | security | — |
| 7.4.4 | 2 | all pages that require authentication have easy and visible access to logout functionality. | Yes | S0 planned | FE ST-010 | sign-out visible on authenticated pages |
| 7.4.5 | 2 | application administrators are able to terminate active sessions for an individual user or for all users. | TBD | Not assessed | security | — |
| 7.5.1 | 2 | the application requires full re-authentication before allowing modifications to sensitive account attributes which m… | TBD | Not assessed | security | — |
| 7.5.2 | 2 | users are able to view and (having authenticated again with at least one factor) terminate any or all currently activ… | TBD | Not assessed | security | — |
| 7.6.1 | 2 | session lifetime and termination between Relying Parties (RPs) and Identity Providers (IdPs) behave as documented, re… | N/A | N/A | — | no external IdP |
| 7.6.2 | 2 | creation of a session requires either the user's consent or an explicit action, preventing the creation of new applic… | N/A | N/A | — | no external IdP |

### V8 Authorization

| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |
|---|---|---|---|---|---|---|
| 8.1.1 | 1 | authorization documentation defines rules for restricting function-level and data-specific access based on consumer p… | Yes | S0 documented | PE/security | api-sprint-00 §2, §5, §7 (owner-only, deny by default) |
| 8.1.2 | 2 | authorization documentation defines rules for field-level access restrictions (both read and write) based on consumer… | Yes | S0 documented | PE | api-sprint-00 §5.1 'never returned' list |
| 8.2.1 | 1 | the application ensures that function-level access is restricted to consumers with explicit permissions. | Yes | S0 planned | BE ST-006 | every route has an auth dependency; anonymous → 401 (`test_anonymous_caller_is_refused…`) |
| 8.2.2 | 1 | the application ensures that data-specific access is restricted to consumers with explicit permissions to specific da… | Yes | S0 planned | BE ST-006 | BOLA matrix + inventory (`test_bola_matrix.py`, IT-00-02) |
| 8.2.3 | 2 | the application ensures that field-level access is restricted to consumers with explicit permissions to specific fiel… | Yes | S0 planned | BE ST-006 | allowlist response schemas; IT-00-01 allowlist test |
| 8.3.1 | 1 | the application enforces authorization rules at a trusted service layer and doesn't rely on controls that an untruste… | Yes | S0 planned | BE | authorisation only in API dependencies, never client |
| 8.4.1 | 2 | multi-tenant applications use cross-tenant controls to ensure consumer operations will never affect tenants with whic… | Yes | S0 planned | BE | per-account isolation = owner scoping (no tenants) |

### V9 Self-contained Tokens

**N/A for R1:** sessions use opaque reference tokens (api-sprint-00 §2), not self-contained tokens. Re-assess if JWTs are adopted.

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

**N/A for R1:** no OAuth/OIDC client or server. Re-assess if an external IdP is adopted for sign-in.

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
