# Contributing

Contributions are welcome, especially threat-model feedback, bypass attempts, tests, docs, and integrations.

## Development

Use Python 3.12 for local development. CI currently tests Python 3.11 and 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
make check   # ruff lint + format check, strict mypy baseline, pytest
```

CI runs the same gates as the core `guard-bands` repo: Ruff lint, Ruff format
check, strict mypy on the files listed under `[tool.mypy]` in `pyproject.toml`,
and pytest on Python 3.11 and 3.12. `make format` applies Ruff fixes. When you
fully type another module, add it to the mypy `files` list.

## Pull Requests

- Keep changes focused.
- Add tests for security-relevant behavior.
- Update docs when changing protocol, context, replay, key, or deployment behavior.
- Do not commit real secrets, tokens, `.env` files, or private infrastructure details.

## Security Changes

Changes touching cryptography, parsing, replay protection, key handling, authentication, audit logging, CI, or dependency pins should receive extra review.

