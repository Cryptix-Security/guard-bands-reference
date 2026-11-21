.PHONY: install-dev test lint format typecheck check demo reference-demo dual-channel-demo mcp-demo dual-channel-keys agentdojo-style-eval redteam-control-plane bench run

PYTHON ?= python3

install-dev:
	$(PYTHON) -m pip install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest

LINT_PATHS = app dual_channel guardbands_sdk integrations reference_app examples scripts tests demo_llm_attack.py

lint:
	$(PYTHON) -m ruff check $(LINT_PATHS)
	$(PYTHON) -m ruff format --check $(LINT_PATHS)

format:
	$(PYTHON) -m ruff check --fix $(LINT_PATHS)
	$(PYTHON) -m ruff format $(LINT_PATHS)

typecheck:
	$(PYTHON) -m mypy

# Everything CI runs.
check: lint typecheck test

demo:
	$(PYTHON) scripts/fastapi_demo.py

reference-demo:
	$(PYTHON) scripts/reference_app_demo.py

dual-channel-demo:
	$(PYTHON) scripts/dual_channel_demo.py

mcp-demo:
	$(PYTHON) -m examples.mcp_guarded_tools

agentdojo-style-eval:
	$(PYTHON) scripts/evaluate_agentdojo_style.py

redteam-control-plane:
	$(PYTHON) scripts/redteam_control_plane.py

# Emit a fresh Ed25519 keypair in env-file form:
#   make dual-channel-keys > .env.dual-channel
dual-channel-keys:
	@$(PYTHON) -c "from guardbands import generate_ed25519_keypair as g; priv, pub = g(); print('DUAL_CHANNEL_SIGNING_KEY=' + priv); print('DUAL_CHANNEL_VERIFY_KEY=' + pub)"

bench:
	$(PYTHON) scripts/benchmark_parser.py

run:
	uvicorn app.main:app --reload
