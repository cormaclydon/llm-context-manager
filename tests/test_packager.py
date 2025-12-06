# tests/test_packager.py
"""Tests for the ContextPackager module."""

import pytest
import tempfile
from pathlib import Path

from context_manager.analyzer import CodebaseAnalyzer
from context_manager.packager import ContextPackager
from context_manager.models import LLMProfile


class TestContextPackager:
    """Test cases for ContextPackager."""

    @pytest.fixture
    def sample_analysis(self, tmp_path):
        """Create a sample codebase and analysis."""
        (tmp_path / "main.py").write_text("def main():\n    print('Hello')\n\nif __name__ == '__main__':\n    main()\n")
        (tmp_path / "utils.py").write_text("def helper(x):\n    return x * 2\n")
        (tmp_path / "README.md").write_text("# Sample Project\n\nA sample project.\n")

        analyzer = CodebaseAnalyzer(str(tmp_path))
        return analyzer.analyze()

    def test_xml_output_format(self, sample_analysis):
        """Test XML output format generation."""
        profile = LLMProfile.load('claude-sonnet')
        packager = ContextPackager(profile)

        context = packager.package(sample_analysis)

        assert context.startswith('<?xml version="1.0"')
        assert '<codebase>' in context
        assert '</codebase>' in context
        assert '<files>' in context
        assert '<file path=' in context
        assert 'CDATA' in context

    def test_markdown_output_format(self, sample_analysis):
        """Test Markdown output format generation."""
        profile = LLMProfile.load('qwen')  # Uses markdown
        packager = ContextPackager(profile)

        context = packager.package(sample_analysis)

        assert '# Codebase Context' in context
        assert '## Files' in context
        assert '```python' in context or '```py' in context

    def test_plain_output_format(self, sample_analysis):
        """Test plain text output format generation."""
        profile = LLMProfile.load('local-small')  # Uses plain
        packager = ContextPackager(profile)

        context = packager.package(sample_analysis)

        assert 'CODEBASE CONTEXT' in context
        assert 'FILE STRUCTURE' in context
        assert 'FILES' in context

    def test_respects_token_limit(self, tmp_path):
        """Test that packager respects token limits."""
        # Create a file with lots of content
        large_content = "x = 1\n" * 10000
        (tmp_path / "large.py").write_text(large_content)
        (tmp_path / "main.py").write_text("print('hello')")

        analyzer = CodebaseAnalyzer(str(tmp_path))
        analysis = analyzer.analyze()

        # Use a small profile
        profile = LLMProfile.load('local-small')  # 4K tokens
        packager = ContextPackager(profile)

        context = packager.package(analysis)
        stats = packager.get_stats(context)

        # Should be within optimal tokens
        assert stats['token_count'] <= profile.optimal_tokens

    def test_file_tree_inclusion(self, sample_analysis):
        """Test that file tree is included when configured."""
        profile = LLMProfile.load('claude-sonnet')
        assert profile.include_tree is True

        packager = ContextPackager(profile)
        context = packager.package(sample_analysis)

        assert '<structure>' in context or 'File Structure' in context

    def test_file_tree_exclusion(self, sample_analysis):
        """Test that file tree can be excluded."""
        profile = LLMProfile.load('claude-sonnet')
        profile.include_tree = False

        packager = ContextPackager(profile)
        context = packager.package(sample_analysis)

        assert '<structure>' not in context

    def test_focus_files(self, tmp_path):
        """Test focusing on specific files."""
        (tmp_path / "main.py").write_text("main code")
        (tmp_path / "utils.py").write_text("util code")
        (tmp_path / "other.py").write_text("other code")

        analyzer = CodebaseAnalyzer(str(tmp_path))
        analysis = analyzer.analyze()

        profile = LLMProfile.load('claude-sonnet')
        packager = ContextPackager(profile)

        context = packager.package(analysis, focus_files=['utils.py'])

        # utils.py should appear first (boosted priority)
        # This is a simple check - more detailed would parse the output
        assert 'utils.py' in context

    def test_stats_generation(self, sample_analysis):
        """Test statistics generation."""
        profile = LLMProfile.load('claude-sonnet')
        packager = ContextPackager(profile)

        context = packager.package(sample_analysis)
        stats = packager.get_stats(context)

        assert 'token_count' in stats
        assert 'max_tokens' in stats
        assert 'optimal_tokens' in stats
        assert 'utilization' in stats
        assert 'character_count' in stats
        assert 'line_count' in stats

        assert stats['token_count'] > 0
        assert 0 <= stats['utilization'] <= 100

    def test_output_to_file(self, sample_analysis, tmp_path):
        """Test saving output to file."""
        output_path = tmp_path / "output.xml"

        profile = LLMProfile.load('claude-sonnet')
        packager = ContextPackager(profile)

        context = packager.package(sample_analysis, str(output_path))

        assert output_path.exists()
        saved_content = output_path.read_text()
        assert saved_content == context


class TestIncrementalPackager:
    """Test cases for IncrementalPackager."""

    def test_incremental_caching(self, tmp_path):
        """Test that incremental packager caches content."""
        from context_manager.packager import IncrementalPackager

        (tmp_path / "main.py").write_text("print('v1')")

        analyzer = CodebaseAnalyzer(str(tmp_path))
        analysis = analyzer.analyze()

        profile = LLMProfile.load('claude-sonnet')
        packager = IncrementalPackager(profile)

        # First pack
        context1 = packager.package_incremental(analysis, [])
        assert 'v1' in context1

        # Modify file
        (tmp_path / "main.py").write_text("print('v2')")
        analysis = analyzer.analyze()

        # Pack with changed files
        context2 = packager.package_incremental(analysis, ['main.py'])
        assert 'v2' in context2

    def test_cache_clear(self, tmp_path):
        """Test cache clearing."""
        from context_manager.packager import IncrementalPackager

        (tmp_path / "main.py").write_text("content")

        analyzer = CodebaseAnalyzer(str(tmp_path))
        analysis = analyzer.analyze()

        profile = LLMProfile.load('claude-sonnet')
        packager = IncrementalPackager(profile)

        packager.package_incremental(analysis, [])
        assert len(packager._cache) > 0

        packager.clear_cache()
        assert len(packager._cache) == 0
