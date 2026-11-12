"""Backend registry. A backend turns (view, references, seed, params) into one image."""
from __future__ import annotations


def get_backend(name: str, **kwargs):
    if name == "test_pattern":
        from .test_pattern import TestPatternBackend
        return TestPatternBackend(**kwargs)
    if name == "photomaker_v2":
        from .photomaker_v2 import PhotoMakerV2Backend
        return PhotoMakerV2Backend(**kwargs)
    if name == "sdcpp":
        from .sdcpp import SdCppBackend
        return SdCppBackend(**kwargs)
    raise ValueError(f"backend inconnu: {name}")
