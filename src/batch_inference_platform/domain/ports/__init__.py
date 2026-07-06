"""Ports: abstract interfaces the application layer depends on.

Concrete adapters (DynamoDB, S3, Step Functions, SageMaker) live in the
infrastructure layer and implement these interfaces, keeping the dependency
arrow pointing inward per Clean Architecture / the Dependency Inversion
Principle.
"""
