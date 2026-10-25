# Environment Baseline

Recorded before implementation on the project workstation:

| Tool | Observed value |
|---|---|
| Python | 3.11.9 |
| Java | Not installed yet |
| Docker CLI | 29.2.1 |
| Docker engine | CLI present, daemon not running when checked |
| Docker Compose | v5.1.0 |
| Node.js | v24.14.0 |
| npm | 11.9.0 |
| kubectl | v1.34.1 client |
| kind | Not installed |
| minikube | Not installed |
| Host architecture | macOS ARM64 |

The first execution target is the owner's computer. No cloud account or resource is required for the sample workflow. Oracle remains an optional future deployment target.

The batch runner uses PySpark 3.5.8. Its documented Java options are 8, 11, and 17; use Java 17 for this project. See [Spark's installation requirements](https://spark.apache.org/docs/3.5.8/api/python/getting_started/install.html).

## Before the first cloud command

1. Confirm the Oracle account and home region.
2. Confirm billing alerts or a zero-spend limit where available.
3. Record the tenancy/compartment identifiers in a local ignored `.env` file, never in Git.
4. Run a read-only identity check before provisioning anything.
5. Provision only the smallest approved resources and record their names.

