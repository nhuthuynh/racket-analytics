# Sprint 0 §7. Owner: senior-qa-engineer. Written before implementation (ST-012).
# Steps: backend/tests/features/test_errors_and_tracing.py
# Regression suites: backend/tests/regression/test_error_bodies.py (IT-00-13),
#                    backend/tests/regression/test_trace_header.py (IT-00-12).
@M0 @story-ST-005 @nfr-058 @nfr-076
Feature: Safe errors and end-to-end tracing

  Rule: Error responses never reveal internals

    Scenario: An unexpected server error
      Given the match service fails unexpectedly
      When Ivy opens one of her matches
      Then she gets a generic error with a support reference
      And the response contains no stack trace, query or internal identifier

  Rule: A request can be followed from the API to the worker

    Scenario: One trace covers upload to probe
      Given tracing is enabled
      When Ivy completes an upload and the probe job runs
      Then the API request, the enqueue and the probe stage share one trace ID

    Scenario: A malformed trace header is ignored safely
      Given a request carries a malformed "traceparent" header
      When the request reaches the API
      Then the request succeeds
      And it is recorded under a new trace
