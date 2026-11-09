## Description

Briefly describe the change and its motivation or context.

Fixes #(issue)

## Type of Change

- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Documentation update
- [ ] Refactor or test improvement

## Quality Checklist

- [ ] I have run `bash scripts/check.sh` locally and all checks passed (Ruff lint, Ruff format, Mypy strict mode, Pytest with >=85% branch coverage).
- [ ] I have added tests for any new functionality or regression tests for bug fixes.
- [ ] I have updated both `README.md` and `README.tr.md` if CLI flags, behavior, or error formats were modified.
- [ ] I have recorded the change in `CHANGELOG.md` under `[Unreleased]` or the target version.
- [ ] Zero runtime dependencies invariant is maintained (stdlib only).
- [ ] No secrets, credentials, or personal identifiable information (PII) are included.
