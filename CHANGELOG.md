# Changelog

All notable changes to this project are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project follows [Semantic Versioning](https://semver.org/); one tagged
release corresponds to one completed phase of the [roadmap](docs/roadmap.md).

## [Unreleased]

## [0.1.0] - 2026-07-06

### Added -- Phase 1: Repository Foundation

- Repository skeleton following Clean Architecture layering
  (`api` / `application` / `domain` / `infrastructure` / `shared`), no
  business logic yet.
- Architecture documentation: system context, container, component, and
  Step Functions state diagrams
  (`docs/architecture/overview.md`).
- Sequence diagrams for every request/job flow
  (`docs/architecture/sequence-diagrams.md`).
- Architecture Decision Records 0001-0008 covering the serverless-first
  approach, SageMaker Batch Transform selection, Step Functions
  orchestration, DynamoDB data model, API Gateway REST API choice, Lambda
  Layer packaging, and the asynchronous job processing pattern.
- Naming conventions and coding standards documentation.
- Development environment guide and deployment strategy guide.
- Project roadmap covering Phases 1-4 and deferred future enhancements.
- Tooling baseline: `pyproject.toml` (Ruff, Black, mypy strict, pytest,
  coverage), `.pre-commit-config.yaml`, `Makefile`.
