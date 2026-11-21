import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

ESTIMATION_METHOD = "approx_chars_per_token"
APPROX_CHARS_PER_TOKEN = 4
USD_PER_MTOK_DIVISOR = 1_000_000


def estimate_tokens_for_value(value: Any) -> int:
    serialized = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return max(1, math.ceil(len(serialized) / APPROX_CHARS_PER_TOKEN))


def calculate_cost_usd(
    input_tokens: int,
    output_tokens: int,
    input_usd_per_mtok: float,
    output_usd_per_mtok: float,
) -> dict[str, float]:
    input_cost = (input_tokens / USD_PER_MTOK_DIVISOR) * input_usd_per_mtok
    output_cost = (output_tokens / USD_PER_MTOK_DIVISOR) * output_usd_per_mtok
    total_cost = input_cost + output_cost
    return {
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "total_cost_usd": round(total_cost, 6),
    }


def estimate_chat_request_cost(
    *,
    model: str,
    system: str,
    messages: Sequence[Mapping[str, Any]],
    tools: Sequence[Mapping[str, Any]],
    output_token_budget: int,
    input_usd_per_mtok: float,
    output_usd_per_mtok: float,
    threshold_usd: float,
    guard_enabled: bool,
) -> dict[str, Any]:
    input_tokens = estimate_tokens_for_value(
        {
            "system": system,
            "messages": messages,
            "tools": tools,
        }
    )
    costs = calculate_cost_usd(
        input_tokens=input_tokens,
        output_tokens=output_token_budget,
        input_usd_per_mtok=input_usd_per_mtok,
        output_usd_per_mtok=output_usd_per_mtok,
    )
    threshold_exceeded = guard_enabled and costs["total_cost_usd"] >= threshold_usd
    return {
        "model": model,
        "method": ESTIMATION_METHOD,
        "currency": "USD",
        "input_tokens_estimate": input_tokens,
        "output_tokens_budget": output_token_budget,
        "estimated_input_cost_usd": costs["input_cost_usd"],
        "estimated_output_cost_usd": costs["output_cost_usd"],
        "estimated_total_cost_usd": costs["total_cost_usd"],
        "threshold_usd": threshold_usd,
        "threshold_exceeded": threshold_exceeded,
        "requires_confirmation": threshold_exceeded,
        "pricing": {
            "input_usd_per_mtok": input_usd_per_mtok,
            "output_usd_per_mtok": output_usd_per_mtok,
        },
    }


def actual_chat_cost(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    input_usd_per_mtok: float,
    output_usd_per_mtok: float,
) -> dict[str, Any]:
    costs = calculate_cost_usd(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_usd_per_mtok=input_usd_per_mtok,
        output_usd_per_mtok=output_usd_per_mtok,
    )
    return {
        "model": model,
        "currency": "USD",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost_usd": costs["input_cost_usd"],
        "output_cost_usd": costs["output_cost_usd"],
        "total_cost_usd": costs["total_cost_usd"],
        "pricing": {
            "input_usd_per_mtok": input_usd_per_mtok,
            "output_usd_per_mtok": output_usd_per_mtok,
        },
    }
