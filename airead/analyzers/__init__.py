"""Static analyzers. Each module exposes ``analyze(fn) -> DimensionScore``."""

from airead.analyzers import naming, srp, side_effects, local_reasoning

ANALYZERS = [naming, srp, side_effects, local_reasoning]

__all__ = ["ANALYZERS", "naming", "srp", "side_effects", "local_reasoning"]
