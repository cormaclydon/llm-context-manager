# context_manager/__init__.py
"""
LLM Context Manager - Package codebases for AI context.

A developer tool that intelligently packages codebases into optimal
context windows for different LLMs like Claude, GPT-4, Qwen, and local models.
"""

__version__ = "0.1.0"

from .analyzer import CodebaseAnalyzer
from .models import LLMProfile, create_custom_profile
from .packager import ContextPackager, IncrementalPackager
from .tokenizers import TokenCounter, get_token_counter
from .watcher import (
    CodebaseWatcher,
    start_watch,
    watch_blocking,
    WatchManager,
    is_watchdog_available,
)

__all__ = [
    # Version
    "__version__",
    # Analyzer
    "CodebaseAnalyzer",
    # Models
    "LLMProfile",
    "create_custom_profile",
    # Packager
    "ContextPackager",
    "IncrementalPackager",
    # Tokenizers
    "TokenCounter",
    "get_token_counter",
    # Watcher
    "CodebaseWatcher",
    "start_watch",
    "watch_blocking",
    "WatchManager",
    "is_watchdog_available",
]


def pack(
    directory: str = ".",
    profile: str = "claude-sonnet",
    output: str = None,
    focus_files: list = None,
) -> str:
    """
    Convenience function to pack a codebase in one call.

    Args:
        directory: Path to codebase (default: current directory)
        profile: LLM profile name (default: claude-sonnet)
        output: Output file path (optional)
        focus_files: List of files to prioritize (optional)

    Returns:
        Packaged context as string

    Example:
        >>> from context_manager import pack
        >>> context = pack("./my-project", profile="gpt4")
        >>> print(f"Generated {len(context)} characters")
    """
    llm_profile = LLMProfile.load(profile)
    analyzer = CodebaseAnalyzer(directory)
    analysis = analyzer.analyze()
    packager = ContextPackager(llm_profile)
    return packager.package(analysis, output, focus_files)
