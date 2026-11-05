# Sprint 5 ST-078e (story ST-078 R1 passes an ASVS L2 review; NFR-067.2-.3, NFR-050.7-.8;
# AQS/SEC-05, AQS/STACK-04). Bound in web/tests/features/client-hygiene.test.ts, which checks
# that every scenario below names its test: the SW handler tests (tests/unit/sw-cache.test.ts),
# the sign-out clear tests (tests/unit/sign-out-hygiene.test.ts), the per-form hydration-lock
# tests (tests/unit/hydration-lock.test.tsx), the browser test
# (e2e/sprint-05/logout-hygiene.spec.ts) and the web-origin IT
# (backend/tests/integration/test_it_05_security_headers.py, IT-05-08).
@M5 @story-ST-078 @web
Feature: The client leaves nothing behind and resists framing and early submits
  A shared phone keeps no account data after sign-out, the service worker never stores match
  video or audio, every web response carries the browser's own defences, and no form can be sent
  before the page is ready to handle it.

  Rule: Sign-out empties the device's stores (NFR-067.2)

    Scenario: Sign-out empties local storage, session storage, IndexedDB and the account caches
      Given the player's device holds local storage, session storage, an IndexedDB database and a kept plan
      When the player signs out
      Then local storage and session storage are empty
      And no IndexedDB database is left
      And no cache holds anything but the content-hashed app files and the offline page

    Scenario: Sign-out removes media even from the app-file cache
      Given an older service worker stored a video under the app-file path
      When the player signs out
      Then no cache holds a media file

  Rule: The service worker never stores media (NFR-067.3)

    Scenario: A media file under the app-file path is never stored
      Given the player's browser asks for an audio file under "/_next/static/media/"
      When the service worker sees the request
      Then it leaves the request to the network and stores nothing

    Scenario: A media answer is never stored, whatever its path
      Given an app file is answered with a "video/mp4" body
      When the service worker fetches it
      Then the answer reaches the page and nothing is stored

    Scenario: A partial answer is never stored
      Given an app file is answered with "206 Partial Content"
      When the service worker fetches it
      Then the answer reaches the page and nothing is stored

  Rule: Every web response carries CSP, nosniff and frame denial (NFR-050.7)

    Scenario: Pages, app files, the service worker and the manifest carry the security headers
      Given the web origin is running
      When the browser fetches a page, a missing page, an app file, the service worker, the manifest and an icon
      Then every answer has a Content-Security-Policy with "frame-ancestors 'none'"
      And every answer has "X-Content-Type-Options: nosniff" and "X-Frame-Options: DENY"

  Rule: No form can be sent before hydration (NFR-050.8)

    Scenario: Every form with a submit handler is locked in the server HTML
      Given a form whose submit is handled by the page script
      When the server HTML is shown before the script has run
      Then the form has no enabled submit button
      And once the script runs the form can be sent
