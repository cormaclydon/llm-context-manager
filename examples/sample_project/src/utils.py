"""Utility functions for the sample project."""

from typing import List


def format_greeting(name: str) -> str:
    """
    Format a greeting message.

    Args:
        name: Name to greet

    Returns:
        Formatted greeting string
    """
    return f"Hello, {name}!"


def calculate_sum(numbers: List[int]) -> int:
    """
    Calculate the sum of a list of numbers.

    Args:
        numbers: List of integers

    Returns:
        Sum of all numbers
    """
    return sum(numbers)


def format_output(data: dict) -> str:
    """
    Format dictionary data for display.

    Args:
        data: Dictionary to format

    Returns:
        Formatted string representation
    """
    lines = [f"  {key}: {value}" for key, value in data.items()]
    return "{\n" + "\n".join(lines) + "\n}"
