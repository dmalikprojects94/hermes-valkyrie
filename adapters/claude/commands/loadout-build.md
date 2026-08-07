# /loadout-build

## Purpose

Admission-test a candidate capability against the default backbone.

## Procedure

1. Compare the candidate against default-loadout criteria using the `loadout-builder` skill.
2. State whether it belongs in default, a specialty loadout, or nowhere.
3. If warranted, draft the design by hand: name the target loadout (new or patched), the exact `shared_skills`, `shared_instructions`, and `packs` wiring changes, and the files under `loadouts/` and `shared/` the change would touch.
4. Recommend exact wiring if admitted. Review the drafted design with the operator before touching manifests.
5. Apply only after operator review, then verify with the public gates:
   ```bash
   python scripts/validate_loadouts.py
   python scripts/smoke_clean_hermes_onboarding.py --json
   ```

Note: Registry automation for this workflow is maintainer development-workspace tooling and does not ship with the public repo.

## Required output shape

- **Candidate**
- **Admission Test**
- **Verdict**
- **Wiring Plan**
- **Verification output** (if gates were run)

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.

## Provenance

- Source: local Claude-OC-System default command inventory plus internal Hermes-operator adaptation.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: exposes shared default behavior as Claude slash-command workflow surface.
