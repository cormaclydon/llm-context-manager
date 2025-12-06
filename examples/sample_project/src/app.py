"""Application module for the sample project."""

from typing import List, Optional
from .utils import calculate_sum


class Application:
    """
    Main application class.

    Demonstrates a simple application structure for context manager testing.
    """

    def __init__(self, name: str = "App"):
        """
        Initialize the application.

        Args:
            name: Application name
        """
        self.name = name
        self.running = False
        self._data: List[int] = []

    def run(self):
        """Start the application."""
        print(f"Starting {self.name}...")
        self.running = True

    def stop(self):
        """Stop the application."""
        print(f"Stopping {self.name}...")
        self.running = False

    def process_data(self, data: List[int]) -> int:
        """
        Process a list of integers.

        Args:
            data: List of integers to process

        Returns:
            Sum of all integers
        """
        self._data = data
        return calculate_sum(data)

    @property
    def is_running(self) -> bool:
        """Check if application is running."""
        return self.running
