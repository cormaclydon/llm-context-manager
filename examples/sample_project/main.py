#!/usr/bin/env python
"""
Sample Project - Main Entry Point

This is an example project to demonstrate the LLM Context Manager.
"""

from src.app import Application
from src.utils import format_greeting


def main():
    """Run the sample application."""
    app = Application(name="Sample App")

    # Display greeting
    greeting = format_greeting("World")
    print(greeting)

    # Run the application
    app.run()

    # Process some data
    result = app.process_data([1, 2, 3, 4, 5])
    print(f"Processed result: {result}")

    app.stop()


if __name__ == "__main__":
    main()
