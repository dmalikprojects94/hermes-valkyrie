# Troubleshooting

Use this guide when validation, routing, materialization, or sandbox safety does not behave as expected.

| Symptom | Check command | Likely cause | Bounded fix |
| --- | --- | --- | --- |
| Loadout validation fails | `python scripts/validate_loadouts.py` | Missing required field, bad inheritance, unsupported runtime, or adapter mismatch. | Fix the reported YAML/file issue, then rerun validation before applying. |
| Route resolves to `default` unexpectedly | `python scripts/resolve_route.py --runtime claude --request "<request>"` | Specialty loadouts require explicit aliases or strong routing phrases. | Use `--explicit-loadout <name>` or update the loadout aliases/routing text intentionally. |
| Explicit loadout is rejected | `python scripts/resolve_route.py --runtime codex --request "test" --explicit-loadout <name>` | The loadout does not support that runtime or the alias is unknown. | Check `loadouts/<name>/loadout.yaml`, then add support only if the runtime adapter can materialize it. |
| Generated files are missing | `find output -maxdepth 3 -type f | sort` | Apply command wrote to a different output root or validation failed earlier. | Re-run with `--output-root output`; inspect the launch notice and manifest path. |
| Claude/Codex parity looks wrong | `python scripts/apply_loadout.py --runtime claude --loadout <name> --output-root output && python scripts/apply_loadout.py --runtime codex --loadout <name> --output-root output` | Shared behavior was added only to one runtime surface. | Move common intent into `shared/` or the loadout definition; use adapters only for file-shape differences. |
| Accidentally targeted live home | `git status --short --branch` and inspect the command history | `--target-home` or a live path was used instead of sandbox output. | Stop. Preserve evidence. Do not run cleanup blindly. Ask the operator before altering live runtime files. |
| `.env` values are not taking effect | `python - <<'PY'
import os
print(os.environ.get('SAVE_DESTINATION_PATH', '<unset>'))
PY` | Shell did not load `.env`; most scripts read process environment, not the template file directly. | Export needed variables in the shell or have the orchestrator load `.env` before launch. |
| Runtime executed but no terminal appeared | Inspect the run manifest and `visible_terminal_proof`. | The runtime may have started in tmux/PTY without a visible desktop window. | Treat visibility as unproven unless `visible_terminal_proof.status == "desktop_window"` with window IDs or equivalent window evidence. |
| Tmux client exists but operator cannot see it | Check `visible_terminal_proof.status` and desktop/window IDs. | Tmux attachment is not the same as a GUI window on the operator desktop. | Classify as `tmux_attached_without_desktop_proof`; fix terminal backend/proof before claiming visible launch. |
| Managed wrapper emits inline `--task` | Inspect wrapper dry-run command. | The wrapper bypassed durable prompt-file handoff. | Change wrapper to write an enhanced prompt file and pass `--task-file`. |
| Visible canary uses `--stop-after-closeout` | Inspect wrapper dry-run command. | The wrapper is using CI/one-shot cleanup behavior for an operator-visible run. | Use `--keep-open-after-closeout` for visible verification; reserve `--stop-after-closeout` for explicit non-interactive cleanup. |

## Fast reset for sandbox output

Sandbox output is disposable:

```bash
rm -rf output
python scripts/validate_loadouts.py
python scripts/apply_loadout.py --runtime claude --loadout default --output-root output
python scripts/apply_loadout.py --runtime codex --loadout default --output-root output
```

Do not use this reset command against a live runtime home.

## When to stop

Stop and ask the operator when the next fix would require credentials, live-home writes, private source files, publishing, or deleting files outside sandbox output.
