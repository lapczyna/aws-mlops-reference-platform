# ADR-0006: API Gateway REST API over HTTP API

## Status

Accepted

## Context

API Gateway offers two relevant product types: **REST API** and **HTTP
API**. HTTP API is cheaper (roughly 70% lower cost per request) and has
lower latency, and would satisfy this platform's four simple routes on its
own. REST API costs more per request but includes several enterprise-grade
features HTTP API lacks or only partially supports:

- **Request validation** against JSON Schema models at the API layer,
  rejecting malformed payloads before they reach Lambda.
- **Usage plans and API keys** for per-client throttling and quota
  management.
- **Native AWS WAF integration** at the API Gateway resource level.
- **Private (VPC-endpoint-only) API deployment**, relevant for an internal
  platform posture.

At this platform's expected request volume (a demonstration/reference
system, not a high-traffic production service), the absolute cost delta
between REST and HTTP API is a few dollars a month at most -- immaterial
next to the value of demonstrating these enterprise controls.

## Decision

We will use **API Gateway REST API** (regional endpoint), with:

- Request validation models (JSON Schema) on `POST /jobs` and
  `POST /datasets/upload-url`.
- Structured access logging to CloudWatch Logs (JSON format, correlation
  ID included).
- Throttling configured at the stage level as a baseline defense against
  abuse, with usage plans available as a future extension point per client.

## Consequences

- **Malformed requests are rejected at the edge**, before incurring a
  Lambda invocation -- both a cost and a security benefit (reduced attack
  surface reaching application code).
- **Slightly higher per-request cost and latency** than HTTP API, which is
  an explicit, documented trade-off rather than an oversight.
- **WAF and private endpoint support are available** if a future phase
  needs them, without an API type migration.
- The technology stack constraint for this project explicitly specifies
  "API Gateway REST API," so this ADR also records the reasoning behind
  that given constraint for future readers, rather than treating it as an
  unexamined default.
