# Running Under an Orchestrator

The Terminal Loadout System is a routing, materialization, and managed-launch
contract for terminal coding agents. It can be used from a shell, but it is
designed so Hermes or another orchestrator can drive Claude Code and Codex
without ambiguous startup behavior.

A complete orchestrated run is not just "start Claude" or "start Codex." It is:

```text
operator request
    │
    ▼
choose runtime + loadout
    │
    ▼
write durable enhanced prompt file
    │
    ▼
materialize/verify runtime surface
    │
    ▼
launch through managed runner
    │
    ▼
prove visible desktop window when requested
    │
    ▼
watch runtime completion
    │
    ▼
extract closeout + route reportback
    │
    ▼
record final lifecycle state
```

## Division of labor

| Concern | Owner |
| --- | --- |
| Choosing runtime (`claude` vs `codex`) | orchestrator/operator |
| Choosing loadout | explicit operator choice or deterministic resolver |
| Preparing prompt/spec | orchestrator wrapper before launch |
| Materializing runtime surface | this repo |
| Launching and supervising terminal runtime | managed runner or wrapper that emits the managed runner command |
| Proving desktop visibility | managed runner/orchestrator proof gate |
| Reportback transport | orchestrator or configured transport adapter |

## Required wrapper behavior

An orchestrator-side wrapper (for example, a Hermes gateway `terminal_agent`
tool or a `hermes loadout launch` command — these live in the orchestrator, not
in this repo) must
emit this command family for normal managed work:

```bash
python scripts/run_loaded_agent.py   --runtime <claude|codex>   --loadout <loadout-name>   --repo <target-repo>   --task-file <enhanced-prompt-file>   --bypass-permissions   --watch   --keep-open-after-closeout   --watch-seconds <seconds>   --json
```

The wrapper may add a deterministic `--label`, origin/reportback metadata, or
runtime-specific metadata. It must not use raw runtime CLIs as the normal path,
and it must not downgrade permission posture. For normal managed work,
`--bypass-permissions` is required; if a managed caller omits it, the start layer
must refuse before tmux is created instead of opening an approval-bound terminal.
Claude's final command must include `--dangerously-skip-permissions`; Codex's
final command must include `--dangerously-bypass-approvals-and-sandbox`.

## Dry-run before live launch

Before any live runtime launch, inspect the dry-run command. It should have:

```text
run_loaded_agent.py
--runtime <claude|codex>
--loadout <name>
--repo <target-repo>
--task-file <enhanced-prompt-file>
--bypass-permissions
--watch
--keep-open-after-closeout
--json
```

Reject these dry-run shapes:

```text
raw claude / raw codex / codex exec
ad-hoc tmux
inline --task for normal work
missing --loadout
missing --task-file
missing --bypass-permissions
missing --watch
--stop-after-closeout for operator-visible verification
```

## Prompt-file contract

The orchestrator must write or request a durable prompt file before launch. The
file should preserve the operator's request and add bounded execution details:
repo, runtime, loadout, scope, verification, permission posture, and reportback
expectations.

Do not paste private transport IDs into prompt prose. Origin/reportback IDs, when
used, are launch metadata or environment configuration.

## Visible terminal proof

If the operator expects to watch the run, the orchestrator must prove a desktop
terminal window opened. Tmux attachment alone is insufficient.

Acceptable proof:

- manifest shows `visible_terminal_proof.status == "desktop_window"`;
- proof includes one or more desktop/window IDs for the launched terminal title;
- or an equivalent Computer Use/accessibility/window-manager proof exists.

If the runtime process executed but no desktop-window proof exists, report it as
unproven visibility. Do not describe it as a successful visible launch.

## Reportback and lifecycle

A managed run is complete only after the watcher and closeout path are accounted
for. A useful final state records:

- runtime/loadout;
- prompt file path;
- manifest path;
- visible proof, if requested;
- watcher result;
- structured closeout status;
- reportback status or reason reportback was skipped;
- final terminal lifecycle (`open`, `stopped`, `closed`, or `needs_attention`).

## Approval gates

Stop and ask before live-home writes, authenticated runtime launches, external
reportback, gateway/service restarts, publication, or permission bypass in an
untrusted repo.

## Related documentation

- [Managed Visible Launch Contract](../guides/managed-visible-launch-contract.md)
- [Reportback Integration](reportback.md)
- [Live Home vs Output Mode](../guides/live-home-vs-output-mode.md)
