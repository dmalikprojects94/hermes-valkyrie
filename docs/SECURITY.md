# Security Policy

## Reporting a vulnerability

If you believe you have found a security issue, please report it privately
rather than opening a public issue.

- Open a private security advisory on the repository hosting platform, or
- If advisories are unavailable, open a minimal public issue that asks for a
  private contact channel without disclosing vulnerability details.

Please include enough detail to reproduce the issue and a suggested severity.
You can expect an acknowledgement and a first assessment within a reasonable
window.

## Scope

This project routes and materializes agent configuration files. The most
relevant classes of issue are:

- Secrets or credentials committed to the repository.
- A generated runtime surface that leaks environment values or personal paths.
- A routing or apply path that writes outside its intended target directory.

## Secrets handling

- Secrets live only in your local `.env`, which is git-ignored and never
  committed. Use `.env.example` as the template.
- Never paste real tokens, IDs, or absolute machine paths into committed files,
  including tests and documentation.
- Generated runtime homes and raw run evidence are local-only and are not part
  of the tracked source.

## Supported versions

This is an evolving baseline. Security fixes target the current `main` branch.
