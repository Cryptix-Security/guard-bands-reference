"""Run the AgentDojo prompt-injection benchmark with the Guard Bands defense.

Requires the benchmark extra:  pip install 'guard-bands-reference[bench]'

Examples:
    # Free end-to-end wiring check with a scripted stub model (no API key, no cost)
    python scripts/run_agentdojo_benchmark.py --model stub --suite banking \\
        --user-task user_task_0 --injection-task injection_task_0

    # Real run (spends API credits) — prints a cost estimate and asks to confirm
    python scripts/run_agentdojo_benchmark.py --model claude-3-5-sonnet-20241022 \\
        --suite banking --defense both

Defenses:
    baseline  — no Guard Bands (undefended reference)
    signed    — cryptographic spotlighting only
    gated     — spotlighting + provenance gate
    both      — run baseline and gated, for a with/without comparison
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agentdojo.agent_pipeline import (  # noqa: E402
    AgentPipeline,
    BasePipelineElement,
    PipelineConfig,
)
from agentdojo.attacks.attack_registry import load_attack  # noqa: E402
from agentdojo.benchmark import benchmark_suite_with_injections  # noqa: E402
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionsRuntime  # noqa: E402
from agentdojo.task_suite.load_suites import get_suite  # noqa: E402

from integrations.agentdojo import build_guard_bands_pipeline  # noqa: E402

BENCHMARK_VERSION = "v1.2.1"
# Rough per-case cost anchors (USD). A "case" is one user task under one
# injection task and runs a multi-turn tool-calling agent. Deliberately
# conservative; real cost depends on tool-call depth.
COST_PER_CASE_USD = {
    "claude-sonnet-5": 0.15,
    "claude-opus-4-8": 0.60,
    "claude-haiku-4-5": 0.03,
    "claude-haiku-4-5-20251001": 0.03,
}


class StubLLM(BasePipelineElement):
    """A scripted, zero-cost 'model' for validating pipeline wiring.

    It never calls a real API. It emits one assistant message with no tool
    calls, so the tool loop terminates immediately. Enough to prove the Guard
    Bands elements are composed and invoked correctly end to end.
    """

    name = "stub"

    def query(self, query, runtime, env=EmptyEnv(), messages=(), extra_args={}):
        from agentdojo.types import ChatAssistantMessage, text_content_block_from_string

        reply = ChatAssistantMessage(
            role="assistant",
            content=[text_content_block_from_string("stub: no action taken")],
            tool_calls=[],
        )
        return query, runtime, env, [*messages, reply], extra_args


def _config(llm, defense: str | None) -> PipelineConfig:
    return PipelineConfig(
        llm=llm, model_id=None, defense=defense,
        system_message_name="default", system_message=None,
    )


def build_llm(model: str) -> BasePipelineElement:
    if model == "stub":
        return StubLLM()
    if "claude" in model:
        # AgentDojo's ModelsEnum only knows retired Claude ids. Build the
        # Anthropic client directly for current models and register the id so
        # the attack resolves it to the "Claude" display name.
        import anthropic
        from agentdojo.agent_pipeline import AnthropicLLM
        from agentdojo.attacks.base_attacks import MODEL_NAMES

        MODEL_NAMES.setdefault(model, "Claude")
        # Current models reject an explicit temperature; pass None to omit it.
        llm = AnthropicLLM(anthropic.Anthropic(), model, temperature=None, max_tokens=4096)
        llm.name = model
        return llm
    # Registered non-Claude models: extract the LLM from a default pipeline.
    return AgentPipeline.from_config(_config(model, None)).elements[2]


def make_pipeline(model: str, defense: str) -> AgentPipeline:
    llm = build_llm(model)  # element carries .name = model (or "stub")
    if defense == "baseline":
        pipeline = AgentPipeline.from_config(_config(llm, None))
        if pipeline.name is None:
            pipeline.name = model
        return pipeline
    return build_guard_bands_pipeline(llm, gated=(defense == "gated"), name=model)


def estimate_cost(model: str, n_cases: int) -> float | None:
    per = COST_PER_CASE_USD.get(model)
    return None if per is None else per * n_cases


def confirm(prompt: str) -> bool:
    try:
        return input(f"{prompt} [y/N] ").strip().lower() in {"y", "yes"}
    except EOFError:
        return False


def run_one(model: str, defense: str, suite, attack_name: str,
            user_tasks: Sequence[str] | None, injection_tasks: Sequence[str] | None,
            logdir: Path | None) -> None:
    from agentdojo.logging import OutputLogger

    pipeline = make_pipeline(model, defense)
    attack = load_attack(attack_name, suite, pipeline)
    with OutputLogger(str(logdir) if logdir else None, live=None):
        results = benchmark_suite_with_injections(
            pipeline, suite, attack, logdir=logdir, force_rerun=True,
            user_tasks=user_tasks, injection_tasks=injection_tasks,
            benchmark_version=BENCHMARK_VERSION, verbose=False,
        )
    utility = results["utility_results"]
    security = results["security_results"]  # True == injection SUCCEEDED (bad)
    attack_success = sum(1 for v in security.values() if v) / (len(security) or 1)
    task_utility = sum(1 for v in utility.values() if v) / (len(utility) or 1)
    print(f"\n[{defense}]  cases={len(security)}  "
          f"attack-success-rate={attack_success:.1%}  "
          f"utility(with attack)={task_utility:.1%}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default="stub")
    p.add_argument("--suite", default="banking", choices=["workspace", "banking", "travel", "slack"])
    p.add_argument("--attack", default="important_instructions")
    p.add_argument("--defense", default="both", choices=["baseline", "signed", "gated", "both"])
    p.add_argument("--user-task", action="append", dest="user_tasks")
    p.add_argument("--injection-task", action="append", dest="injection_tasks")
    p.add_argument("--logdir", default=None)
    p.add_argument("--yes", action="store_true", help="skip the cost confirmation")
    args = p.parse_args()

    suite = get_suite(BENCHMARK_VERSION, args.suite)
    n_user = len(args.user_tasks) if args.user_tasks else len(suite.user_tasks)
    n_inj = len(args.injection_tasks) if args.injection_tasks else len(suite.injection_tasks)
    defenses = ["baseline", "gated"] if args.defense == "both" else [args.defense]
    n_cases = n_user * n_inj * len(defenses)

    if args.model != "stub":
        est = estimate_cost(args.model, n_cases)
        est_str = f"~${est:.2f}" if est is not None else "unknown"
        print(f"About to run {n_cases} live cases on {args.model} "
              f"({n_user} user × {n_inj} injection × {len(defenses)} defense). "
              f"Estimated cost: {est_str}.")
        if not args.yes and not confirm("Proceed and spend API credits?"):
            print("Aborted — no credits spent.")
            return 1

    import tempfile
    logdir = Path(args.logdir) if args.logdir else Path(tempfile.mkdtemp(prefix="agentdojo-runs-"))
    for defense in defenses:
        run_one(args.model, defense, suite, args.attack,
                args.user_tasks, args.injection_tasks, logdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
