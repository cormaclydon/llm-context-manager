# context_manager/cli.py
"""
Command-line interface for LLM Context Manager.
"""

import sys
from pathlib import Path
from typing import Optional, List

import click

from .analyzer import CodebaseAnalyzer
from .packager import ContextPackager
from .models import LLMProfile, create_custom_profile
from .tokenizers import TokenCounter
from .watcher import watch_blocking, is_watchdog_available


# CLI styling
COLORS = {
    'success': 'green',
    'error': 'red',
    'warning': 'yellow',
    'info': 'cyan',
    'muted': 'bright_black'
}


def echo_success(msg: str):
    click.secho(f'[OK] {msg}', fg=COLORS['success'])


def echo_error(msg: str):
    click.secho(f'[ERROR] {msg}', fg=COLORS['error'], err=True)


def echo_info(msg: str):
    click.secho(f'[INFO] {msg}', fg=COLORS['info'])


def echo_warning(msg: str):
    click.secho(f'[WARN] {msg}', fg=COLORS['warning'])


@click.group()
@click.version_option(version='0.1.0', prog_name='llm-context')
def cli():
    """
    LLM Context Manager - Package codebases for AI context.

    Intelligently package your codebase into optimal context windows
    for different LLMs like Claude, GPT-4, Qwen, and local models.

    \b
    Examples:
        llm-context pack                    # Pack current directory
        llm-context pack . -p gpt4 -o ctx   # Use GPT-4 profile
        llm-context pack --watch            # Auto-regenerate on changes
        llm-context profiles                # List available profiles
        llm-context analyze ./my-project    # Analyze without packing
    """
    pass


@cli.command()
@click.argument('directory', type=click.Path(exists=True), default='.')
@click.option(
    '--profile', '-p',
    default='claude-sonnet',
    help='LLM profile to use (see "profiles" command for list)'
)
@click.option(
    '--output', '-o',
    default=None,
    help='Output file path (default: llm-context.<format>)'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['xml', 'markdown', 'plain']),
    default=None,
    help='Output format (overrides profile default)'
)
@click.option(
    '--watch', '-w',
    is_flag=True,
    help='Watch for changes and auto-regenerate'
)
@click.option(
    '--focus', '-F',
    multiple=True,
    help='Focus on specific files/patterns (can specify multiple)'
)
@click.option(
    '--ignore', '-i',
    multiple=True,
    help='Additional patterns to ignore (can specify multiple)'
)
@click.option(
    '--max-tokens', '-t',
    type=int,
    default=None,
    help='Override maximum tokens from profile'
)
@click.option(
    '--no-tree',
    is_flag=True,
    help='Exclude file tree from output'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Verbose output'
)
@click.option(
    '--quiet', '-q',
    is_flag=True,
    help='Minimal output'
)
def pack(
    directory: str,
    profile: str,
    output: Optional[str],
    format: Optional[str],
    watch: bool,
    focus: tuple,
    ignore: tuple,
    max_tokens: Optional[int],
    no_tree: bool,
    verbose: bool,
    quiet: bool
):
    """
    Package codebase into LLM context.

    DIRECTORY is the path to the codebase (defaults to current directory).

    \b
    Examples:
        llm-context pack                           # Current dir, Claude profile
        llm-context pack ./src -p gpt4             # Specific dir, GPT-4 profile
        llm-context pack -o context.md -f markdown # Markdown output
        llm-context pack --watch                   # Watch mode
        llm-context pack -F src/main.py -F api/    # Focus on specific files
    """
    try:
        # Load profile
        llm_profile = LLMProfile.load(profile)

        # Apply overrides
        if format:
            llm_profile.output_format = format
        if max_tokens:
            llm_profile.max_tokens = max_tokens
            llm_profile.optimal_tokens = int(max_tokens * 0.8)
        if no_tree:
            llm_profile.include_tree = False

        # Determine output path
        if output is None:
            ext_map = {'xml': 'xml', 'markdown': 'md', 'plain': 'txt'}
            ext = ext_map.get(llm_profile.output_format, 'txt')
            output = f'llm-context.{ext}'

        if verbose:
            echo_info(f'Profile: {llm_profile.name}')
            echo_info(f'Max tokens: {llm_profile.max_tokens:,}')
            echo_info(f'Optimal tokens: {llm_profile.optimal_tokens:,}')
            echo_info(f'Output format: {llm_profile.output_format}')
            echo_info(f'Output file: {output}')

        # Analyze codebase
        if not quiet:
            click.echo(f'Analyzing {directory}...')

        analyzer = CodebaseAnalyzer(directory, ignore_patterns=list(ignore))
        analysis = analyzer.analyze()

        if verbose:
            echo_info(f'Found {len(analysis["files"])} files')
            if analysis.get('summary'):
                summary = analysis['summary']
                echo_info(f'Total size: {summary["total_size"]:,} bytes')
                for ftype, count in summary.get('by_type', {}).items():
                    click.echo(f'  - {ftype}: {count}')

        # Package context
        packager = ContextPackager(llm_profile)
        context = packager.package(
            analysis,
            output,
            focus_files=list(focus) if focus else None
        )

        # Report results
        stats = packager.get_stats(context)
        token_count = stats['token_count']

        if not quiet:
            echo_success(f'Generated: {output}')
            utilization = stats['utilization']
            util_color = 'green' if utilization < 80 else ('yellow' if utilization < 95 else 'red')
            click.echo(f'  Tokens: {token_count:,} / {llm_profile.optimal_tokens:,} ({utilization:.1f}%)',
                      color=util_color)
            click.echo(f'  Files included: {len(analysis["files"])}')

        # Watch mode
        if watch:
            if not is_watchdog_available():
                echo_error('Watch mode requires watchdog library')
                echo_info('Install with: pip install watchdog')
                sys.exit(1)

            def regenerate_callback(changed_files: List[str]):
                nonlocal analysis
                click.echo('Regenerating context...')
                analysis = analyzer.analyze()
                context = packager.package(
                    analysis,
                    output,
                    focus_files=list(focus) if focus else None
                )
                stats = packager.get_stats(context)
                echo_success(f'Updated: {stats["token_count"]:,} tokens')

            watch_blocking(directory, regenerate_callback)

    except ValueError as e:
        echo_error(str(e))
        sys.exit(1)
    except Exception as e:
        echo_error(f'Error: {str(e)}')
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed profile info')
def profiles(verbose: bool):
    """
    List available LLM profiles.

    Shows all built-in and custom profiles with their token limits.
    """
    available = LLMProfile.list_profiles()

    click.echo('\nAvailable profiles:\n')

    for profile_name in available:
        try:
            profile = LLMProfile.load(profile_name)
            tokens_str = f'{profile.max_tokens:,}'

            click.echo(f'  {click.style(profile.name, fg="cyan", bold=True)}')
            click.echo(f'    Tokens: {tokens_str} (optimal: {profile.optimal_tokens:,})')

            if verbose:
                click.echo(f'    Format: {profile.output_format}')
                click.echo(f'    Tokenizer: {profile.tokenizer_type}')
                click.echo(f'    Strategy: {profile.chunking_strategy}')
                if profile.description:
                    click.echo(f'    {click.style(profile.description, fg="bright_black")}')
            click.echo()
        except Exception as e:
            click.echo(f'  {profile_name} (error loading: {e})')

    click.echo(f'Total: {len(available)} profiles')


@cli.command()
@click.argument('directory', type=click.Path(exists=True), default='.')
@click.option('--top', '-n', default=15, help='Number of top files to show')
@click.option('--type', '-t', 'file_type', default=None, help='Filter by file type')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
def analyze(directory: str, top: int, file_type: Optional[str], as_json: bool):
    """
    Analyze codebase structure without packaging.

    Shows file priorities, types, and structure analysis.

    \b
    Examples:
        llm-context analyze                    # Analyze current directory
        llm-context analyze ./src --top 20    # Show top 20 files
        llm-context analyze -t source          # Only source files
        llm-context analyze --json             # JSON output
    """
    analyzer = CodebaseAnalyzer(directory)
    analysis = analyzer.analyze()

    if as_json:
        import json
        # Convert to JSON-serializable format
        output = {
            'summary': analysis.get('summary', {}),
            'files': [
                {k: v for k, v in f.items() if k != 'absolute_path'}
                for f in analysis['files']
            ]
        }
        click.echo(json.dumps(output, indent=2))
        return

    click.echo(f'\n{click.style("Codebase Analysis", bold=True)}: {directory}\n')

    summary = analysis.get('summary', {})
    click.echo(f'Total files: {summary.get("total_files", len(analysis["files"]))}')
    click.echo(f'Total size: {summary.get("total_size", 0):,} bytes')

    # Show by type
    if summary.get('by_type'):
        click.echo('\nFiles by type:')
        for ftype, count in sorted(summary['by_type'].items(), key=lambda x: -x[1]):
            click.echo(f'  {ftype}: {count}')

    # Filter if requested
    files = analysis['files']
    if file_type:
        files = [f for f in files if f['type'] == file_type]
        click.echo(f'\nFiltered to type: {file_type}')

    # Show top files
    click.echo(f'\n{click.style(f"Top {min(top, len(files))} files by priority:", bold=True)}')
    for file_info in files[:top]:
        priority = file_info['priority']
        path = file_info['path']
        ftype = file_info['type']

        # Color-code by priority
        if priority >= 90:
            color = 'green'
        elif priority >= 70:
            color = 'cyan'
        elif priority >= 40:
            color = 'yellow'
        else:
            color = 'bright_black'

        click.echo(f'  {click.style(f"{priority:3d}", fg=color)} | {path} ({ftype})')


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--profile', '-p', default='claude-sonnet', help='Profile for tokenizer')
def tokens(file_path: str, profile: str):
    """
    Count tokens in a file.

    \b
    Examples:
        llm-context tokens ./src/main.py
        llm-context tokens README.md -p gpt4
    """
    try:
        llm_profile = LLMProfile.load(profile)
        counter = TokenCounter(llm_profile.tokenizer_type)

        content = Path(file_path).read_text(encoding='utf-8')
        stats = counter.get_stats(content)

        click.echo(f'\n{click.style("Token Analysis", bold=True)}: {file_path}\n')
        click.echo(f'Tokenizer: {stats["tokenizer"]}')
        click.echo(f'Using tiktoken: {stats["using_tiktoken"]}')
        click.echo()
        click.echo(f'Tokens: {stats["tokens"]:,}')
        click.echo(f'Characters: {stats["characters"]:,}')
        click.echo(f'Lines: {stats["lines"]:,}')
        click.echo(f'Words: {stats["words"]:,}')
        click.echo(f'Chars/token: {stats["chars_per_token"]:.2f}')

        # Show context utilization
        click.echo()
        utilization = (stats['tokens'] / llm_profile.optimal_tokens) * 100
        click.echo(f'Profile: {llm_profile.name}')
        click.echo(f'Context usage: {utilization:.1f}% of {llm_profile.optimal_tokens:,} optimal tokens')

    except Exception as e:
        echo_error(str(e))
        sys.exit(1)


@cli.command()
@click.option('--name', '-n', required=True, help='Profile name')
@click.option('--max-tokens', '-t', required=True, type=int, help='Max context tokens')
@click.option('--tokenizer', default='gpt2', help='Tokenizer type')
@click.option('--format', '-f', default='markdown', help='Output format')
@click.option('--description', '-d', default='', help='Profile description')
def create_profile(name: str, max_tokens: int, tokenizer: str, format: str, description: str):
    """
    Create a custom LLM profile.

    \b
    Examples:
        llm-context create-profile -n my-model -t 16000
        llm-context create-profile -n phi-3 -t 4096 --tokenizer gpt2 -f plain
    """
    try:
        profile = create_custom_profile(
            name=name,
            max_tokens=max_tokens,
            tokenizer_type=tokenizer,
            output_format=format,
            description=description
        )

        saved_path = profile.save()
        echo_success(f'Created profile: {name}')
        click.echo(f'  Saved to: {saved_path}')
        click.echo(f'  Max tokens: {profile.max_tokens:,}')
        click.echo(f'  Optimal tokens: {profile.optimal_tokens:,}')

    except Exception as e:
        echo_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument('directory', type=click.Path(exists=True), default='.')
@click.option('--profile', '-p', default='claude-sonnet', help='Profile to estimate for')
def estimate(directory: str, profile: str):
    """
    Estimate tokens needed for a codebase.

    Shows how much of the context window the codebase would use.

    \b
    Examples:
        llm-context estimate
        llm-context estimate ./src -p qwen
    """
    try:
        llm_profile = LLMProfile.load(profile)
        counter = TokenCounter(llm_profile.tokenizer_type)

        click.echo(f'Analyzing {directory}...')

        analyzer = CodebaseAnalyzer(directory)
        analysis = analyzer.analyze()

        total_tokens = 0
        file_tokens = []

        for file_info in analysis['files']:
            try:
                content = Path(file_info['absolute_path']).read_text(encoding='utf-8')
                tokens = counter.count(content)
                total_tokens += tokens
                file_tokens.append((file_info['path'], tokens))
            except Exception:
                pass

        click.echo(f'\n{click.style("Token Estimate", bold=True)}: {directory}\n')
        click.echo(f'Profile: {llm_profile.name}')
        click.echo(f'Total files: {len(analysis["files"])}')
        click.echo(f'Total tokens: {total_tokens:,}')
        click.echo()

        # Context fit analysis
        optimal = llm_profile.optimal_tokens
        max_tokens = llm_profile.max_tokens

        if total_tokens <= optimal:
            echo_success(f'Fits within optimal limit ({total_tokens:,} / {optimal:,})')
        elif total_tokens <= max_tokens:
            echo_warning(f'Fits but exceeds optimal ({total_tokens:,} / {optimal:,})')
            echo_info(f'Consider focusing on specific files')
        else:
            echo_error(f'Exceeds max tokens ({total_tokens:,} / {max_tokens:,})')
            click.echo(f'\nLargest files:')
            file_tokens.sort(key=lambda x: -x[1])
            for path, tokens in file_tokens[:10]:
                click.echo(f'  {tokens:,} tokens - {path}')

    except Exception as e:
        echo_error(str(e))
        sys.exit(1)


def main():
    """Entry point for CLI."""
    cli()


if __name__ == '__main__':
    main()
