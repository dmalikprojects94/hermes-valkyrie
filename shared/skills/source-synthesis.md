# Source Synthesis

Combine completed source reports into recurring patterns and candidate clusters. Synthesis **cannot invent claims** not present in state/reports.

## When to use

Several repos in a list have completed ingestion reports and you want the cross-cutting picture before proposing loadouts.

## Process

The synthesis automation for this workflow lives in the maintainer development workspace and does not ship with the public repo; follow the steps manually or with your own tooling. Combine the alias's completed reports into a synthesis document in your maintainer notes.

## Output sections

- completed reports
- missing reports
- recurring patterns
- superseded ideas
- risky ideas
- candidate clusters
- next audits
- migration micro-passes

## Hard rules

- Report only what is recorded in state and on-disk reports. Qualitative claims (recurring patterns beyond derived counts, candidate clusters, risky ideas) come from operator-recorded state, not invention.
- Synthesis migrates nothing.

## Verification

Re-run the synthesis and confirm the output is stable, then run:

```bash
python scripts/validate_loadouts.py
python scripts/smoke_clean_hermes_onboarding.py --json
```

## Provenance

- Source: internal Hermes-operator design; see the maintainer utility-skill audit notes (utility skill 11, not shipped publicly).
- Disposition: repo-resident onboarding utility skill; not wired into `default`; available through the explicit `loadout-management` loadout.
- Notes: backed by synthesis tooling in the maintainer development workspace.
