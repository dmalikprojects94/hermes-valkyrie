# DevOps Ops

Use this skill for the lightweight operational checks that should be available from every loadout, and for deeper infrastructure work when selected through the `devops` loadout.

## Default posture

- Identify the live environment, deployment target, branch, secrets boundary, and rollback path before changing operational systems.
- Prefer read-only inspection before mutation: status, logs, config diff, dry-run, and health checks.
- Treat deploys, DNS, databases, credentials, queues, cron, containers, CI, and infra as side-effectful even when the code change is small.
- Keep commands copyable and evidence-backed; report exact health checks and whether they passed.

## Escalate to the `devops` loadout when

- The task is primarily deployment, hosting, CI/CD, observability, containers, server recovery, networking, or infrastructure design.
- The work needs a runbook, rollback plan, secret/environment audit, production smoke test, or incident-style closeout.

## Closeout

Report: target system, change made or skipped, verification commands, rollback handle, remaining risk, and whether follow-up monitoring is needed.
