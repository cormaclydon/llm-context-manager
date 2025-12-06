# context_manager/tokenizers.py
"""
Token counting utilities for different LLM types.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import re

# Try to import tiktoken, fall back to estimation if not available
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


class TokenCounter:
    """
    Count tokens for different LLM types.

    Supports:
    - claude: Claude models (uses cl100k_base as approximation)
    - cl100k_base: OpenAI models (GPT-4, etc.)
    - gpt2: Older OpenAI models and many open-source models
    - p50k_base: GPT-3.5 and Codex models
    """

    # Approximate characters per token for different tokenizers
    # Used as fallback when tiktoken is not available
    CHARS_PER_TOKEN = {
        'claude': 3.5,
        'cl100k_base': 4.0,
        'gpt4': 4.0,
        'gpt2': 4.5,
        'p50k_base': 4.0,
        'default': 4.0
    }

    def __init__(self, tokenizer_type: str = 'cl100k_base'):
        """
        Initialize token counter.

        Args:
            tokenizer_type: Type of tokenizer to use
        """
        self.tokenizer_type = tokenizer_type
        self.encoder = None

        if TIKTOKEN_AVAILABLE:
            try:
                if tokenizer_type in ['claude', 'gpt4', 'cl100k_base']:
                    self.encoder = tiktoken.get_encoding('cl100k_base')
                elif tokenizer_type == 'gpt2':
                    self.encoder = tiktoken.get_encoding('gpt2')
                elif tokenizer_type == 'p50k_base':
                    self.encoder = tiktoken.get_encoding('p50k_base')
                else:
                    # Default to cl100k_base for unknown types
                    self.encoder = tiktoken.get_encoding('cl100k_base')
            except Exception:
                self.encoder = None

    def count(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception:
                pass

        # Fallback to estimation
        return self._estimate_tokens(text)

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count based on character count.
        Uses heuristics when tiktoken is not available.
        """
        # Get chars per token for this tokenizer type
        chars_per_token = self.CHARS_PER_TOKEN.get(
            self.tokenizer_type,
            self.CHARS_PER_TOKEN['default']
        )

        # Adjust for code content (tends to have more tokens)
        # Code has more special characters and shorter words
        code_indicators = ['{', '}', '(', ')', '[', ']', ';', 'def ', 'function ', 'class ']
        code_score = sum(text.count(ind) for ind in code_indicators)

        if code_score > len(text) / 100:  # High code density
            chars_per_token *= 0.85  # Code tends to have more tokens

        return int(len(text) / chars_per_token)

    def count_file(self, file_path: str) -> int:
        """
        Count tokens in a file.

        Args:
            file_path: Path to file

        Returns:
            Number of tokens, or 0 if file cannot be read
        """
        try:
            content = Path(file_path).read_text(encoding='utf-8')
            return self.count(content)
        except (UnicodeDecodeError, PermissionError, OSError):
            return 0

    def count_files(self, file_paths: list) -> Dict[str, int]:
        """
        Count tokens for multiple files.

        Args:
            file_paths: List of file paths

        Returns:
            Dictionary mapping file paths to token counts
        """
        return {fp: self.count_file(fp) for fp in file_paths}

    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to approximately max_tokens.

        Args:
            text: Text to truncate
            max_tokens: Maximum number of tokens

        Returns:
            Truncated text
        """
        if self.count(text) <= max_tokens:
            return text

        if self.encoder:
            try:
                tokens = self.encoder.encode(text)
                truncated_tokens = tokens[:max_tokens]
                return self.encoder.decode(truncated_tokens)
            except Exception:
                pass

        # Fallback: estimate based on character count
        chars_per_token = self.CHARS_PER_TOKEN.get(
            self.tokenizer_type,
            self.CHARS_PER_TOKEN['default']
        )
        max_chars = int(max_tokens * chars_per_token)
        return text[:max_chars]

    def split_into_chunks(self, text: str, chunk_size: int, overlap: int = 0) -> list:
        """
        Split text into chunks of approximately chunk_size tokens.

        Args:
            text: Text to split
            chunk_size: Target size of each chunk in tokens
            overlap: Number of tokens to overlap between chunks

        Returns:
            List of text chunks
        """
        if self.count(text) <= chunk_size:
            return [text]

        chunks = []
        if self.encoder:
            try:
                tokens = self.encoder.encode(text)
                start = 0
                while start < len(tokens):
                    end = start + chunk_size
                    chunk_tokens = tokens[start:end]
                    chunks.append(self.encoder.decode(chunk_tokens))
                    start = end - overlap if overlap > 0 else end
                return chunks
            except Exception:
                pass

        # Fallback: split by lines to approximate chunks
        lines = text.split('\n')
        current_chunk = []
        current_tokens = 0

        for line in lines:
            line_tokens = self.count(line + '\n')
            if current_tokens + line_tokens > chunk_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                # Handle overlap by keeping some lines
                if overlap > 0:
                    overlap_lines = []
                    overlap_tokens = 0
                    for prev_line in reversed(current_chunk):
                        prev_tokens = self.count(prev_line + '\n')
                        if overlap_tokens + prev_tokens <= overlap:
                            overlap_lines.insert(0, prev_line)
                            overlap_tokens += prev_tokens
                        else:
                            break
                    current_chunk = overlap_lines
                    current_tokens = overlap_tokens
                else:
                    current_chunk = []
                    current_tokens = 0

            current_chunk.append(line)
            current_tokens += line_tokens

        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

    def get_stats(self, text: str) -> Dict[str, Any]:
        """
        Get detailed statistics about text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with token count, character count, etc.
        """
        token_count = self.count(text)
        char_count = len(text)
        line_count = text.count('\n') + 1
        word_count = len(text.split())

        return {
            'tokens': token_count,
            'characters': char_count,
            'lines': line_count,
            'words': word_count,
            'avg_tokens_per_line': token_count / line_count if line_count > 0 else 0,
            'chars_per_token': char_count / token_count if token_count > 0 else 0,
            'tokenizer': self.tokenizer_type,
            'using_tiktoken': self.encoder is not None
        }

    @staticmethod
    def is_tiktoken_available() -> bool:
        """Check if tiktoken is available for accurate counting."""
        return TIKTOKEN_AVAILABLE


def get_token_counter(profile_or_type) -> TokenCounter:
    """
    Get a token counter for the given profile or tokenizer type.

    Args:
        profile_or_type: Either an LLMProfile object or a tokenizer type string

    Returns:
        TokenCounter instance
    """
    if hasattr(profile_or_type, 'tokenizer_type'):
        return TokenCounter(profile_or_type.tokenizer_type)
    return TokenCounter(profile_or_type)
