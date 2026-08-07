# Codex planning runs

Use this reference when the operator asks Codex to use `/plan` or to perform a design/planning pass over a repo.

## Learned pattern

Codex CLI may not expose a native `/plan` command in the selected loadout. Do not assume it exists. Check command inventory first:

```bash
cd /home/<operator>/projects/<GITHUB_REPO_NAME>
python scripts/list_runtime_commands.py --runtime codex --loadout <loadout>
```

If `/plan` is absent, use the `project-planner` loadout and convert the operator's request into a normal initial prompt that explicitly says it is the `/plan` equivalent.

## Prompt requirements

For a repo design/planning pass, include:

- target repo path and current branch
- original user request
- note that native `/plan` is unavailable if inventory proved that
- planning/design mode instruction
- scope of files/docs to inspect
- external docs to consult, with official docs preferred
- constraints and out-of-scope boundaries
- concrete deliverables to write inside the repo
- verification commands
- closeout contract with changed files, verification output, blockers, and next steps

## Launch shape

Use the managed runner, not raw Codex, unless doing a narrow diagnostic:

```bash
python scripts/run_loaded_agent.py \
  --runtime codex \
  --loadout project-planner \
  --repo /path/to/repo \
  --task-file /tmp/enhanced-prompt.md \
  --label <short-label> \
  --bypass-permissions \
  --watch \
  --watch-seconds 1800 \
  --json
```

The current Codex default model should be pinned in `/home/<operator>/.codex/config.toml` when the operator asks for a persistent default. Verify with:

```bash
HOME=/home/<operator> codex --strict-config --version
python3 - <<'PY'
import tomllib
from pathlib import Path
print(tomllib.loads(Path('/home/<operator>/.codex/config.toml').read_text()).get('model'))
PY
```

For visible runs, capture proof from the pane/status line when possible, e.g. `gpt-5.5 default · ~/projects/<repo>`.

## Pitfalls

- Do not claim `/plan` worked unless Codex actually accepted `/plan` or inventory proves the command exists.
- Do not block on the absence of `/plan`; the project-planner loadout plus explicit prompt is the right fallback.
- Do not commit generated planning docs unless the operator explicitly approves a commit.
