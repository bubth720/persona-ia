from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GenerationResult:
    path: Path
    engine: str
    model: str
    model_version: str
    licence: str
    is_generation: bool            # False => layout/test only, can never satisfy Gate D/E
    seed: int
    prompt: str
    negative_prompt: str
    params: dict = field(default_factory=dict)
    duration_s: float = 0.0
    peak_vram_mb: float | None = None
    hardware: str = ""
    warnings: list[str] = field(default_factory=list)


class Backend:
    name = "base"
    is_generation = False

    def describe(self) -> dict:
        return {"name": self.name, "is_generation": self.is_generation}

    def generate(self, *, kind: str, view: str, references: list[Path], seed: int, params: dict,
                 out_path: Path) -> GenerationResult:
        raise NotImplementedError

    def close(self) -> None:
        pass
