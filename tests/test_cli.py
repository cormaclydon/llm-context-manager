# tests/test_cli.py
"""Tests for the CLI module."""

import pytest
import json
from pathlib import Path
from click.testing import CliRunner

from context_manager.cli import cli, echo_success, echo_error, echo_info, echo_warning


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project for testing."""
    (tmp_path / "main.py").write_text("def main():\n    pass\n")
    (tmp_path / "utils.py").write_text("def helper():\n    return 42\n")
    (tmp_path / "config.yaml").write_text("key: value\n")
    (tmp_path / "README.md").write_text("# Test Project\n")

    src = tmp_path / "src"
    src.mkdir()
    (src / "__init__.py").write_text("from .app import App\n")
    (src / "app.py").write_text("class App:\n    pass\n")

    return tmp_path


class TestCLIHelp:
    """Test CLI help commands."""

    def test_main_help(self, runner):
        """Test main help output."""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'LLM Context Manager' in result.output
        assert 'pack' in result.output
        assert 'profiles' in result.output

    def test_version(self, runner):
        """Test version output."""
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert '0.1.0' in result.output

    def test_pack_help(self, runner):
        """Test pack command help."""
        result = runner.invoke(cli, ['pack', '--help'])
        assert result.exit_code == 0
        assert '--profile' in result.output
        assert '--output' in result.output
        assert '--watch' in result.output

    def test_analyze_help(self, runner):
        """Test analyze command help."""
        result = runner.invoke(cli, ['analyze', '--help'])
        assert result.exit_code == 0
        assert '--top' in result.output
        assert '--json' in result.output


class TestPackCommand:
    """Test the pack command."""

    def test_pack_default(self, runner, sample_project):
        """Test packing with default options."""
        result = runner.invoke(cli, ['pack', str(sample_project)])
        assert result.exit_code == 0
        assert '[OK] Generated' in result.output
        assert 'Tokens:' in result.output

    def test_pack_with_profile(self, runner, sample_project):
        """Test packing with specific profile."""
        result = runner.invoke(cli, ['pack', str(sample_project), '-p', 'gpt4'])
        assert result.exit_code == 0
        assert '[OK] Generated' in result.output

    def test_pack_with_output(self, runner, sample_project):
        """Test packing with custom output path."""
        output_file = sample_project / "output.xml"
        result = runner.invoke(cli, ['pack', str(sample_project), '-o', str(output_file)])
        assert result.exit_code == 0
        assert output_file.exists()

    def test_pack_markdown_format(self, runner, sample_project):
        """Test packing with markdown format."""
        output_file = sample_project / "output.md"
        result = runner.invoke(cli, ['pack', str(sample_project), '-f', 'markdown', '-o', str(output_file)])
        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert '# Codebase Context' in content

    def test_pack_plain_format(self, runner, sample_project):
        """Test packing with plain format."""
        output_file = sample_project / "output.txt"
        result = runner.invoke(cli, ['pack', str(sample_project), '-f', 'plain', '-o', str(output_file)])
        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert 'CODEBASE CONTEXT' in content

    def test_pack_verbose(self, runner, sample_project):
        """Test packing with verbose output."""
        result = runner.invoke(cli, ['pack', str(sample_project), '-v'])
        assert result.exit_code == 0
        assert '[INFO] Profile:' in result.output
        assert '[INFO] Max tokens:' in result.output

    def test_pack_quiet(self, runner, sample_project):
        """Test packing with quiet output."""
        result = runner.invoke(cli, ['pack', str(sample_project), '-q'])
        assert result.exit_code == 0
        # Quiet mode should have minimal output
        assert 'Analyzing' not in result.output

    def test_pack_no_tree(self, runner, sample_project):
        """Test packing without file tree."""
        output_file = sample_project / "output.xml"
        result = runner.invoke(cli, ['pack', str(sample_project), '--no-tree', '-o', str(output_file)])
        assert result.exit_code == 0
        content = output_file.read_text()
        assert '<structure>' not in content

    def test_pack_with_focus(self, runner, sample_project):
        """Test packing with focus files."""
        result = runner.invoke(cli, ['pack', str(sample_project), '-F', 'main.py'])
        assert result.exit_code == 0

    def test_pack_with_ignore(self, runner, sample_project):
        """Test packing with additional ignore patterns."""
        result = runner.invoke(cli, ['pack', str(sample_project), '-i', 'utils.py'])
        assert result.exit_code == 0

    def test_pack_with_max_tokens(self, runner, sample_project):
        """Test packing with custom max tokens."""
        result = runner.invoke(cli, ['pack', str(sample_project), '-t', '5000'])
        assert result.exit_code == 0

    def test_pack_invalid_profile(self, runner, sample_project):
        """Test packing with invalid profile."""
        result = runner.invoke(cli, ['pack', str(sample_project), '-p', 'nonexistent'])
        assert result.exit_code == 1
        assert '[ERROR]' in result.output

    def test_pack_invalid_directory(self, runner):
        """Test packing with non-existent directory."""
        result = runner.invoke(cli, ['pack', '/nonexistent/path'])
        assert result.exit_code == 2  # Click's error for invalid path


class TestProfilesCommand:
    """Test the profiles command."""

    def test_profiles_list(self, runner):
        """Test listing profiles."""
        result = runner.invoke(cli, ['profiles'])
        assert result.exit_code == 0
        assert 'claude-sonnet' in result.output
        assert 'gpt' in result.output
        assert 'Total:' in result.output

    def test_profiles_verbose(self, runner):
        """Test listing profiles with verbose output."""
        result = runner.invoke(cli, ['profiles', '-v'])
        assert result.exit_code == 0
        assert 'Format:' in result.output
        assert 'Tokenizer:' in result.output


class TestAnalyzeCommand:
    """Test the analyze command."""

    def test_analyze_default(self, runner, sample_project):
        """Test analyzing with default options."""
        result = runner.invoke(cli, ['analyze', str(sample_project)])
        assert result.exit_code == 0
        assert 'Codebase Analysis' in result.output
        assert 'Total files:' in result.output

    def test_analyze_with_top(self, runner, sample_project):
        """Test analyzing with limited top files."""
        result = runner.invoke(cli, ['analyze', str(sample_project), '--top', '3'])
        assert result.exit_code == 0
        assert 'Top 3 files' in result.output

    def test_analyze_with_type_filter(self, runner, sample_project):
        """Test analyzing with type filter."""
        result = runner.invoke(cli, ['analyze', str(sample_project), '-t', 'source'])
        assert result.exit_code == 0
        assert 'Filtered to type: source' in result.output

    def test_analyze_json_output(self, runner, sample_project):
        """Test analyzing with JSON output."""
        result = runner.invoke(cli, ['analyze', str(sample_project), '--json'])
        assert result.exit_code == 0
        # Should be valid JSON
        data = json.loads(result.output)
        assert 'files' in data
        assert 'summary' in data


class TestTokensCommand:
    """Test the tokens command."""

    def test_tokens_file(self, runner, sample_project):
        """Test counting tokens in a file."""
        result = runner.invoke(cli, ['tokens', str(sample_project / 'main.py')])
        assert result.exit_code == 0
        assert 'Token Analysis' in result.output
        assert 'Tokens:' in result.output
        assert 'Characters:' in result.output

    def test_tokens_with_profile(self, runner, sample_project):
        """Test counting tokens with specific profile."""
        result = runner.invoke(cli, ['tokens', str(sample_project / 'main.py'), '-p', 'gpt4'])
        assert result.exit_code == 0
        assert 'gpt-4-turbo' in result.output


class TestEstimateCommand:
    """Test the estimate command."""

    def test_estimate_default(self, runner, sample_project):
        """Test estimating tokens for a codebase."""
        result = runner.invoke(cli, ['estimate', str(sample_project)])
        assert result.exit_code == 0
        assert 'Token Estimate' in result.output
        assert 'Total tokens:' in result.output

    def test_estimate_with_profile(self, runner, sample_project):
        """Test estimating with specific profile."""
        result = runner.invoke(cli, ['estimate', str(sample_project), '-p', 'local-small'])
        assert result.exit_code == 0
        assert 'local-small' in result.output


class TestCreateProfileCommand:
    """Test the create-profile command."""

    def test_create_profile(self, runner, tmp_path):
        """Test creating a custom profile."""
        # Change to tmp directory so profile is created there
        result = runner.invoke(cli, [
            'create-profile',
            '-n', 'test-profile',
            '-t', '8000',
            '--tokenizer', 'gpt2',
            '-f', 'markdown',
            '-d', 'Test profile'
        ])
        assert result.exit_code == 0
        assert '[OK] Created profile' in result.output


class TestEchoFunctions:
    """Test the echo helper functions."""

    def test_echo_success(self, runner):
        """Test echo_success function."""
        @cli.command()
        def test_success():
            echo_success("Test message")

        result = runner.invoke(cli, ['test-success'])
        assert '[OK]' in result.output

    def test_echo_error(self, runner):
        """Test echo_error function."""
        @cli.command()
        def test_error():
            echo_error("Error message")

        result = runner.invoke(cli, ['test-error'])
        assert '[ERROR]' in result.output

    def test_echo_info(self, runner):
        """Test echo_info function."""
        @cli.command()
        def test_info():
            echo_info("Info message")

        result = runner.invoke(cli, ['test-info'])
        assert '[INFO]' in result.output

    def test_echo_warning(self, runner):
        """Test echo_warning function."""
        @cli.command()
        def test_warning():
            echo_warning("Warning message")

        result = runner.invoke(cli, ['test-warning'])
        assert '[WARN]' in result.output
