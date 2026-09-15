"""Structured recovery report for a conversion attempt."""
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class RecoveryReport:
    original_path: Path
    original_type: str = "unknown"
    detected_corruption: List[str] = field(default_factory=list)
    attempted_strategies: List[str] = field(default_factory=list)
    successful_strategy: Optional[str] = None
    removed_components: List[str] = field(default_factory=list)
    repaired_components: List[str] = field(default_factory=list)
    slides_recovered: int = 0
    slides_lost: int = 0
    engine_used: Optional[str] = None
    final_pdf_path: Optional[Path] = None
    final_pdf_size: int = 0
    reconstructed: bool = False
    font_substitutions: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "original_path": str(self.original_path),
            "original_type": self.original_type,
            "detected_corruption": self.detected_corruption,
            "attempted_strategies": self.attempted_strategies,
            "successful_strategy": self.successful_strategy,
            "removed_components": self.removed_components,
            "repaired_components": self.repaired_components,
            "slides_recovered": self.slides_recovered,
            "slides_lost": self.slides_lost,
            "engine_used": self.engine_used,
            "final_pdf_path": str(self.final_pdf_path) if self.final_pdf_path else None,
            "final_pdf_size": self.final_pdf_size,
            "reconstructed": self.reconstructed,
            "font_substitutions": self.font_substitutions,
            "errors": self.errors,
            "warnings": self.warnings,
        }
