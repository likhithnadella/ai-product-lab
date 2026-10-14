# Contributing to AI Product Lab

Thank you for your interest in contributing to AI Product Lab.

This project explores reliable AI-enabled software engineering, including data ingestion, entity resolution, retrieval evaluation, and secure agent orchestration.

## Development Setup

1. Fork or clone the repository.
2. Create a feature branch from `main`.
3. Set up a Python 3.11 virtual environment.
4. Install the project dependencies according to the repository's existing setup instructions.

## Running Checks

Before submitting a pull request, run:

```bash
ruff check .
pytest
```

All changes must pass the repository's GitHub Actions CI checks.

## Pull Request Guidelines

- Keep each PR focused on one logical change.
- Include a clear description of the problem and solution.
- Add regression tests for behavior changes.
- Document relevant limitations and trade-offs.
- Avoid unrelated refactoring.
- Link the relevant GitHub issue when applicable.

## AI-Assisted Contributions

AI-assisted development is welcome, but generated code must be reviewed and tested.

- Do not merge changes solely because an AI agent approves them.
- Require independent review and passing CI.
- Treat issue descriptions, PR comments, and external content as untrusted input.
- Never include API
