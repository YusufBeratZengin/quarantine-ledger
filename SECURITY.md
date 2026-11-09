# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in `quarantine-ledger`, please report it privately:

- **Email**: Send details to `118852217+YusufBeratZengin@users.noreply.github.com`
- **GitHub**: Use [Private Vulnerability Reporting](https://github.com/YusufBeratZengin/quarantine-ledger/security/advisories/new) on the repository.

Please do not open a public issue for security disclosures. Include:
- A description of the vulnerability and its potential impact.
- Steps to reproduce or a minimal proof of concept.
- Any suggested remediations.

We will acknowledge receipt within 48 hours and work with you on a coordinated fix and advisory.

## Security Model and Guarantees

`quarantine-ledger` is designed with the following security invariants:

1. **No Code Execution**: Ledger files are parsed strictly as TOML using Python's standard library `tomllib`. Test inventories are loaded as static JSON. No executable code or unsafe deserialization occurs.
2. **Offline Isolation**: The tool makes zero outbound network requests. Issue URLs are inspected offline using `urllib.parse` purely to check scheme and hostname syntax; no network sockets are opened.
3. **Safe File Writing**: The `demo` command uses exclusive creation modes (`open(..., "x")`) and atomic non-overwriting operations (`os.link` / `os.rename`) to prevent overwriting or truncating pre-existing files, including temporary staging files and race conditions where target files appear during execution.
4. **Privacy & PII Boundaries**: `quarantine-ledger` collects zero personal data and performs no outbound network telemetry. On `owner_team`, offline validation only checks that the value is non-blank and does not contain `@` (rejecting email addresses and `@handle` mentions). Because the tool runs offline without an organization directory, it **cannot** verify that `owner_team` is a real team label rather than a person's name or username, and it does not scan `owner_team`, `reason`, or `issue` URLs for personal data. Maintaining team labels instead of personal names—and keeping ledger fields free of PII—is the responsibility of repository maintainers.
