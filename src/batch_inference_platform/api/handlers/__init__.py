"""Lambda entrypoints: one thin handler per API Gateway route or state machine task.

Handlers parse the incoming event, delegate to an application use case, and
translate the result back into an API Gateway / Step Functions response.
No business logic belongs in this package.
"""
