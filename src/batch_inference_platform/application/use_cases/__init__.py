"""Use cases: one class per application capability (e.g. SubmitBatchJob, GetJobStatus).

Use cases depend only on domain entities and ports (interfaces) -- never on
concrete infrastructure implementations. Dependencies are injected at the
handler composition root.
"""
