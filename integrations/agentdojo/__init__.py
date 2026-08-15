"""Guard Bands defense for the AgentDojo prompt-injection benchmark.

Optional integration — requires `pip install 'guard-bands-reference[bench]'` (installs
agentdojo). Not imported by the core package.
"""

from integrations.agentdojo.guard_bands_defense import (
    GUARD_BAND_SYSTEM_SUFFIX,
    GuardBandProvenanceGate,
    GuardBandToolOutputSigner,
    build_guard_bands_pipeline,
)

__all__ = [
    "GUARD_BAND_SYSTEM_SUFFIX",
    "GuardBandProvenanceGate",
    "GuardBandToolOutputSigner",
    "build_guard_bands_pipeline",
]
