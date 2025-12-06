# context_manager/watcher.py
"""
File watching for live updates.
Monitors codebase for changes and auto-regenerates context.
"""

import time
import threading
from pathlib import Path
from typing import Callable, List, Optional, Set
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object
    FileSystemEvent = None


class CodebaseWatcher(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """
    Watch codebase for changes and auto-regenerate context.
    """

    # Patterns to ignore
    DEFAULT_IGNORE_PATTERNS = [
        '.git/', '__pycache__/', '.pyc', '.swp', '.swo',
        '.tmp', 'node_modules/', '.next/', '.pytest_cache/',
        '.mypy_cache/', '.coverage', '~', '.DS_Store',
        'Thumbs.db', '.venv/', 'venv/', 'dist/', 'build/',
        '.egg-info/', '*.egg', '.tox/', '.nox/'
    ]

    # Extensions to watch
    WATCH_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs',
        '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.rb',
        '.php', '.swift', '.kt', '.scala', '.vue', '.svelte',
        '.yaml', '.yml', '.json', '.toml', '.md', '.txt',
        '.sh', '.bash', '.sql', '.graphql', '.html', '.css'
    }

    def __init__(
        self,
        root_dir: str,
        callback: Callable[[List[str]], None],
        debounce_seconds: float = 2.0,
        ignore_patterns: Optional[List[str]] = None
    ):
        """
        Initialize the watcher.

        Args:
            root_dir: Directory to watch
            callback: Function to call when changes detected
            debounce_seconds: Minimum time between callbacks
            ignore_patterns: Additional patterns to ignore
        """
        if WATCHDOG_AVAILABLE:
            super().__init__()

        self.root_dir = Path(root_dir).resolve()
        self.callback = callback
        self.debounce_seconds = debounce_seconds

        self.ignore_patterns = self.DEFAULT_IGNORE_PATTERNS.copy()
        if ignore_patterns:
            self.ignore_patterns.extend(ignore_patterns)

        self.last_trigger = 0.0
        self.pending_changes: Set[str] = set()
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None

    def on_modified(self, event: 'FileSystemEvent'):
        """Handle file modification events."""
        if event.is_directory:
            return
        self._handle_change(event.src_path)

    def on_created(self, event: 'FileSystemEvent'):
        """Handle file creation events."""
        if event.is_directory:
            return
        self._handle_change(event.src_path)

    def on_deleted(self, event: 'FileSystemEvent'):
        """Handle file deletion events."""
        if event.is_directory:
            return
        self._handle_change(event.src_path)

    def on_moved(self, event: 'FileSystemEvent'):
        """Handle file move events."""
        if event.is_directory:
            return
        self._handle_change(event.src_path)
        if hasattr(event, 'dest_path'):
            self._handle_change(event.dest_path)

    def _handle_change(self, path: str):
        """Process a file change event."""
        if self._should_ignore(path):
            return

        with self._lock:
            self.pending_changes.add(path)
            self._schedule_callback()

    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        path_str = str(path)

        # Check ignore patterns
        if any(pattern in path_str for pattern in self.ignore_patterns):
            return True

        # Check extension
        ext = Path(path).suffix.lower()
        if ext and ext not in self.WATCH_EXTENSIONS:
            return True

        return False

    def _schedule_callback(self):
        """Schedule the callback with debouncing."""
        # Cancel existing timer if any
        if self._timer is not None:
            self._timer.cancel()

        # Schedule new timer
        self._timer = threading.Timer(self.debounce_seconds, self._trigger_callback)
        self._timer.start()

    def _trigger_callback(self):
        """Trigger the callback with accumulated changes."""
        with self._lock:
            if not self.pending_changes:
                return

            changes = list(self.pending_changes)
            self.pending_changes.clear()
            self.last_trigger = time.time()

        # Call callback outside lock
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f'\n[{timestamp}] Detected changes in {len(changes)} file(s)')
            self.callback(changes)
        except Exception as e:
            print(f'[ERROR] Callback failed: {e}')


def start_watch(
    root_dir: str,
    callback: Callable[[List[str]], None],
    debounce_seconds: float = 2.0
) -> Optional['Observer']:
    """
    Start watching directory for changes.

    Args:
        root_dir: Directory to watch
        callback: Function to call when changes detected
        debounce_seconds: Minimum time between callbacks

    Returns:
        Observer instance (can be stopped with observer.stop())
    """
    if not WATCHDOG_AVAILABLE:
        print('[ERROR] watchdog library not installed. Install with: pip install watchdog')
        return None

    event_handler = CodebaseWatcher(root_dir, callback, debounce_seconds)
    observer = Observer()
    observer.schedule(event_handler, root_dir, recursive=True)
    observer.start()

    print(f'[WATCH] Monitoring {root_dir} for changes...')
    print(f'[WATCH] Debounce: {debounce_seconds}s | Press Ctrl+C to stop')

    return observer


def watch_blocking(
    root_dir: str,
    callback: Callable[[List[str]], None],
    debounce_seconds: float = 2.0
):
    """
    Start watching directory for changes (blocking).

    This function blocks until Ctrl+C is pressed.

    Args:
        root_dir: Directory to watch
        callback: Function to call when changes detected
        debounce_seconds: Minimum time between callbacks
    """
    observer = start_watch(root_dir, callback, debounce_seconds)
    if observer is None:
        return

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n[WATCH] Stopping...')
        observer.stop()

    observer.join()
    print('[WATCH] Stopped')


class WatchManager:
    """
    Manager for multiple directory watchers.
    """

    def __init__(self):
        self.observers: List['Observer'] = []
        self._running = False

    def add_watch(
        self,
        root_dir: str,
        callback: Callable[[List[str]], None],
        debounce_seconds: float = 2.0
    ):
        """Add a directory to watch."""
        observer = start_watch(root_dir, callback, debounce_seconds)
        if observer:
            self.observers.append(observer)

    def stop_all(self):
        """Stop all watchers."""
        for observer in self.observers:
            observer.stop()
        for observer in self.observers:
            observer.join()
        self.observers.clear()
        print('[WATCH] All watchers stopped')

    def run_blocking(self):
        """Run all watchers (blocking until Ctrl+C)."""
        if not self.observers:
            print('[WATCH] No watchers configured')
            return

        self._running = True
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            print('\n[WATCH] Stopping all watchers...')
        finally:
            self.stop_all()


def is_watchdog_available() -> bool:
    """Check if watchdog library is available."""
    return WATCHDOG_AVAILABLE
