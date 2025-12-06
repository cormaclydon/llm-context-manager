# tests/test_analyzer.py
"""Tests for the CodebaseAnalyzer module."""

import pytest
import tempfile
from pathlib import Path

from context_manager.analyzer import CodebaseAnalyzer


class TestCodebaseAnalyzer:
    """Test cases for CodebaseAnalyzer."""

    def test_analyze_empty_directory(self, tmp_path):
        """Test analyzing an empty directory."""
        analyzer = CodebaseAnalyzer(str(tmp_path))
        result = analyzer.analyze()

        assert 'files' in result
        assert 'structure' in result
        assert len(result['files']) == 0

    def test_analyze_with_python_files(self, tmp_path):
        """Test analyzing a directory with Python files."""
        # Create test files
        (tmp_path / "main.py").write_text("def main():\n    pass\n")
        (tmp_path / "utils.py").write_text("def helper():\n    pass\n")

        analyzer = CodebaseAnalyzer(str(tmp_path))
        result = analyzer.analyze()

        assert len(result['files']) == 2
        # main.py should have higher priority
        assert result['files'][0]['path'] == 'main.py'
        assert result['files'][0]['priority'] == 100

    def test_ignore_patterns(self, tmp_path):
        """Test that ignore patterns work correctly."""
        # Create files and directories
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "main.cpython-311.pyc").write_bytes(b"binary")

        analyzer = CodebaseAnalyzer(str(tmp_path))
        result = analyzer.analyze()

        # Should only find main.py
        assert len(result['files']) == 1
        assert result['files'][0]['path'] == 'main.py'

    def test_priority_calculation(self, tmp_path):
        """Test file priority calculation."""
        # Create files with different priorities
        (tmp_path / "main.py").write_text("if __name__ == '__main__': pass")
        (tmp_path / "config.yaml").write_text("key: value")
        (tmp_path / "README.md").write_text("# Readme")

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "core.py").write_text("class Core: pass")

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_core.py").write_text("def test_core(): pass")

        analyzer = CodebaseAnalyzer(str(tmp_path))
        result = analyzer.analyze()

        # Check priorities are in correct order
        paths = [f['path'] for f in result['files']]
        priorities = {f['path']: f['priority'] for f in result['files']}

        assert priorities['main.py'] == 100
        assert priorities.get('src/core.py', 0) >= 70
        assert priorities.get('tests/test_core.py', 0) == 40
        assert priorities.get('config.yaml', 0) == 30

    def test_file_type_detection(self, tmp_path):
        """Test file type detection."""
        (tmp_path / "main.py").write_text("pass")
        (tmp_path / "test_main.py").write_text("pass")
        (tmp_path / "config.json").write_text("{}")
        (tmp_path / "README.md").write_text("# Docs")

        analyzer = CodebaseAnalyzer(str(tmp_path))
        result = analyzer.analyze()

        types = {f['path']: f['type'] for f in result['files']}

        assert types['main.py'] == 'entry_point'
        assert types['test_main.py'] == 'test'
        assert types['config.json'] == 'config'
        assert types['README.md'] == 'documentation'

    def test_structure_building(self, tmp_path):
        """Test directory structure building."""
        (tmp_path / "main.py").write_text("pass")
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "module.py").write_text("pass")

        analyzer = CodebaseAnalyzer(str(tmp_path))
        result = analyzer.analyze()

        assert 'structure' in result
        assert 'main.py' in result['structure']
        assert 'src' in result['structure']
        assert 'module.py' in result['structure']['src']

    def test_summary_stats(self, tmp_path):
        """Test summary statistics generation."""
        (tmp_path / "main.py").write_text("print('hello world')")
        (tmp_path / "test.py").write_text("def test(): pass")

        analyzer = CodebaseAnalyzer(str(tmp_path))
        result = analyzer.analyze()

        assert 'summary' in result
        summary = result['summary']
        assert summary['total_files'] == 2
        assert summary['total_size'] > 0
        assert 'by_type' in summary
        assert 'by_extension' in summary


class TestPythonStructureExtraction:
    """Test Python code structure extraction."""

    def test_extract_functions(self, tmp_path):
        """Test function extraction from Python files."""
        code = """
def foo():
    pass

def bar(x, y):
    return x + y

async def baz():
    pass
"""
        (tmp_path / "funcs.py").write_text(code)

        analyzer = CodebaseAnalyzer(str(tmp_path))
        result = analyzer.analyze()

        file_info = result['files'][0]
        assert 'functions' in file_info
        assert 'foo' in file_info['functions']
        assert 'bar' in file_info['functions']

    def test_extract_classes(self, tmp_path):
        """Test class extraction from Python files."""
        code = """
class MyClass:
    pass

class AnotherClass(Base):
    def method(self):
        pass
"""
        (tmp_path / "classes.py").write_text(code)

        analyzer = CodebaseAnalyzer(str(tmp_path))
        result = analyzer.analyze()

        file_info = result['files'][0]
        assert 'classes' in file_info
        assert 'MyClass' in file_info['classes']
        assert 'AnotherClass' in file_info['classes']

    def test_extract_imports(self, tmp_path):
        """Test import extraction from Python files."""
        code = """
import os
import sys
from pathlib import Path
from typing import List, Optional
"""
        (tmp_path / "imports.py").write_text(code)

        analyzer = CodebaseAnalyzer(str(tmp_path))
        result = analyzer.analyze()

        file_info = result['files'][0]
        assert 'imports' in file_info
        assert len(file_info['imports']) >= 2
