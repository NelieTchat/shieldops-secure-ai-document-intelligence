# ADR 0014: User Provisioning by Admin Seed Job

## Status
Accepted

## Context
The api originally let anyone create an account through POST /auth/register.
For a system that stores sensitive documents, open self-registration with no
identity verification is not acceptable outside the sandbox demo. The api now
refuses registration unless REGISTRATION_ENABLED is set, and the Kubernetes
manifest sets it to false. That closes the hole but leaves a gap: in a real
cluster there is no way to create the first user, or any later one.

The reference architecture serves a small, known set of users. Related
decisions: ADR 0010 already runs one-off administrative work as Kubernetes
Jobs with a least-privilege IRSA role instead of a bastion, and ADR 0012
removes any pipeline or human path that needs direct cluster credentials.

## Decision
Create users with a Kubernetes Job, following the pattern of ADR 0010.

A Job named user-seed runs in the shieldops-jobs namespace, from the same image
as the api, with a different command. It reads a Secrets Manager secret that
maps usernames to initial passwords, hashes each password with the api's own
Argon2 code, and creates the user through the api's service layer. Because it
calls the service layer directly, it does not depend on REGISTRATION_ENABLED.

The secret is created by an operator outside Git and outside Terraform state,
so no password is ever committed. The Job runs under its own IRSA role that can
read only that secret and the database credential. The Job is idempotent:
usernames that already exist are skipped and their passwords are never
overwritten. It logs usernames and counts only, never passwords.

Adding a user means updating the secret and running the Job again. Secret reads
are recorded in CloudTrail, and Job runs are visible as Kubernetes events, which
gives an audit trail for who was provisioned and when.

## Alternatives Considered
**Admin-only API endpoint.** Rejected. It needs a role model, has a bootstrap
problem (the first admin must still be created some other way), and adds
internet-facing attack surface to the most sensitive operation in the system.

**Federated login (OIDC with Cognito or an agency identity provider).**
Rejected for now, not forever. It is the realistic long-term answer for
GovCloud, but it is the largest change and needs an identity provider to design
against. This decision does not block it: once federation exists, the seed Job
and local passwords can be retired.

**Leave registration open behind the WAF or an allow-list.** Rejected. An
allow-list of source addresses is not an identity check, and the control would
live outside the application that depends on it.

## Consequences
- There is no self-service sign-up. Every account is created deliberately.
- There is still no password-change endpoint. Rotating a password currently
  means deleting the user row and re-seeding. A change-password endpoint is a
  follow-up.
- New work follows from this decision: a seed script in the api image with
  tests, a Terraform IRSA role and an empty secret container for user-seed, and
  a Job manifest in shieldops-jobs next to the db-migration Job from ADR 0010.
- The sandbox demo keeps working because the local environment file sets
  REGISTRATION_ENABLED=true.
