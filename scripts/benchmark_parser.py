import sys
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from guardbands import GuardBandCrypto, extract_guard_band_blocks


def bench(label: str, samples: list[float]) -> None:
    print(
        f"{label}: min={min(samples):.6f}s "
        f"median={statistics.median(samples):.6f}s max={max(samples):.6f}s"
    )


def time_call(fn, iterations: int = 100) -> list[float]:
    samples = []
    for _ in range(iterations):
        started = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - started)
    return samples


def main() -> None:
    crypto = GuardBandCrypto(b"benchmark-secret")
    context = {"request_id": "bench-001", "policy_path": "rag.read_only"}
    block = crypto.wrap_content("Document body " * 200, context)
    prompt = "\n\n".join([block] * 10)
    malformed_prompt = ("⟪INERT:START:v:1:r:abc:iat:1:exp:2⟫ incomplete\n" * 500) + block

    bench("wrap 2.8 KB content", time_call(lambda: crypto.wrap_content("x" * 2800, context)))
    bench("verify 2.8 KB content", time_call(lambda: crypto.extract_and_verify(block, context)))
    bench("extract 10 blocks", time_call(lambda: extract_guard_band_blocks(prompt)))
    bench("extract after malformed markers", time_call(lambda: extract_guard_band_blocks(malformed_prompt)))


if __name__ == "__main__":
    main()
