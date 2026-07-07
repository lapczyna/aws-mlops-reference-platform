# Documentation Index

| Category           | Document                                                                 |
| -------------------- | ---------------------------------------------------------------------------- |
| **Architecture**       | [Architecture overview](architecture/overview.md) -- system context, containers, components, data model, Well-Architected mapping |
|                       | [Sequence diagrams](architecture/sequence-diagrams.md) -- every request/job flow in detail |
|                       | [Scalability and performance](architecture/scalability.md) -- bottleneck analysis, scaling levers, cold starts |
| **Decisions**          | [Architecture Decision Records](adr/README.md) -- why each significant choice was made |
| **Security**            | [Security guide](guides/security-guide.md) -- IAM, data protection, input validation, dependency scanning |
|                        | [Threat model](security/threat-model.md) -- STRIDE walkthrough per trust boundary |
| **Standards**          | [Naming conventions](standards/naming-conventions.md) -- AWS resource, IaC, and code naming |
|                       | [Coding standards](standards/coding-standards.md) -- typing, layering, SOLID, testing, security review checklist |
| **Guides**             | [Development environment](guides/development-environment.md) -- local setup, tooling, testing |
|                        | [Developer guide](guides/developer-guide.md) -- how to add an endpoint, a state machine state, debugging tips |
|                       | [Deployment strategy](guides/deployment-strategy.md) -- environments, promotion flow, IaC approach |
|                       | [Deployment guide](guides/deployment-guide.md) -- concrete `sam build`/`deploy` steps, CI/CD setup, teardown |
|                       | [Cost guide](guides/cost-guide.md) -- worked estimates, cost levers |
|                        | [Disaster recovery guide](guides/disaster-recovery.md) -- RTO/RPO, backup/restore procedures |
| **Runbooks**           | [Runbook index](runbooks/README.md) -- stuck jobs, high failure rate, API 5xx, deployment rollback |
| **Contributing**        | [CONTRIBUTING.md](../CONTRIBUTING.md) -- PR process, definition of done |
| **Planning**           | [Project roadmap](roadmap.md) -- phased delivery plan and future enhancements |
|                        | [Design review](design-review.md) -- staff-engineer-style review of the finished repository |

Start with the [root README](../README.md) for a project overview, then the
[architecture overview](architecture/overview.md) for how the system fits
together.
