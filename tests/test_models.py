# tests/test_models.py
"""Tests for the LLMProfile module."""

import pytest
import tempfile
from pathlib import Path

from context_manager.models import LLMProfile, create_custom_profile


class TestLLMProfile:
    """Test cases for LLMProfile."""

    def test_load_builtin_profile(self):
        """Test loading a built-in profile."""
        profile = LLMProfile.load('claude-sonnet')

        assert profile.name == 'claude-sonnet-4'
        assert profile.max_tokens == 200000
        assert profile.optimal_tokens == 160000
        assert profile.tokenizer_type == 'claude'
        assert profile.output_format == 'xml'

    def test_load_gpt4_profile(self):
        """Test loading GPT-4 profile."""
        profile = LLMProfile.load('gpt4')

        assert profile.max_tokens == 128000
        assert profile.tokenizer_type == 'cl100k_base'

    def test_load_qwen_profile(self):
        """Test loading Qwen profile."""
        profile = LLMProfile.load('qwen')

        assert profile.max_tokens == 32000
        assert profile.output_format == 'markdown'

    def test_load_nonexistent_profile(self):
        """Test loading non-existent profile raises error."""
        with pytest.raises(ValueError) as exc_info:
            LLMProfile.load('nonexistent-profile-xyz')

        assert 'not found' in str(exc_info.value)

    def test_list_profiles(self):
        """Test listing available profiles."""
        profiles = LLMProfile.list_profiles()

        assert isinstance(profiles, list)
        assert len(profiles) > 0
        assert 'claude-sonnet' in profiles
        assert 'gpt4' in profiles
        assert 'qwen' in profiles

    def test_profile_to_dict(self):
        """Test converting profile to dictionary."""
        profile = LLMProfile.load('claude-sonnet')
        data = profile.to_dict()

        assert isinstance(data, dict)
        assert 'name' in data
        assert 'max_tokens' in data
        assert 'tokenizer_type' in data

    def test_profile_save_and_load(self, tmp_path):
        """Test saving and loading custom profile."""
        profile = create_custom_profile(
            name='test-model',
            max_tokens=8000,
            description='Test model'
        )

        # Save to temp directory
        save_path = tmp_path / 'test-model.yaml'
        profile.save(str(save_path))

        assert save_path.exists()

        # Load back
        import yaml
        with open(save_path) as f:
            loaded_data = yaml.safe_load(f)

        assert loaded_data['name'] == 'test-model'
        assert loaded_data['max_tokens'] == 8000

    def test_profile_repr(self):
        """Test profile string representation."""
        profile = LLMProfile.load('claude-sonnet')
        repr_str = repr(profile)

        assert 'LLMProfile' in repr_str
        assert 'claude-sonnet' in repr_str
        assert '200,000' in repr_str


class TestCreateCustomProfile:
    """Test cases for create_custom_profile function."""

    def test_create_basic_profile(self):
        """Test creating a basic custom profile."""
        profile = create_custom_profile(
            name='my-model',
            max_tokens=16000
        )

        assert profile.name == 'my-model'
        assert profile.max_tokens == 16000
        assert profile.optimal_tokens == 12800  # 80% of max

    def test_create_profile_with_options(self):
        """Test creating profile with all options."""
        profile = create_custom_profile(
            name='custom-llm',
            max_tokens=32000,
            tokenizer_type='gpt2',
            optimal_ratio=0.9,
            output_format='plain',
            description='My custom LLM'
        )

        assert profile.name == 'custom-llm'
        assert profile.max_tokens == 32000
        assert profile.optimal_tokens == 28800  # 90% of max
        assert profile.tokenizer_type == 'gpt2'
        assert profile.output_format == 'plain'
        assert profile.description == 'My custom LLM'

    def test_chunking_strategy_selection(self):
        """Test that chunking strategy is set based on token size."""
        small_profile = create_custom_profile('small', 4000)
        large_profile = create_custom_profile('large', 100000)

        # Small models should use 'file' strategy
        assert small_profile.chunking_strategy == 'file'

        # Large models should use 'hierarchical' strategy
        assert large_profile.chunking_strategy == 'hierarchical'


class TestBuiltinProfiles:
    """Test all built-in profiles load correctly."""

    @pytest.mark.parametrize('profile_name', [
        'claude-sonnet',
        'claude-opus',
        'claude-haiku',
        'gpt4',
        'gpt4o',
        'gpt4o-mini',
        'qwen',
        'qwen-long',
        'llama',
        'mistral',
        'deepseek',
        'gemini',
        'local-small',
        'local-medium',
        'local-large',
    ])
    def test_profile_loads(self, profile_name):
        """Test that each built-in profile loads without error."""
        profile = LLMProfile.load(profile_name)

        assert profile.max_tokens > 0
        assert profile.optimal_tokens > 0
        assert profile.optimal_tokens <= profile.max_tokens
        assert profile.tokenizer_type in ['claude', 'cl100k_base', 'gpt2', 'p50k_base']
        assert profile.output_format in ['xml', 'markdown', 'plain']
