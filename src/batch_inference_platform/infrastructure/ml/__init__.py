"""Intentionally empty.

Batch Transform jobs are launched and monitored directly by Step Functions'
optimized `.sync` SageMaker integration (see
statemachine/job_orchestration.asl.json and ADR-0004) -- there is no Lambda
code in the invocation path, so no adapter belongs here. Kept as a package
in case a future need (e.g. inspecting a transform job's metrics from a
Lambda) requires one.
"""
