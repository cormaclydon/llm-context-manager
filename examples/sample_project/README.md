# Sample Project

A simple example project to demonstrate the LLM Context Manager.

## Structure

```
sample_project/
├── main.py          # Entry point
├── src/
│   ├── __init__.py  # Package init
│   ├── app.py       # Main application
│   └── utils.py     # Utility functions
├── config.yaml      # Configuration
└── README.md        # This file
```

## Usage

```bash
# Run from project directory
python main.py

# Or pack with LLM Context Manager
llm-context pack ./examples/sample_project -p claude-sonnet
```
