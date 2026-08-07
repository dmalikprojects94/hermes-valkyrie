# /verify

## Purpose

Check that the requested artifact actually works using concrete evidence.

## Procedure

1. List the expected behavior.
2. Run the narrowest checks that prove or disprove it.
3. Quote the real command output or artifact path.
4. Fail loudly if the result is not verified.

## Required output shape

- **Target**
- **Checks Run**
- **Observed Output**
- **Verdict**

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.

## Provenance

- Source: local Claude-OC-System default command inventory plus internal Hermes-operator adaptation.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: exposes shared default behavior as Claude slash-command workflow surface.
