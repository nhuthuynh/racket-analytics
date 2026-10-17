# Sprint 4, ticket C4-CA (sre-devops-engineer; VR3-S3-01). Written before the binding ran green.
# Binding: infra/tests/test_compose_extra_ca_scenarios.py renders infra/compose.yaml with the real
# `docker compose config`, then builds one probe image through the real compose secret wiring
# (a throwaway CA, never committed) and searches every layer of it for the certificate.
@ticket-C4-CA @VR3-S3-01
Feature: Build behind a TLS-intercepting proxy (VR3-S3-01)
  Rule: EXTRA_CA_FILE is off by default; when set, every built service receives it as the
        BuildKit secret extra_ca, which never lands in an image layer

    Scenario: No extra CA -> no secret, no CA in image
      Given no extra CA file is configured
      When the stack images are built
      Then no build service receives the secret "extra_ca"
      And the probe build saw no secret "extra_ca"
      And no image layer holds the certificate

    Scenario: Extra CA configured
      Given EXTRA_CA_FILE names a CA certificate
      When the stack images are built
      Then every build service receives the secret "extra_ca"
      And the probe build read that certificate as the secret "extra_ca"
      And no image layer holds the certificate
