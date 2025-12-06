"""Setup script for LLM Context Manager."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="llm-context-manager",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Intelligently package codebases into optimal context windows for LLMs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/llm-context-manager",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "": ["profiles/*.yaml"],
    },
    python_requires=">=3.11",
    install_requires=[
        "click>=8.0.0",
        "tiktoken>=0.5.0",
        "pyyaml>=6.0.0",
    ],
    extras_require={
        "watch": ["watchdog>=3.0.0"],
        "parsing": [
            "tree-sitter>=0.21.0",
            "tree-sitter-python>=0.21.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
        ],
        "all": [
            "watchdog>=3.0.0",
            "tree-sitter>=0.21.0",
            "tree-sitter-python>=0.21.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "llm-context=context_manager.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: General",
        "Topic :: Utilities",
    ],
    keywords="llm, context, codebase, ai, claude, gpt, tokenizer",
)
