---
name: Bug Report
about: Create a report to help us improve quarantine-ledger
title: '[BUG] '
labels: ['bug']
assignees: ''
---

## Describe the Bug

A clear and concise description of what the bug is.

## Steps to Reproduce

1. Quarantine ledger configuration (`quarantine.toml`):
   ```toml
   # Paste minimal quarantine TOML here
   ```
2. Inventory file (`tests.json`):
   ```json
   []
   ```
3. Command executed:
   ```bash
   quarantine-ledger check quarantine.toml --inventory tests.json --today YYYY-MM-DD
   ```
4. Output and exit code received.

## Expected Behavior

A clear and concise description of what you expected to happen.

## Environment

- OS: (e.g. Linux Ubuntu 22.04, Windows 11, macOS 14)
- Python Version: (`python --version`, e.g. Python 3.11.8)
- `quarantine-ledger` version: (`quarantine-ledger --version`)

## Additional Context

Add any other context or terminal logs here. Ensure no confidential data, passwords, or personal identifiable information (PII) are included.
