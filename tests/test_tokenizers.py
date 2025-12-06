# tests/test_tokenizers.py
"""Tests for the TokenCounter module."""

import pytest
from pathlib import Path

from context_manager.tokenizers import TokenCounter, get_token_counter


class TestTokenCounter:
    """Test cases for TokenCounter."""

    def test_count_empty_string(self):
        """Test counting empty string."""
        counter = TokenCounter('cl100k_base')
        assert counter.count('') == 0

    def test_count_simple_text(self):
        """Test counting simple text."""
        counter = TokenCounter('cl100k_base')
        count = counter.count('Hello, world!')

        # Should be a small positive number
        assert count > 0
        assert count < 10

    def test_count_code(self):
        """Test counting code content."""
        counter = TokenCounter('cl100k_base')
        code = """
def hello_world():
    print("Hello, World!")
    return True
"""
        count = counter.count(code)
        assert count > 0

    def test_different_tokenizers(self):
        """Test different tokenizer types."""
        text = "The quick brown fox jumps over the lazy dog."

        counter_cl100k = TokenCounter('cl100k_base')
        counter_gpt2 = TokenCounter('gpt2')

        count_cl100k = counter_cl100k.count(text)
        count_gpt2 = counter_gpt2.count(text)

        # Both should produce tokens
        assert count_cl100k > 0
        assert count_gpt2 > 0

        # May have slightly different counts
        # Just verify they're in same ballpark
        assert abs(count_cl100k - count_gpt2) < count_cl100k

    def test_count_file(self, tmp_path):
        """Test counting tokens in a file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('Hello')\n" * 10)

        counter = TokenCounter('cl100k_base')
        count = counter.count_file(str(test_file))

        assert count > 0

    def test_count_missing_file(self):
        """Test counting tokens in non-existent file."""
        counter = TokenCounter('cl100k_base')
        count = counter.count_file('/nonexistent/file.txt')

        assert count == 0

    def test_count_files_batch(self, tmp_path):
        """Test counting tokens in multiple files."""
        (tmp_path / "a.py").write_text("print('a')")
        (tmp_path / "b.py").write_text("print('b')")

        counter = TokenCounter('cl100k_base')
        counts = counter.count_files([
            str(tmp_path / "a.py"),
            str(tmp_path / "b.py"),
        ])

        assert len(counts) == 2
        assert all(c > 0 for c in counts.values())

    def test_truncate_to_tokens(self):
        """Test truncating text to token limit."""
        counter = TokenCounter('cl100k_base')
        long_text = "word " * 1000

        truncated = counter.truncate_to_tokens(long_text, 50)

        # Truncated should be shorter
        assert len(truncated) < len(long_text)
        # And should be around 50 tokens
        assert counter.count(truncated) <= 50

    def test_truncate_short_text(self):
        """Test truncating text that's already short enough."""
        counter = TokenCounter('cl100k_base')
        short_text = "Hello"

        truncated = counter.truncate_to_tokens(short_text, 1000)

        # Should be unchanged
        assert truncated == short_text

    def test_split_into_chunks(self):
        """Test splitting text into chunks."""
        counter = TokenCounter('cl100k_base')
        long_text = "word " * 500

        chunks = counter.split_into_chunks(long_text, 100)

        assert len(chunks) > 1
        # Each chunk should be around 100 tokens
        for chunk in chunks:
            assert counter.count(chunk) <= 110  # Allow some overflow

    def test_split_short_text(self):
        """Test splitting short text returns single chunk."""
        counter = TokenCounter('cl100k_base')
        short_text = "Hello world"

        chunks = counter.split_into_chunks(short_text, 1000)

        assert len(chunks) == 1
        assert chunks[0] == short_text

    def test_get_stats(self):
        """Test getting text statistics."""
        counter = TokenCounter('cl100k_base')
        text = "Hello\nWorld\nTest"

        stats = counter.get_stats(text)

        assert 'tokens' in stats
        assert 'characters' in stats
        assert 'lines' in stats
        assert 'words' in stats
        assert 'tokenizer' in stats

        assert stats['lines'] == 3
        assert stats['words'] == 3
        assert stats['characters'] == len(text)

    def test_tiktoken_available_check(self):
        """Test tiktoken availability check."""
        # This should return True if tiktoken is installed
        available = TokenCounter.is_tiktoken_available()
        assert isinstance(available, bool)


class TestTokenCounterAdditional:
    """Additional test cases for TokenCounter."""

    def test_p50k_base_tokenizer(self):
        """Test p50k_base tokenizer."""
        counter = TokenCounter('p50k_base')
        count = counter.count('Hello, world!')
        assert count > 0

    def test_unknown_tokenizer_defaults(self):
        """Test that unknown tokenizer defaults to cl100k_base."""
        counter = TokenCounter('unknown_tokenizer')
        count = counter.count('Hello, world!')
        assert count > 0

    def test_claude_tokenizer(self):
        """Test Claude tokenizer type."""
        counter = TokenCounter('claude')
        count = counter.count('Hello, world!')
        assert count > 0

    def test_gpt4_tokenizer(self):
        """Test GPT-4 tokenizer type."""
        counter = TokenCounter('gpt4')
        count = counter.count('Hello, world!')
        assert count > 0

    def test_split_with_overlap(self):
        """Test splitting text with overlap."""
        counter = TokenCounter('cl100k_base')
        # Create text that will definitely need multiple chunks
        long_text = "word " * 500

        chunks = counter.split_into_chunks(long_text, 100, overlap=20)

        assert len(chunks) > 1
        # With overlap, chunks should share some content

    def test_estimate_tokens_with_code(self):
        """Test token estimation with high code density."""
        counter = TokenCounter('gpt2')
        # Create code-like content with many code indicators
        code = """
def function() {
    if (true) {
        console.log("test");
    }
    return [1, 2, 3];
}
class MyClass {
    constructor() {}
}
""" * 10

        # This should trigger the code density adjustment
        count = counter.count(code)
        assert count > 0

    def test_count_file_with_binary(self, tmp_path):
        """Test counting tokens in a binary file returns 0."""
        binary_file = tmp_path / "binary.bin"
        binary_file.write_bytes(b'\x00\x01\x02\x03\xff\xfe')

        counter = TokenCounter('cl100k_base')
        count = counter.count_file(str(binary_file))

        # Should return 0 for unreadable file
        assert count == 0

    def test_get_stats_empty_text(self):
        """Test getting stats for empty text."""
        counter = TokenCounter('cl100k_base')
        stats = counter.get_stats('')

        assert stats['tokens'] == 0
        assert stats['characters'] == 0
        assert stats['lines'] == 1
        assert stats['words'] == 0

    def test_chars_per_token_values(self):
        """Test that CHARS_PER_TOKEN has expected values."""
        assert TokenCounter.CHARS_PER_TOKEN['claude'] == 3.5
        assert TokenCounter.CHARS_PER_TOKEN['cl100k_base'] == 4.0
        assert TokenCounter.CHARS_PER_TOKEN['gpt2'] == 4.5
        assert TokenCounter.CHARS_PER_TOKEN['default'] == 4.0

    def test_truncate_with_fallback(self):
        """Test truncation uses correct fallback logic."""
        counter = TokenCounter('gpt2')
        long_text = "word " * 1000

        truncated = counter.truncate_to_tokens(long_text, 50)

        assert len(truncated) < len(long_text)


class TestGetTokenCounter:
    """Test cases for get_token_counter helper."""

    def test_with_string(self):
        """Test creating counter from string."""
        counter = get_token_counter('gpt2')
        assert counter.tokenizer_type == 'gpt2'

    def test_with_profile(self):
        """Test creating counter from profile."""
        from context_manager.models import LLMProfile

        profile = LLMProfile.load('claude-sonnet')
        counter = get_token_counter(profile)

        assert counter.tokenizer_type == profile.tokenizer_type

    def test_with_different_profiles(self):
        """Test with various profile types."""
        from context_manager.models import LLMProfile

        for profile_name in ['gpt4', 'qwen', 'local-small']:
            profile = LLMProfile.load(profile_name)
            counter = get_token_counter(profile)
            assert counter.tokenizer_type == profile.tokenizer_type
