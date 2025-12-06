# context_manager/packager.py
"""
Context packaging logic for LLM-optimized output.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import html

from .models import LLMProfile
from .tokenizers import TokenCounter


class ContextPackager:
    """
    Package codebase into LLM-optimized context.
    """

    def __init__(self, profile: LLMProfile):
        """
        Initialize packager with LLM profile.

        Args:
            profile: LLMProfile defining output format and limits
        """
        self.profile = profile
        self.token_counter = TokenCounter(profile.tokenizer_type)

    def package(
        self,
        analysis: Dict[str, Any],
        output_path: Optional[str] = None,
        focus_files: Optional[List[str]] = None
    ) -> str:
        """
        Create packaged context from codebase analysis.

        Args:
            analysis: Output from CodebaseAnalyzer.analyze()
            output_path: Where to save (optional)
            focus_files: List of specific files to prioritize (optional)

        Returns:
            Packaged context as string
        """
        # Apply focus files if specified
        if focus_files:
            analysis = self._apply_focus(analysis, focus_files)

        # Build context based on output format
        if self.profile.output_format == 'xml':
            context = self._build_xml_context(analysis)
        elif self.profile.output_format == 'markdown':
            context = self._build_markdown_context(analysis)
        else:
            context = self._build_plain_context(analysis)

        # Save if output path provided
        if output_path:
            Path(output_path).write_text(context, encoding='utf-8')

        return context

    def _apply_focus(self, analysis: Dict[str, Any], focus_files: List[str]) -> Dict[str, Any]:
        """Prioritize specific files in the analysis."""
        files = analysis['files'].copy()

        # Boost priority of focus files
        focus_set = set(focus_files)
        for file_info in files:
            if file_info['path'] in focus_set or any(
                f in file_info['path'] for f in focus_files
            ):
                file_info['priority'] = 150  # Higher than max normal priority

        # Re-sort by priority
        files.sort(key=lambda x: x['priority'], reverse=True)

        return {
            **analysis,
            'files': files
        }

    def _build_xml_context(self, analysis: Dict[str, Any]) -> str:
        """Build XML-formatted context."""
        xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_parts.append('<codebase>')

        # Add metadata
        xml_parts.append('  <metadata>')
        xml_parts.append(f'    <generated>{datetime.now().isoformat()}</generated>')
        xml_parts.append(f'    <profile>{self.profile.name}</profile>')
        xml_parts.append(f'    <total_files>{len(analysis["files"])}</total_files>')
        if 'summary' in analysis:
            xml_parts.append(f'    <total_size>{analysis["summary"].get("total_size", 0)}</total_size>')
        xml_parts.append('  </metadata>')

        # Add file tree
        if self.profile.include_tree:
            xml_parts.append('  <structure>')
            xml_parts.append(self._tree_to_xml(analysis['structure'], indent=4))
            xml_parts.append('  </structure>')

        # Add files in priority order
        xml_parts.append('  <files>')

        # Calculate initial overhead
        header = '\n'.join(xml_parts) + '\n  </files>\n</codebase>'
        current_tokens = self.token_counter.count(header)

        files_included = 0
        files_truncated = 0

        for file_info in analysis['files']:
            try:
                file_content = Path(file_info['absolute_path']).read_text(
                    encoding='utf-8', errors='ignore'
                )
            except (OSError, IOError):
                continue

            # Escape XML special characters if not using CDATA
            # CDATA handles most cases but we still escape ]]>
            safe_content = file_content.replace(']]>', ']]]]><![CDATA[>')

            file_xml = self._format_file_xml(file_info, safe_content)
            file_tokens = self.token_counter.count(file_xml)

            # Check if adding this file exceeds limit
            if current_tokens + file_tokens > self.profile.optimal_tokens:
                files_truncated = len(analysis['files']) - files_included
                xml_parts.append(
                    f'    <!-- Truncated: {files_truncated} files omitted '
                    f'to stay within {self.profile.optimal_tokens:,} token limit -->'
                )
                break

            xml_parts.append(file_xml)
            current_tokens += file_tokens
            files_included += 1

        xml_parts.append('  </files>')
        xml_parts.append('</codebase>')

        return '\n'.join(xml_parts)

    def _format_file_xml(self, file_info: Dict[str, Any], content: str) -> str:
        """Format a single file as XML."""
        attrs = [
            f'path="{html.escape(file_info["path"])}"',
            f'priority="{file_info["priority"]}"',
            f'type="{file_info["type"]}"'
        ]

        # Add optional attributes
        if file_info.get('functions'):
            attrs.append(f'functions="{len(file_info["functions"])}"')
        if file_info.get('classes'):
            attrs.append(f'classes="{len(file_info["classes"])}"')

        attr_str = ' '.join(attrs)
        return f'    <file {attr_str}>\n<![CDATA[{content}]]>\n    </file>'

    def _build_markdown_context(self, analysis: Dict[str, Any]) -> str:
        """Build Markdown-formatted context."""
        md_parts = ['# Codebase Context\n']

        # Add metadata
        md_parts.append('## Metadata\n')
        md_parts.append(f'- **Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        md_parts.append(f'- **Profile**: {self.profile.name}')
        md_parts.append(f'- **Total Files**: {len(analysis["files"])}')
        md_parts.append(f'- **Token Limit**: {self.profile.optimal_tokens:,}')

        if 'summary' in analysis:
            summary = analysis['summary']
            md_parts.append(f'- **Total Size**: {summary.get("total_size", 0):,} bytes')
            if summary.get('by_type'):
                type_str = ', '.join(f'{k}: {v}' for k, v in summary['by_type'].items())
                md_parts.append(f'- **By Type**: {type_str}')

        md_parts.append('')

        # Add file tree
        if self.profile.include_tree:
            md_parts.append('## File Structure\n')
            md_parts.append('```')
            md_parts.append(self._tree_to_text(analysis['structure']))
            md_parts.append('```\n')

        # Add files
        md_parts.append('## Files\n')

        # Calculate overhead
        header = '\n'.join(md_parts)
        current_tokens = self.token_counter.count(header)

        files_included = 0

        for file_info in analysis['files']:
            try:
                file_content = Path(file_info['absolute_path']).read_text(
                    encoding='utf-8', errors='ignore'
                )
            except (OSError, IOError):
                continue

            file_md = self._format_file_markdown(file_info, file_content)
            file_tokens = self.token_counter.count(file_md)

            if current_tokens + file_tokens > self.profile.optimal_tokens:
                remaining = len(analysis['files']) - files_included
                md_parts.append(f'\n---\n\n*Truncated: {remaining} files omitted to stay within token limit*')
                break

            md_parts.append(file_md)
            current_tokens += file_tokens
            files_included += 1

        return '\n'.join(md_parts)

    def _format_file_markdown(self, file_info: Dict[str, Any], content: str) -> str:
        """Format a single file as Markdown."""
        lines = [f'### {file_info["path"]}']
        lines.append(f'*Priority: {file_info["priority"]} | Type: {file_info["type"]}*\n')

        # Detect language for syntax highlighting
        extension = Path(file_info['path']).suffix.lstrip('.')
        lang_map = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'jsx': 'jsx',
            'tsx': 'tsx',
            'rb': 'ruby',
            'yml': 'yaml',
            'sh': 'bash',
            'md': 'markdown',
        }
        lang = lang_map.get(extension, extension)

        lines.append(f'```{lang}')
        lines.append(content)
        lines.append('```\n')

        return '\n'.join(lines)

    def _build_plain_context(self, analysis: Dict[str, Any]) -> str:
        """Build plain text context."""
        parts = ['=' * 60]
        parts.append('CODEBASE CONTEXT')
        parts.append('=' * 60)
        parts.append('')

        # Add metadata
        parts.append(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        parts.append(f'Profile: {self.profile.name}')
        parts.append(f'Total Files: {len(analysis["files"])}')
        parts.append(f'Token Limit: {self.profile.optimal_tokens:,}')
        parts.append('')

        # Add file tree
        if self.profile.include_tree:
            parts.append('-' * 40)
            parts.append('FILE STRUCTURE')
            parts.append('-' * 40)
            parts.append(self._tree_to_text(analysis['structure']))
            parts.append('')

        # Add files
        parts.append('-' * 40)
        parts.append('FILES')
        parts.append('-' * 40)
        parts.append('')

        header = '\n'.join(parts)
        current_tokens = self.token_counter.count(header)

        files_included = 0

        for file_info in analysis['files']:
            try:
                file_content = Path(file_info['absolute_path']).read_text(
                    encoding='utf-8', errors='ignore'
                )
            except (OSError, IOError):
                continue

            file_plain = self._format_file_plain(file_info, file_content)
            file_tokens = self.token_counter.count(file_plain)

            if current_tokens + file_tokens > self.profile.optimal_tokens:
                remaining = len(analysis['files']) - files_included
                parts.append(f'\n[Truncated: {remaining} files omitted]')
                break

            parts.append(file_plain)
            current_tokens += file_tokens
            files_included += 1

        return '\n'.join(parts)

    def _format_file_plain(self, file_info: Dict[str, Any], content: str) -> str:
        """Format a single file as plain text."""
        lines = [
            f'\n--- {file_info["path"]} ---',
            f'Priority: {file_info["priority"]} | Type: {file_info["type"]}',
            '-' * 40,
            content,
            f'--- End of {file_info["path"]} ---\n'
        ]
        return '\n'.join(lines)

    def _tree_to_xml(self, tree: Dict[str, Any], indent: int = 0) -> str:
        """Convert file tree to XML."""
        xml_lines = []
        spaces = ' ' * indent

        for name, content in sorted(tree.items()):
            if isinstance(content, dict) and 'priority' not in content:
                # Directory
                xml_lines.append(f'{spaces}<directory name="{html.escape(name)}">')
                xml_lines.append(self._tree_to_xml(content, indent + 2))
                xml_lines.append(f'{spaces}</directory>')
            else:
                # File
                if isinstance(content, dict):
                    attrs = f'name="{html.escape(name)}" priority="{content.get("priority", 0)}"'
                else:
                    attrs = f'name="{html.escape(name)}"'
                xml_lines.append(f'{spaces}<file {attrs} />')

        return '\n'.join(xml_lines)

    def _tree_to_text(self, tree: Dict[str, Any], prefix: str = '') -> str:
        """Convert file tree to plain text tree representation."""
        lines = []
        items = sorted(tree.items())

        for i, (name, content) in enumerate(items):
            is_last = i == len(items) - 1
            connector = '└── ' if is_last else '├── '

            if isinstance(content, dict) and 'priority' not in content:
                # Directory
                lines.append(f'{prefix}{connector}{name}/')
                extension = '    ' if is_last else '│   '
                subtree = self._tree_to_text(content, prefix + extension)
                if subtree:
                    lines.append(subtree)
            else:
                # File
                lines.append(f'{prefix}{connector}{name}')

        return '\n'.join(lines)

    def get_stats(self, context: str) -> Dict[str, Any]:
        """
        Get statistics about the packaged context.

        Args:
            context: The packaged context string

        Returns:
            Dictionary with token count, utilization, etc.
        """
        token_count = self.token_counter.count(context)

        return {
            'token_count': token_count,
            'max_tokens': self.profile.max_tokens,
            'optimal_tokens': self.profile.optimal_tokens,
            'utilization': token_count / self.profile.optimal_tokens * 100,
            'character_count': len(context),
            'line_count': context.count('\n') + 1
        }


class IncrementalPackager(ContextPackager):
    """
    Packager that supports incremental updates for changed files.
    """

    def __init__(self, profile: LLMProfile):
        super().__init__(profile)
        self._cache: Dict[str, str] = {}
        self._cache_tokens: Dict[str, int] = {}

    def package_incremental(
        self,
        analysis: Dict[str, Any],
        changed_files: List[str],
        output_path: Optional[str] = None
    ) -> str:
        """
        Package with incremental update for changed files only.

        Args:
            analysis: Output from CodebaseAnalyzer.analyze()
            changed_files: List of file paths that changed
            output_path: Where to save (optional)

        Returns:
            Packaged context as string
        """
        # Update cache for changed files
        for file_info in analysis['files']:
            path = file_info['path']
            if path in changed_files or path not in self._cache:
                try:
                    content = Path(file_info['absolute_path']).read_text(
                        encoding='utf-8', errors='ignore'
                    )
                    self._cache[path] = content
                    self._cache_tokens[path] = self.token_counter.count(content)
                except (OSError, IOError):
                    pass

        # Use regular packaging with cached content
        return self.package(analysis, output_path)

    def clear_cache(self):
        """Clear the file content cache."""
        self._cache.clear()
        self._cache_tokens.clear()
