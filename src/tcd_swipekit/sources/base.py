"""Abstract base class for pluggable content sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from tcd_swipekit.models import Language, SlideItem


class BaseSource(ABC):
    """Contract for any content source (GitHub, Websites, Product Hunt, etc.)."""

    def __init__(self, cache_dir: Path, language: Language = Language.EN) -> None:
        self.cache_dir = cache_dir
        self.language = language
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def fetch_items(self, limit: int = 6, **kwargs: object) -> list[SlideItem]:
        """Fetch a list of unified SlideItem objects from this source."""
