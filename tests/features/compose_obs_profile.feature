# Sprint 5 ticket ST-075b (sre-devops-engineer; story ST-075; NFR-042.5; ADR 0057 §3; SEC-5 T5-OB-1,
# T5-OB-4, T5-OB-7). Written before the profile existed. Bindings:
# infra/tests/test_compose_obs_profile_scenarios.py (static: real or planted copies of
# infra/compose.yaml and the obs config files; `docker compose config`) and
# infra/tests/test_compose_obs_live.py (IT-05-02, a running stack with the obs profile).
@ticket-ST-075b
Feature: The obs Compose profile stores the R1 SLI series in Prometheus
  Rule: the collector and Prometheus run only with the obs profile, are never reachable from
        outside the host, and the API and purge export to the collector only when told to

    Scenario: A Prometheus port published on every interface is refused
      Given a copy of compose.yaml whose prometheus port is "0.0.0.0:9090:9090"
      When the obs profile check runs
      Then it fails naming "prometheus" and "0.0.0.0:9090:9090"

    Scenario: A Prometheus rule-file glob is refused
      Given a copy of prometheus.yml whose rule_files is "/etc/prometheus/rules/*.yml"
      When the obs profile check runs
      Then it fails naming "rule_files"

    Scenario: The shipped obs profile passes the check
      Given the shipped compose.yaml and obs config files
      When the obs profile check runs
      Then it reports no problem

    Scenario: Without the obs profile the stack and its exports are unchanged
      Given an env file copied from env.example
      When Compose renders the stack configuration
      Then "otel-collector, prometheus" are not in the stack
      And "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT" is "" in "api, purge"

    Scenario: The obs overlay turns on the profile and the metrics export
      Given an env file copied from env.example
      And the obs overlay appended to it
      When Compose renders the stack configuration
      Then "otel-collector, prometheus" are in the stack
      And "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT" is "http://otel-collector:4318/v1/metrics" in "api, purge"
      And "PURGE_INTERVAL_S" is "300" in "purge"

    @live
    Scenario: Both SLI series are in Prometheus after a demo upload (IT-05-02)
      Given a running stack with the obs profile
      When "make demo" uploads the demo video
      Then Prometheus has the series "http_server_request_duration_seconds_count"
      And Prometheus has the series "racket_upload_sessions_total" with event "completed"
      And the collector scrape target is up
      And Prometheus has loaded the rule group "billing"

    @live
    Scenario: The collector drops a metric attribute that is not on the allowlist (T5-OB-1)
      Given a running stack with the obs profile
      When a metric point with the attribute "user.email" is sent to the collector
      Then Prometheus has that series without a "user_email" label
