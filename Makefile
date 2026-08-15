.PHONY: install-dev test demo reference-demo dual-channel-demo dual-channel-keys agentdojo-style-eval redteam-control-plane bench run

PYTHON ?= python3

install-dev:
	$(PYTHON) -m pip install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest

demo:
	$(PYTHON) scripts/fastapi_demo.py

reference-demo:
	$(PYTHON) scripts/reference_app_demo.py

dual-channel-demo:
	$(PYTHON) scripts/dual_channel_demo.py

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
