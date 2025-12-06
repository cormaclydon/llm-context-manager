# tests/conftest.py
"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def sample_codebase(tmp_path):
    """Create a sample codebase structure for testing."""
    # Create main entry point
    (tmp_path / "main.py").write_text('''#!/usr/bin/env python
"""Main entry point for the application."""

from src.app import Application


def main():
    """Run the application."""
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
''')

    # Create src directory with modules
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    (src_dir / "__init__.py").write_text('''"""Source package."""

from .app import Application
from .utils import helper

__all__ = ["Application", "helper"]
''')

    (src_dir / "app.py").write_text('''"""Application module."""


class Application:
    """Main application class."""

    def __init__(self):
        self.running = False

    def run(self):
        """Run the application."""
        self.running = True
        print("Application running...")

    def stop(self):
        """Stop the application."""
        self.running = False
''')

    (src_dir / "utils.py").write_text('''"""Utility functions."""


def helper(x: int) -> int:
    """Double the input value."""
    return x * 2


def format_output(data: dict) -> str:
    """Format data for output."""
    return str(data)
''')

    # Create tests directory
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    (tests_dir / "__init__.py").write_text("")

    (tests_dir / "test_app.py").write_text('''"""Tests for app module."""

import pytest
from src.app import Application


def test_application_init():
    app = Application()
    assert app.running is False


def test_application_run():
    app = Application()
    app.run()
    assert app.running is True
''')

    # Create config files
    (tmp_path / "config.yaml").write_text('''# Configuration file
app:
  name: Sample App
  version: 1.0.0
  debug: true

database:
  host: localhost
  port: 5432
''')

    (tmp_path / "README.md").write_text('''# Sample Project

A sample Python project for testing.

## Installation

```bash
pip install -e .
```

## Usage

```python
from src import Application
app = Application()
app.run()
```
''')

    return tmp_path


@pytest.fixture
def large_codebase(tmp_path):
    """Create a large codebase for testing token limits."""
    # Create many files with content
    for i in range(50):
        (tmp_path / f"module_{i}.py").write_text(f'''"""Module {i}."""


class Module{i}:
    """Class for module {i}."""

    def __init__(self):
        self.value = {i}

    def process(self):
        """Process data."""
        return self.value * 2

    def transform(self, x):
        """Transform input."""
        return x + self.value
''' + '\n' * 50)  # Add extra lines

    return tmp_path
