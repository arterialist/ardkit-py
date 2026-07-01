# Contributing to ardkit

Thanks for helping make agentic resources discoverable!

## Dev setup

```bash
uv sync --group testing --group lint --group dev
uv run pre-commit install
```

## Before you push

```bash
uv run ruff check src tests
uv run ruff format src tests --check
uv run pyright src/ardkit
uv run pytest
```

## Guidelines

- Keep the package core dependency-light (only `pydantic`). Framework code lives
  behind optional extras and lazy/guarded imports.
- New entry shapes or fields must round-trip through `ardkit.validation` against
  the vendored JSON Schema — add a conformance test.
- Don't hand-edit files in `src/ardkit/schemas/`; refresh them with
  `python scripts/vendor_schemas.py` and review the diff.
- Update `CHANGELOG.md` under `[Unreleased]`.

## Releasing

1. Bump `src/ardkit/__about__.py` and move the changelog section.
2. Tag and create a GitHub Release — `release_pypi.yaml` publishes to PyPI via
   OIDC trusted publishing.
