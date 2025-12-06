# LLM Context Manager

A developer tool that intelligently packages codebases into optimal context windows for different LLMs. Automatically prioritizes important files, chunks code appropriately for each model's context limits, and provides watch mode for real-time updates as you code.

## Features

- **Smart Prioritization**: Ranks files by importance (entry points > core logic > tests > configs)
- **Model-Specific Optimization**: Adjusts chunking for different context windows (Claude, GPT-4, Qwen, local models)
- **Watch Mode**: Auto-regenerates context when files change
- **Multiple Output Formats**: XML, Markdown, or plain text
- **Token Counting**: Accurate estimates for each model type using tiktoken
- **Incremental Updates**: Only re-processes changed files in watch mode

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/llm-context-manager
cd llm-context-manager

# Install with pip (recommended)
pip install -e .

# Or install with all optional dependencies
pip install -e ".[all]"

# Or install specific extras
pip install -e ".[watch]"     # For watch mode
pip install -e ".[parsing]"   # For better Python analysis
```

### Requirements

- Python 3.11+
- click >= 8.0.0
- tiktoken >= 0.5.0
- pyyaml >= 6.0.0
- watchdog >= 3.0.0 (optional, for watch mode)
- tree-sitter >= 0.21.0 (optional, for better code analysis)

## Quick Start

```bash
# Pack current directory with default Claude profile
llm-context pack

# Use a specific profile and output file
llm-context pack ./my-project -p gpt4 -o context.xml

# Watch mode (auto-regenerate on file changes)
llm-context pack --watch

# List available profiles
llm-context profiles

# Analyze codebase structure
llm-context analyze ./my-project

# Count tokens in a file
llm-context tokens ./src/main.py
```

## CLI Commands

### `pack` - Package codebase into context

```bash
llm-context pack [DIRECTORY] [OPTIONS]

Options:
  -p, --profile TEXT     LLM profile (default: claude-sonnet)
  -o, --output TEXT      Output file path
  -f, --format TEXT      Output format: xml, markdown, plain
  -w, --watch            Watch mode - auto-regenerate on changes
  -F, --focus TEXT       Focus on specific files (can repeat)
  -i, --ignore TEXT      Additional patterns to ignore
  -t, --max-tokens INT   Override max tokens from profile
  --no-tree              Exclude file tree from output
  -v, --verbose          Verbose output
  -q, --quiet            Minimal output
```

### `profiles` - List available profiles

```bash
llm-context profiles [-v]
```

### `analyze` - Analyze codebase without packaging

```bash
llm-context analyze [DIRECTORY] [OPTIONS]

Options:
  -n, --top INT          Number of top files to show (default: 15)
  -t, --type TEXT        Filter by file type
  --json                 Output as JSON
```

### `tokens` - Count tokens in a file

```bash
llm-context tokens FILE_PATH [-p PROFILE]
```

### `estimate` - Estimate tokens for a codebase

```bash
llm-context estimate [DIRECTORY] [-p PROFILE]
```

### `create-profile` - Create custom profile

```bash
llm-context create-profile -n NAME -t MAX_TOKENS [OPTIONS]
```

## Available Profiles

| Profile | Model | Max Tokens | Optimal | Format |
|---------|-------|------------|---------|--------|
| `claude-sonnet` | Claude Sonnet 4 | 200K | 160K | XML |
| `claude-opus` | Claude Opus 4 | 200K | 160K | XML |
| `claude-haiku` | Claude Haiku 3.5 | 200K | 160K | XML |
| `gpt4` | GPT-4 Turbo | 128K | 100K | XML |
| `gpt4o` | GPT-4o | 128K | 100K | XML |
| `gpt4o-mini` | GPT-4o Mini | 128K | 100K | Markdown |
| `qwen` | Qwen 2.5 Coder | 32K | 28K | Markdown |
| `qwen-long` | Qwen 2.5 32B | 128K | 100K | Markdown |
| `llama` | Llama 3.1 70B | 128K | 100K | Markdown |
| `mistral` | Mistral Large | 32K | 28K | Markdown |
| `deepseek` | DeepSeek Coder V2 | 128K | 100K | Markdown |
| `gemini` | Gemini 1.5 Pro | 1M | 800K | XML |
| `local-small` | Local 4K | 4K | 3.5K | Plain |
| `local-medium` | Local 8K | 8K | 7K | Markdown |
| `local-large` | Local 32K | 32K | 28K | Markdown |

## Python API

```python
from context_manager import (
    CodebaseAnalyzer,
    ContextPackager,
    LLMProfile,
    pack,
)

# Quick one-liner
context = pack("./my-project", profile="claude-sonnet", output="context.xml")

# Or with more control
profile = LLMProfile.load("gpt4")
analyzer = CodebaseAnalyzer("./my-project")
analysis = analyzer.analyze()

print(f"Found {len(analysis['files'])} files")
print(f"Top file: {analysis['files'][0]['path']}")

packager = ContextPackager(profile)
context = packager.package(analysis, "output.xml")
stats = packager.get_stats(context)
print(f"Token count: {stats['token_count']:,}")
```

## File Priority System

Files are automatically prioritized (0-100):

| Priority | Category | Examples |
|----------|----------|----------|
| 100 | Entry points | `main.py`, `app.py`, `index.js`, `cli.py` |
| 90 | Package init | `__init__.py` with exports |
| 80 | Core source | Files in `src/`, `lib/`, `core/` |
| 75 | API/Routes | `api.py`, `routes.py` |
| 70 | Models/Schemas | `models.py`, `schema.py` |
| 60 | Utilities | `utils.py`, `helpers.py` |
| 40 | Tests | `test_*.py`, files in `tests/` |
| 35 | Setup files | `setup.py`, `package.json` |
| 30 | Config | `*.yaml`, `*.json`, `*.toml` |
| 25 | README | `README.md` |
| 20 | Documentation | Other `.md`, `.rst` files |
| 15 | Examples | Files in `examples/` |
| 10 | Other | Everything else |

## Custom Profiles

Create a custom profile YAML:

```yaml
# profiles/my-model.yaml
name: my-custom-model
max_tokens: 16000
optimal_tokens: 14000
tokenizer_type: gpt2
chunking_strategy: file
include_tree: true
output_format: markdown
description: My custom local model
```

Or create via CLI:

```bash
llm-context create-profile -n my-model -t 16000 -f markdown
```

## Output Formats

### XML (recommended for Claude)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<codebase>
  <metadata>
    <generated>2024-01-15T10:30:00</generated>
    <profile>claude-sonnet-4</profile>
  </metadata>
  <structure>
    <directory name="src">
      <file name="main.py" priority="100" />
    </directory>
  </structure>
  <files>
    <file path="src/main.py" priority="100" type="entry_point">
<![CDATA[
def main():
    print("Hello, World!")
]]>
    </file>
  </files>
</codebase>
```

### Markdown
```markdown
# Codebase Context

## Metadata
- **Profile**: gpt-4-turbo
- **Total Files**: 42
- **Token Limit**: 100,000

## File Structure
```
├── src/
│   ├── main.py
│   └── utils.py
└── tests/
```

## Files

### src/main.py
*Priority: 100 | Type: entry_point*

\```python
def main():
    print("Hello, World!")
\```
```

## License

MIT License - see LICENSE file for details.
