# context_manager/models.py
"""
LLM Profile definitions and management.
Defines characteristics and limits for different LLMs.
"""

import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class LLMProfile:
    """
    Defines characteristics and limits for different LLMs.
    """
    name: str
    max_tokens: int
    optimal_tokens: int
    tokenizer_type: str
    chunking_strategy: str
    include_tree: bool
    output_format: str
    description: str = ""

    @classmethod
    def from_dict(cls, name: str, config: Dict[str, Any]) -> 'LLMProfile':
        """Create profile from dictionary config."""
        return cls(
            name=config.get('name', name),
            max_tokens=config['max_tokens'],
            optimal_tokens=config.get('optimal_tokens', int(config['max_tokens'] * 0.8)),
            tokenizer_type=config.get('tokenizer_type', 'cl100k_base'),
            chunking_strategy=config.get('chunking_strategy', 'file'),
            include_tree=config.get('include_tree', True),
            output_format=config.get('output_format', 'xml'),
            description=config.get('description', '')
        )

    @classmethod
    def load(cls, profile_name: str) -> 'LLMProfile':
        """
        Load profile from YAML file.

        Args:
            profile_name: Name of the profile (without .yaml extension)

        Returns:
            LLMProfile instance

        Raises:
            ValueError: If profile not found
        """
        # Try multiple locations for profiles
        possible_paths = [
            Path(__file__).parent.parent / 'profiles' / f'{profile_name}.yaml',
            Path.cwd() / 'profiles' / f'{profile_name}.yaml',
            Path(__file__).parent / 'profiles' / f'{profile_name}.yaml',
        ]

        profile_path = None
        for path in possible_paths:
            if path.exists():
                profile_path = path
                break

        if not profile_path:
            # Check if it's a built-in profile
            builtin = cls._get_builtin_profiles()
            if profile_name in builtin:
                return cls.from_dict(profile_name, builtin[profile_name])

            available = cls.list_profiles()
            raise ValueError(
                f"Profile '{profile_name}' not found. "
                f"Available profiles: {', '.join(available)}"
            )

        with open(profile_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return cls.from_dict(profile_name, config)

    @classmethod
    def list_profiles(cls) -> List[str]:
        """List all available profiles (files + built-in)."""
        profiles = set(cls._get_builtin_profiles().keys())

        # Check for YAML files in profiles directory
        profiles_dirs = [
            Path(__file__).parent.parent / 'profiles',
            Path.cwd() / 'profiles',
        ]

        for profiles_dir in profiles_dirs:
            if profiles_dir.exists():
                for p in profiles_dir.glob('*.yaml'):
                    profiles.add(p.stem)
                for p in profiles_dir.glob('*.yml'):
                    profiles.add(p.stem)

        return sorted(profiles)

    @staticmethod
    def _get_builtin_profiles() -> Dict[str, Dict[str, Any]]:
        """Return built-in profile configurations."""
        return {
            'claude-sonnet': {
                'name': 'claude-sonnet-4',
                'max_tokens': 200000,
                'optimal_tokens': 160000,
                'tokenizer_type': 'claude',
                'chunking_strategy': 'hierarchical',
                'include_tree': True,
                'output_format': 'xml',
                'description': 'Claude Sonnet 4 with 200K context window'
            },
            'claude-opus': {
                'name': 'claude-opus-4',
                'max_tokens': 200000,
                'optimal_tokens': 160000,
                'tokenizer_type': 'claude',
                'chunking_strategy': 'hierarchical',
                'include_tree': True,
                'output_format': 'xml',
                'description': 'Claude Opus 4 with 200K context window'
            },
            'claude-haiku': {
                'name': 'claude-haiku-3.5',
                'max_tokens': 200000,
                'optimal_tokens': 160000,
                'tokenizer_type': 'claude',
                'chunking_strategy': 'hierarchical',
                'include_tree': True,
                'output_format': 'xml',
                'description': 'Claude Haiku 3.5 with 200K context window'
            },
            'gpt4': {
                'name': 'gpt-4-turbo',
                'max_tokens': 128000,
                'optimal_tokens': 100000,
                'tokenizer_type': 'cl100k_base',
                'chunking_strategy': 'hierarchical',
                'include_tree': True,
                'output_format': 'xml',
                'description': 'GPT-4 Turbo with 128K context'
            },
            'gpt4o': {
                'name': 'gpt-4o',
                'max_tokens': 128000,
                'optimal_tokens': 100000,
                'tokenizer_type': 'cl100k_base',
                'chunking_strategy': 'hierarchical',
                'include_tree': True,
                'output_format': 'xml',
                'description': 'GPT-4o with 128K context'
            },
            'gpt4o-mini': {
                'name': 'gpt-4o-mini',
                'max_tokens': 128000,
                'optimal_tokens': 100000,
                'tokenizer_type': 'cl100k_base',
                'chunking_strategy': 'file',
                'include_tree': True,
                'output_format': 'markdown',
                'description': 'GPT-4o Mini with 128K context'
            },
            'qwen': {
                'name': 'qwen-2.5-coder',
                'max_tokens': 32000,
                'optimal_tokens': 28000,
                'tokenizer_type': 'gpt2',
                'chunking_strategy': 'file',
                'include_tree': True,
                'output_format': 'markdown',
                'description': 'Qwen 2.5 Coder with 32K context'
            },
            'qwen-long': {
                'name': 'qwen-2.5-coder-32b',
                'max_tokens': 131072,
                'optimal_tokens': 100000,
                'tokenizer_type': 'gpt2',
                'chunking_strategy': 'hierarchical',
                'include_tree': True,
                'output_format': 'markdown',
                'description': 'Qwen 2.5 Coder 32B with 128K context'
            },
            'llama': {
                'name': 'llama-3.1-70b',
                'max_tokens': 128000,
                'optimal_tokens': 100000,
                'tokenizer_type': 'gpt2',
                'chunking_strategy': 'file',
                'include_tree': True,
                'output_format': 'markdown',
                'description': 'Llama 3.1 70B with 128K context'
            },
            'mistral': {
                'name': 'mistral-large',
                'max_tokens': 32000,
                'optimal_tokens': 28000,
                'tokenizer_type': 'gpt2',
                'chunking_strategy': 'file',
                'include_tree': True,
                'output_format': 'markdown',
                'description': 'Mistral Large with 32K context'
            },
            'deepseek': {
                'name': 'deepseek-coder-v2',
                'max_tokens': 128000,
                'optimal_tokens': 100000,
                'tokenizer_type': 'gpt2',
                'chunking_strategy': 'hierarchical',
                'include_tree': True,
                'output_format': 'markdown',
                'description': 'DeepSeek Coder V2 with 128K context'
            },
            'gemini': {
                'name': 'gemini-1.5-pro',
                'max_tokens': 1000000,
                'optimal_tokens': 800000,
                'tokenizer_type': 'gpt2',
                'chunking_strategy': 'hierarchical',
                'include_tree': True,
                'output_format': 'xml',
                'description': 'Gemini 1.5 Pro with 1M context window'
            },
            'local-small': {
                'name': 'local-small',
                'max_tokens': 4096,
                'optimal_tokens': 3500,
                'tokenizer_type': 'gpt2',
                'chunking_strategy': 'file',
                'include_tree': True,
                'output_format': 'plain',
                'description': 'Small local model with 4K context'
            },
            'local-medium': {
                'name': 'local-medium',
                'max_tokens': 8192,
                'optimal_tokens': 7000,
                'tokenizer_type': 'gpt2',
                'chunking_strategy': 'file',
                'include_tree': True,
                'output_format': 'markdown',
                'description': 'Medium local model with 8K context'
            },
            'local-large': {
                'name': 'local-large',
                'max_tokens': 32000,
                'optimal_tokens': 28000,
                'tokenizer_type': 'gpt2',
                'chunking_strategy': 'file',
                'include_tree': True,
                'output_format': 'markdown',
                'description': 'Large local model with 32K context'
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            'name': self.name,
            'max_tokens': self.max_tokens,
            'optimal_tokens': self.optimal_tokens,
            'tokenizer_type': self.tokenizer_type,
            'chunking_strategy': self.chunking_strategy,
            'include_tree': self.include_tree,
            'output_format': self.output_format,
            'description': self.description
        }

    def save(self, filepath: Optional[str] = None) -> str:
        """
        Save profile to YAML file.

        Args:
            filepath: Optional path to save to. Defaults to profiles directory.

        Returns:
            Path where profile was saved
        """
        if filepath is None:
            profiles_dir = Path(__file__).parent.parent / 'profiles'
            profiles_dir.mkdir(exist_ok=True)
            filepath = profiles_dir / f'{self.name}.yaml'

        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

        return str(filepath)

    def __repr__(self) -> str:
        return (
            f"LLMProfile(name='{self.name}', max_tokens={self.max_tokens:,}, "
            f"tokenizer='{self.tokenizer_type}', format='{self.output_format}')"
        )


def create_custom_profile(
    name: str,
    max_tokens: int,
    tokenizer_type: str = 'gpt2',
    optimal_ratio: float = 0.8,
    output_format: str = 'markdown',
    description: str = ''
) -> LLMProfile:
    """
    Create a custom LLM profile.

    Args:
        name: Profile name
        max_tokens: Maximum context window size
        tokenizer_type: Type of tokenizer ('claude', 'cl100k_base', 'gpt2')
        optimal_ratio: Ratio of max_tokens to use as optimal (default 0.8)
        output_format: Output format ('xml', 'markdown', 'plain')
        description: Profile description

    Returns:
        LLMProfile instance
    """
    return LLMProfile(
        name=name,
        max_tokens=max_tokens,
        optimal_tokens=int(max_tokens * optimal_ratio),
        tokenizer_type=tokenizer_type,
        chunking_strategy='file' if max_tokens < 50000 else 'hierarchical',
        include_tree=True,
        output_format=output_format,
        description=description or f"Custom profile: {name}"
    )
