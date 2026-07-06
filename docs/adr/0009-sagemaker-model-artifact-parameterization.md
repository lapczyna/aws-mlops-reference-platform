# ADR-0009: SageMaker Model and Container Image as Deploy-Time Parameters

## Status

Accepted

## Context

The Step Functions state machine's `RunBatchTransformJob` state must reference
a real `AWS::SageMaker::Model` resource, which in turn requires a container
image URI and a `ModelDataUrl` pointing to a packaged model artifact in S3.
But per the [roadmap](../roadmap.md), training and packaging the Iris model
artifact is Phase 3 work -- it happens *after* this infrastructure phase.
This creates an apparent ordering problem: how can Phase 2 create a working
`AWS::SageMaker::Model` resource that references an artifact that doesn't
exist yet?

The resolution rests on a specific, verifiable fact about the SageMaker API:
**`CreateModel` only registers metadata.** It does not eagerly read or
validate the S3 object at `ModelDataUrl`, nor does it validate that the
container image is pullable. Those checks only happen later, when a
Transform (or hosting) job actually tries to use the model. This means the
`AWS::SageMaker::Model` resource can be created successfully in Phase 2, and
will simply fail at *execution* time (not stack *deployment* time) until
Phase 3 uploads the real artifact -- which is exactly the phase boundary we
want.

The container image URI is a second wrinkle: AWS publishes the prebuilt
scikit-learn inference container at a different ECR account ID per region,
and that mapping is long (and occasionally changes as AWS adds framework
versions), so hard-coding a `Mappings` block risked shipping a subtly wrong
or stale URI without an easy way to verify it in this environment.

## Decision

We expose both values as CloudFormation parameters rather than hard-coded
resource properties:

- `SklearnContainerImage` -- defaults to the us-east-1 scikit-learn 1.2-1
  CPU container URI. Deploying to another region requires overriding this
  parameter with the correct region's URI (documented lookup method in the
  parameter description and the deployment guide).
- `ModelArtifactS3Key` -- defaults to `model/model.tar.gz`, the key Phase 3's
  packaging script will upload the trained artifact to, inside the
  `ModelArtifactsBucket` this stack creates.

## Consequences

- **The full stack, including the SageMaker Model resource, deploys
  successfully in Phase 2** with zero application code or trained model
  artifact in place, satisfying "infrastructure should deploy successfully"
  without pulling Phase 3 work forward.
- **The first real Batch Transform job will fail** until Phase 3 uploads an
  actual `model.tar.gz` to the artifacts bucket -- this is expected,
  intentional, and clearly documented, not a bug to route around.
- **Region portability is explicit, not silent.** Deploying outside
  us-east-1 requires a deliberate parameter override, with the lookup
  method documented right on the parameter, rather than a template that
  quietly deploys a Model resource pointing at an image that doesn't exist
  in the target region.
- Re-running Phase 3's model packaging step never requires a template or
  infrastructure change -- it only uploads a new object to a key this stack
  already knows about, keeping infrastructure and ML artifact lifecycles
  decoupled per the [ML Lens guidance](../architecture/overview.md#aws-ml-lens-considerations).
