"""Pluggable content source providers for TCD-Swipekit."""

from tcd_swipekit.sources.base import BaseSource
from tcd_swipekit.sources.github import GitHubSource
from tcd_swipekit.sources.manual import ManualDeckSource
from tcd_swipekit.sources.website import WebsiteSource

__all__ = ["BaseSource", "GitHubSource", "WebsiteSource", "ManualDeckSource"]
