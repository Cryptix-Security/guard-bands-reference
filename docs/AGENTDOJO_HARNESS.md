# AgentDojo Benchmark Harness

A harness for running Guard Bands as a defense in
[AgentDojo](https://github.com/ethz-spylab/agentdojo), the standard dynamic
benchmark for prompt-injection attacks and defenses on tool-calling LLM agents.

Unlike the structural smoke test in [`EVALUATION.md`](EVALUATION.md) (which
drives the two-channel API through test clients, no model), this runs a **real
agent against a real model** and measures attack success and task utility. Use
it to evaluate Guard Bands against any model/attack combination — including the
weaker or fine-tuned models and the adaptive attacks where a boundary control
has the most to prove.

## Running it

Install the benchmark extra:

```bash
pip install 'guard-bands-reference[bench]'
```

Free wiring check — a scripted stub "model", no API key, no cost:

```bash
python scripts/run_agentdojo_benchmark.py --model stub --suite banking \
  --user-task user_task_0 --injection-task injection_task_0 \
  --defense both --attack direct
```

Real run — prints a cost estimate and asks before spending API credits:

```bash
python scripts/run_agentdojo_benchmark.py --model claude-sonnet-5 \
  --suite banking --defense both --attack important_instructions
```

Defenses:

- `baseline` — no Guard Bands (undefended reference, AgentDojo's default pipeline)
- `signed` — cryptographic spotlighting: tool outputs are wrapped in signed
  Guard Band markers and the system message instructs the model to treat
  guard-banded text as inert data. Unlike plain delimiter spotlighting, the
  boundary cannot be forged by injected content.
- `gated` — `signed` plus a provenance gate that blocks tool calls whose
  arguments echo guard-banded (untrusted) content
- `both` — runs `baseline` and `gated` for a with/without comparison

`attack-success-rate` is the fraction of cases where the injection achieved its
goal (lower is better); `utility` is the fraction of legitimate user tasks the
agent still completed under attack (higher is better).

The defense mechanisms are unit-tested independently of any model in
`tests/test_agentdojo_integration.py` (the signer wraps and records tool
outputs; the gate blocks tool calls carrying guard-banded content).

## Note on results with current frontier models

Guard Bands is a provenance and integrity control, not a jailbreak classifier,
and this harness makes that distinction measurable. On small baseline slices of
the `banking` suite, current Anthropic models (`claude-sonnet-5`,
`claude-haiku-4-5`) already resisted the suite's classic injection attacks
(`important_instructions`, `tool_knowledge`) at **0% attack success** with no
defense at all — so there is no behavioral attack-rate reduction for a boundary
control to demonstrate on that configuration. The `gated` pipeline was verified
to run end to end and to preserve utility on the same slices.

That is expected and consistent with the project's scope: on a model that
already ignores injected instructions, cryptographic spotlighting is redundant
*for that specific job*. Guard Bands' value is the guarantee the model cannot
provide — deterministic, auditable provenance and a fail-closed authority gate —
which matters exactly where model robustness does not hold: weaker or fine-tuned
models, novel or adaptive attacks, and the two-channel split where a compromised
control plane must not be able to forge data-plane provenance (see
[`DUAL_CHANNEL.md`](DUAL_CHANNEL.md)). To quantify attack reduction, point the
harness at a configuration where the baseline is actually vulnerable.
