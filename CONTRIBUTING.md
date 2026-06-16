# Developer Guide

## Setup

```bash
uv sync
```

## Format and linting

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.
The checks are run automatically on every pull request in the [GitHub Actions workflow](.github/workflows/lint.yml)
and are a pre-condition for merging.

To run the same  checks locally:

```bash
uv run ruff format src/ # format the project in-place
uv run ruff check --fix src/ # Run linters and auto-fix issues
uv run pyright src/ # Type-check   
```


These checks also run automatically on every pull request and pushes to main via
the [github workflow](./.github/workflows/lint.yml)

## Proto dependencies

Generated code is pulled from the [Buf Schema Registry](https://buf.build/beyer-labs/h2pcontrol) via the
`buf.build/gen/python` index configured in `pyproject.toml`. To update to the latest proto versions:

```bash
uv sync --upgrade
```

## Releasing a new version
When you want to release a new version,
create a pull request that bumps the version in [pyproject.toml](pyproject.toml).
Once that is merged, from main run:
```bash
 git tag <version> && git push origin <version> 
```
After tagging you can create a release from the Github Repository.
