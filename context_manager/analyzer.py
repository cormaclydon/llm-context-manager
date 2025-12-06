# context_manager/analyzer.py
"""
Code analysis and prioritization module.
Analyzes codebase to determine file importance and structure.
"""

import os
from pathlib import Path
from typing import Optional

# Tree-sitter imports with graceful fallback
try:
    from tree_sitter import Language, Parser
    import tree_sitter_python as tspython
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


class CodebaseAnalyzer:
    """
    Analyzes codebase to determine file importance and structure.
    """

    # Default patterns to ignore
    DEFAULT_IGNORE_PATTERNS = [
        '.git', '__pycache__', 'node_modules', '.venv',
        'venv', 'dist', 'build', '.next', '.pytest_cache',
        '.mypy_cache', '.tox', 'eggs', '*.egg-info',
        '.coverage', 'htmlcov', '.hypothesis', '.nox',
        '.cargo', 'target', 'vendor', '.bundle'
    ]

    # File extensions to include
    CODE_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs',
        '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.rb',
        '.php', '.swift', '.kt', '.scala', '.vue', '.svelte',
        '.yaml', '.yml', '.json', '.toml', '.ini', '.cfg',
        '.md', '.rst', '.txt', '.sh', '.bash', '.zsh',
        '.sql', '.graphql', '.proto', '.html', '.css', '.scss'
    }

    def __init__(self, root_dir: str, ignore_patterns: Optional[list] = None):
        """
        Initialize the analyzer.

        Args:
            root_dir: Root directory of the codebase to analyze
            ignore_patterns: Additional patterns to ignore
        """
        self.root_dir = Path(root_dir).resolve()
        self.ignore_patterns = self.DEFAULT_IGNORE_PATTERNS.copy()
        if ignore_patterns:
            self.ignore_patterns.extend(ignore_patterns)

        # Initialize tree-sitter parser if available
        self.parser = None
        if TREE_SITTER_AVAILABLE:
            try:
                PY_LANGUAGE = Language(tspython.language())
                self.parser = Parser(PY_LANGUAGE)
            except Exception:
                pass

    def analyze(self) -> dict:
        """
        Analyze entire codebase and return prioritized file list.

        Returns:
            {
                'files': [
                    {
                        'path': 'src/main.py',
                        'absolute_path': '/full/path/src/main.py',
                        'priority': 100,
                        'type': 'entry_point',
                        'size': 1024,
                        'extension': '.py',
                        'imports': ['module1', 'module2'],
                        'functions': ['main', 'helper'],
                        'classes': ['App']
                    },
                    ...
                ],
                'structure': {
                    'src/': {...},
                    'tests/': {...}
                },
                'summary': {
                    'total_files': 42,
                    'total_size': 102400,
                    'by_type': {'source': 30, 'test': 10, ...}
                }
            }
        """
        files = []

        for file_path in self._get_all_files():
            analysis = self._analyze_file(file_path)
            if analysis:
                files.append(analysis)

        # Sort by priority (highest first)
        files.sort(key=lambda x: x['priority'], reverse=True)

        # Build summary statistics
        summary = self._build_summary(files)

        return {
            'files': files,
            'structure': self._build_tree_structure(files),
            'summary': summary
        }

    def _get_all_files(self) -> list:
        """
        Recursively get all relevant files, respecting ignore patterns.
        """
        all_files = []

        for root, dirs, files in os.walk(self.root_dir):
            # Remove ignored directories in-place
            dirs[:] = [d for d in dirs if not self._should_ignore_dir(d)]

            for file in files:
                file_path = Path(root) / file
                if self._is_relevant_file(file_path):
                    all_files.append(file_path)

        return all_files

    def _should_ignore_dir(self, dirname: str) -> bool:
        """Check if directory should be ignored."""
        dirname_lower = dirname.lower()
        for pattern in self.ignore_patterns:
            # Handle glob patterns like *.egg-info
            if pattern.startswith('*'):
                if dirname_lower.endswith(pattern[1:].lower()):
                    return True
            # Exact match or match with dot prefix (hidden dirs)
            elif dirname_lower == pattern.lower() or dirname_lower == '.' + pattern.lower():
                return True
        return False

    def _is_relevant_file(self, file_path: Path) -> bool:
        """Check if file should be included in analysis."""
        # Check extension
        if file_path.suffix.lower() not in self.CODE_EXTENSIONS:
            # Also include files without extension that might be scripts
            if file_path.suffix:
                return False

        # Check if any path component matches ignore patterns
        # Only match exact component names, not substrings in the full path
        try:
            relative = file_path.relative_to(self.root_dir)
            parts = relative.parts
        except ValueError:
            parts = file_path.parts

        for part in parts:
            part_lower = part.lower()
            for pattern in self.ignore_patterns:
                pattern_lower = pattern.lower()
                # Handle glob patterns like *.egg-info
                if pattern.startswith('*'):
                    if part_lower.endswith(pattern_lower[1:]):
                        return False
                # Exact match or hidden file/dir match
                elif part_lower == pattern_lower or part_lower == '.' + pattern_lower:
                    return False

        return True

    def _analyze_file(self, file_path: Path) -> Optional[dict]:
        """
        Analyze single file to extract metadata.
        """
        try:
            content = file_path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, PermissionError, OSError):
            return None  # Skip binary/unreadable files

        try:
            relative_path = file_path.relative_to(self.root_dir)
        except ValueError:
            relative_path = file_path

        # Determine file type and priority
        priority = self._calculate_priority(file_path, content)
        file_type = self._determine_file_type(file_path, content)

        # Extract code structure (for Python files)
        structure = {}
        if file_path.suffix == '.py' and self.parser:
            structure = self._extract_python_structure(content)
        elif file_path.suffix in ['.js', '.ts', '.jsx', '.tsx']:
            structure = self._extract_js_structure(content)

        return {
            'path': str(relative_path).replace('\\', '/'),
            'absolute_path': str(file_path),
            'priority': priority,
            'type': file_type,
            'size': len(content),
            'extension': file_path.suffix,
            **structure
        }

    def _calculate_priority(self, file_path: Path, content: str) -> int:
        """
        Calculate file priority (0-100).

        Priority rules:
        - Entry points (main.py, __main__.py, app.py): 100
        - Package init files with exports: 90
        - Core modules (src/, lib/): 80
        - API/Routes: 75
        - Models/Schemas: 70
        - Utilities: 60
        - Tests: 40
        - Config files: 30
        - Documentation: 20
        - Other: 10
        """
        filename = file_path.name.lower()

        # Get relative path parts within the project (not absolute path)
        try:
            relative_path = file_path.relative_to(self.root_dir)
            rel_parts = [p.lower() for p in relative_path.parts]
            # Parent dir within the project (not the temp directory name)
            parent_dir = rel_parts[-2] if len(rel_parts) > 1 else ''
        except ValueError:
            rel_parts = [p.lower() for p in file_path.parts]
            parent_dir = file_path.parent.name.lower()

        # Entry points - highest priority
        entry_points = ['main.py', '__main__.py', 'app.py', 'index.js', 'index.ts',
                       'main.go', 'main.rs', 'server.py', 'server.js', 'server.ts']
        if filename in entry_points:
            return 100

        # Package init with exports
        if filename == '__init__.py':
            if 'import' in content or '__all__' in content:
                return 90
            return 50

        # CLI entry points
        if filename == 'cli.py' or 'cli' in filename:
            return 95

        # Core source directories
        core_dirs = ['src', 'lib', 'core', 'app', 'pkg', 'internal']
        if parent_dir in core_dirs or any(d in rel_parts for d in core_dirs):
            # Further prioritize within core
            if 'api' in filename or 'route' in filename:
                return 75
            if 'model' in filename or 'schema' in filename:
                return 70
            if 'util' in filename or 'helper' in filename:
                return 60
            return 80

        # Tests - moderate priority (check filename patterns and specific directory names)
        if filename.startswith('test_') or filename.endswith('_test.py'):
            return 40
        if parent_dir in ['test', 'tests'] or 'tests' in rel_parts:
            return 40

        # Config files
        config_extensions = ['.yaml', '.yml', '.json', '.toml', '.ini', '.cfg', '.env']
        config_names = ['config', 'settings', 'setup.py', 'setup.cfg', 'pyproject.toml',
                       'package.json', 'tsconfig.json', 'cargo.toml', 'go.mod']
        if file_path.suffix in config_extensions or filename in config_names:
            # Setup files slightly higher
            if filename in ['setup.py', 'pyproject.toml', 'package.json']:
                return 35
            return 30

        # Documentation
        if file_path.suffix in ['.md', '.rst', '.txt']:
            if filename.lower() == 'readme.md':
                return 25
            return 20

        # Examples/samples
        if parent_dir in ['example', 'examples', 'sample', 'samples']:
            return 15

        return 10

    def _determine_file_type(self, file_path: Path, content: str) -> str:
        """Categorize file type."""
        filename = file_path.name.lower()

        # Get relative path parts within the project (not absolute path)
        try:
            relative_path = file_path.relative_to(self.root_dir)
            rel_parts = [p.lower() for p in relative_path.parts]
            parent_dir = rel_parts[-2] if len(rel_parts) > 1 else ''
        except ValueError:
            rel_parts = []
            parent_dir = file_path.parent.name.lower()

        # Entry points
        if filename in ['main.py', 'app.py', '__main__.py', 'index.js', 'index.ts',
                       'main.go', 'main.rs', 'server.py', 'cli.py']:
            return 'entry_point'

        # Tests (check filename patterns and specific directory names)
        if filename.startswith('test_') or filename.endswith('_test.py'):
            return 'test'
        if parent_dir in ['test', 'tests'] or 'tests' in rel_parts:
            return 'test'

        # Configuration
        if file_path.suffix in ['.yaml', '.yml', '.json', '.toml', '.ini', '.cfg']:
            return 'config'
        if filename in ['setup.py', 'setup.cfg', 'pyproject.toml', 'package.json']:
            return 'config'

        # Documentation
        if file_path.suffix in ['.md', '.rst', '.txt']:
            return 'documentation'

        # Examples
        if parent_dir in ['example', 'examples', 'sample', 'samples']:
            return 'example'

        return 'source'

    def _extract_python_structure(self, content: str) -> dict:
        """
        Use tree-sitter to extract imports, functions, classes from Python.
        """
        if not self.parser:
            return self._extract_python_structure_regex(content)

        try:
            tree = self.parser.parse(bytes(content, 'utf8'))
            root = tree.root_node

            imports = []
            functions = []
            classes = []

            def walk_tree(node, depth=0):
                # Only process top-level definitions (depth 0 or 1)
                if node.type == 'import_statement' or node.type == 'import_from_statement':
                    imports.append(content[node.start_byte:node.end_byte])
                elif node.type == 'function_definition' and depth <= 1:
                    func_name = node.child_by_field_name('name')
                    if func_name:
                        functions.append(content[func_name.start_byte:func_name.end_byte])
                elif node.type == 'class_definition' and depth <= 1:
                    class_name = node.child_by_field_name('name')
                    if class_name:
                        classes.append(content[class_name.start_byte:class_name.end_byte])

                for child in node.children:
                    walk_tree(child, depth + 1)

            walk_tree(root)

            return {
                'imports': imports,
                'functions': functions,
                'classes': classes
            }
        except Exception:
            return self._extract_python_structure_regex(content)

    def _extract_python_structure_regex(self, content: str) -> dict:
        """Fallback regex-based extraction for Python."""
        import re

        imports = re.findall(r'^(?:from\s+\S+\s+)?import\s+.+$', content, re.MULTILINE)
        functions = re.findall(r'^def\s+(\w+)\s*\(', content, re.MULTILINE)
        classes = re.findall(r'^class\s+(\w+)\s*[:\(]', content, re.MULTILINE)

        return {
            'imports': imports[:20],  # Limit to first 20
            'functions': functions,
            'classes': classes
        }

    def _extract_js_structure(self, content: str) -> dict:
        """Extract structure from JavaScript/TypeScript files."""
        import re

        # Extract imports
        imports = re.findall(r'^import\s+.+$', content, re.MULTILINE)
        imports.extend(re.findall(r'^const\s+.+\s*=\s*require\(.+\)', content, re.MULTILINE))

        # Extract functions
        functions = re.findall(r'(?:function|const|let|var)\s+(\w+)\s*(?:=\s*(?:async\s*)?\(|=\s*function|\()', content)
        functions.extend(re.findall(r'(?:async\s+)?(\w+)\s*\([^)]*\)\s*{', content))

        # Extract classes
        classes = re.findall(r'class\s+(\w+)', content)

        # Deduplicate
        functions = list(dict.fromkeys(functions))

        return {
            'imports': imports[:20],
            'functions': functions,
            'classes': classes
        }

    def _build_tree_structure(self, files: list) -> dict:
        """Build hierarchical directory structure."""
        tree = {}

        for file_info in files:
            path_str = file_info['path']
            if not path_str:
                continue

            parts = Path(path_str).parts
            if not parts:
                continue

            current = tree

            # Navigate/create directories
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                # Ensure we don't overwrite a file entry with a dict
                if isinstance(current[part], dict) and 'priority' not in current[part]:
                    current = current[part]
                else:
                    # Edge case: directory name conflicts with file
                    break

            # Store just filename at leaf
            if parts:
                current[parts[-1]] = {
                    'priority': file_info['priority'],
                    'type': file_info['type']
                }

        return tree

    def _build_summary(self, files: list) -> dict:
        """Build summary statistics."""
        by_type = {}
        by_extension = {}
        total_size = 0

        for f in files:
            # Count by type
            file_type = f['type']
            by_type[file_type] = by_type.get(file_type, 0) + 1

            # Count by extension
            ext = f['extension'] or 'no_extension'
            by_extension[ext] = by_extension.get(ext, 0) + 1

            # Sum size
            total_size += f['size']

        return {
            'total_files': len(files),
            'total_size': total_size,
            'by_type': by_type,
            'by_extension': by_extension
        }
