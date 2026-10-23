# Environment Baseline

Recorded before implementation on the project workstation:

| Tool | Observed value |
|---|---|
| Python | 3.11.9 |
| Java | Not installed yet |
| Docker | 29.2.1 |
| Docker Compose | v5.1.0 |
| Node.js | v24.14.0 |
| npm | 11.9.0 |
| kubectl | v1.34.1 client |
| kind | Not installed |
| minikube | Not installed |

The cloud target is Oracle Cloud Always Free. No Oracle account or cloud resource has been connected or created yet. Add account, region, VM shape, and Kubernetes runtime details after the owner connects the account.

## Before the first cloud command

1. Confirm the Oracle account and home region.
2. Confirm billing alerts or a zero-spend limit where available.
3. Record the tenancy/compartment identifiers in a local ignored `.env` file, never in Git.
4. Run a read-only identity check before provisioning anything.
5. Provision only the smallest approved resources and record their names.

