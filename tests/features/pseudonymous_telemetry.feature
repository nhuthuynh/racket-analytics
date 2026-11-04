# ST-075a (story ST-075 "We know when R1 is unhealthy"; NFR-069.1; threat notes T5-OB-1, T5-OB-2).
# Integration level: IT-05-01 backend/tests/integration/test_it_05_pii_labels.py.
# API binding: backend/tests/features/test_pseudonymous_telemetry.py (a real OTLP/HTTP receiver
# on 127.0.0.1, the API and worker entry points in their own processes, real Postgres and object
# store for the demo run).
@story-ST-075 @ticket-ST-075a @nfr-069
Feature: Telemetry reaches the collector without personal data

  Scenario: The API and the worker export their metrics to the configured collector
    Given a metrics collector endpoint is configured
    When the API answers a request and the worker refuses an upload
    Then the collector receives metrics from the API and from the worker
    And no exported attribute holds an email, a nickname or a signed URL

  Scenario: A demo run leaves no personal data in metric attributes or logs
    Given Ivy has created a match with Carlos in the title and uploaded its video
    When the worker processes the video and Carlos tries to open Ivy's match
    Then no metric attribute or log line holds an email, a nickname or a signed URL
