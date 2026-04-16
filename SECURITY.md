# Security Policy

## Supported Versions

Only the latest stable release receives security fixes. Older versions are not backported.

| Version | Supported |
| ------- | --------- |
| 0.7.x   | Yes       |
| < 0.7   | No        |

## Reporting a Vulnerability

**Please do not file a public GitHub issue for security vulnerabilities.**

Use [GitHub's private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability) feature instead:

1. Go to the [Security tab](https://github.com/schinnam/lingo/security) of this repository.
2. Click **"Report a vulnerability"**.
3. Fill in the report form with as much detail as possible (steps to reproduce, impact, affected versions, and any suggested fixes).

Your report will be visible only to the repository maintainers. GitHub will notify you when the report is triaged.

## Response Timeline

| Milestone             | Target window |
| --------------------- | ------------- |
| Initial acknowledgement | 3 business days |
| Triage and severity assessment | 7 days |
| Patch and advisory published | 30 days (critical: 14 days) |

We will keep you informed of progress throughout the process. If a deadline cannot be met we will communicate that in the private thread.

## Common Attack Surfaces

The following areas are of particular interest for this project:

- **`LINGO_DATABASE_URL` in logs or error messages** — the connection string contains credentials; ensure it is never surfaced in stack traces or HTTP responses.
- **JWT secret (`LINGO_SECRET_KEY`) strength and rotation** — weak or reused secrets allow session forgery; report any code path that logs or exposes this value.
- **Slack token scope over-provisioning** — tokens should request only the minimum required OAuth scopes; over-scoped tokens expand blast radius on compromise.
- **SSRF via Slack OAuth redirect URIs** — unvalidated redirect parameters in the OAuth callback flow can be abused to forward requests to internal services.

## Out of Scope

The following are **not** considered security vulnerabilities for this project:

- Issues that require physical access to the server or database host.
- Denial-of-service attacks that require sending large volumes of traffic.
- Vulnerabilities in third-party dependencies that have no confirmed impact on Lingo (please report those upstream).
- Missing security headers that are handled by a reverse proxy in the recommended deployment configuration.
- Findings from automated scanners submitted without a proof-of-concept or evidence of real-world impact.
