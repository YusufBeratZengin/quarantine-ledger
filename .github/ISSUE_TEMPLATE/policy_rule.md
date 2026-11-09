---
name: Policy Rule Proposal
about: Propose a new quarantine policy check or gate validation rule
title: '[RULE] '
labels: ['enhancement', 'policy']
assignees: ''
---

## Proposed Policy Rule

Name and description of the quarantine rule:
Example: "Hard budget limit per test runner directory" or "Disallow quarantine without linked ticket component"

## Motivation & CI Quality Value

Why is this rule beneficial for engineering teams maintaining quarantine lists?

## Validation Semantics

- **Validation Level**: [ ] Syntax/TOML parsing (Exit code 2) / [ ] Policy finding (Exit code 1 or 2)
- **Configuration in `[policy]`**:
  ```toml
  [policy]
  # proposed configuration key
  ```
- **Finding Code**: (e.g. `RULE_NAME_EXCEEDED`)
- **Deterministic Evaluation**: How will this remain deterministic across local machines and CI runners?

## Alternatives & Trade-offs

Any edge cases or potential false alarms?
