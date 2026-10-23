# Oracle Cloud Preparation

This project is prepared for Oracle Cloud Free Tier, but this document does not create resources or require account credentials.

## Why Oracle

Oracle advertises Always Free compute resources with no expiration. Current official limits include up to two AMD micro VMs or an Ampere A1 allocation equivalent to 2 OCPUs and 12 GB memory, subject to region and capacity limits. See the [official Always Free resource list](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

The project will use the smallest Kubernetes-capable setup that fits the account. ARM instances may require ARM-compatible container images and dependencies. If capacity is unavailable, do not upgrade the account automatically. Record the failure and choose a different region or a different approved provider.

## Account handoff

The account owner must provide these values locally, never in Git:

```text
OCI_REGION=
OCI_COMPARTMENT_ID=
OCI_TENANCY_ID=
OCI_USER_ID=
OCI_FINGERPRINT=
OCI_PRIVATE_KEY_PATH=
OCI_AVAILABILITY_DOMAIN=
```

Use `.env.example` for names only. Put real values in `.env`, which is ignored by Git.

## Preparation order

1. Create or connect the Oracle account manually.
2. Enable billing alerts and confirm the free-tier resource limits.
3. Install and authenticate the OCI CLI locally.
4. Run an identity and region read-only check.
5. Select a free-tier-compatible VM shape.
6. Prepare a small Kubernetes runtime, preferably k3s or another lightweight distribution.
7. Add only the minimum deployment manifests for the project.
8. Deploy a health-check-only smoke service before Kafka, Cassandra, or Spark.
9. Record the command, resource names, region, shape, and cleanup command in `evidence/`.

## Cost and safety rules

- Do not create paid resources automatically.
- Do not switch to Pay As You Go to bypass capacity errors without explicit owner approval.
- Do not deploy the full stack before the health-check smoke test works.
- Do not expose Kafka, Cassandra, or databases directly to the public internet.
- Stop or delete non-free resources after testing.
- Keep a resource inventory and cleanup command in the deployment evidence.

## Current status

Account connection: pending.

Cloud resources: none created.

Deployment manifests: to be added after the account and VM shape are confirmed.

