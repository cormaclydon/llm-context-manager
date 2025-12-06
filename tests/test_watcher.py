# tests/test_watcher.py
"""Tests for the watcher module."""

import pytest
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from context_manager.watcher import (
    CodebaseWatcher,
    start_watch,
    watch_blocking,
    WatchManager,
    is_watchdog_available,
)


class TestCodebaseWatcher:
    """Test the CodebaseWatcher class."""

    def test_init(self, tmp_path):
        """Test watcher initialization."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback)

        assert watcher.root_dir == tmp_path.resolve()
        assert watcher.callback == callback
        assert watcher.debounce_seconds == 2.0
        assert len(watcher.pending_changes) == 0

    def test_init_with_custom_debounce(self, tmp_path):
        """Test watcher with custom debounce."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback, debounce_seconds=1.0)

        assert watcher.debounce_seconds == 1.0

    def test_init_with_custom_ignore_patterns(self, tmp_path):
        """Test watcher with custom ignore patterns."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback, ignore_patterns=['custom_dir/'])

        assert 'custom_dir/' in watcher.ignore_patterns

    def test_should_ignore_pycache(self, tmp_path):
        """Test that __pycache__ is ignored."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback)

        assert watcher._should_ignore('__pycache__/file.pyc')
        assert watcher._should_ignore('/path/to/__pycache__/module.pyc')

    def test_should_ignore_git(self, tmp_path):
        """Test that .git is ignored."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback)

        assert watcher._should_ignore('.git/config')
        assert watcher._should_ignore('/path/.git/objects/123')

    def test_should_ignore_node_modules(self, tmp_path):
        """Test that node_modules is ignored."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback)

        assert watcher._should_ignore('node_modules/package/index.js')

    def test_should_not_ignore_python_files(self, tmp_path):
        """Test that Python files are not ignored."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback)

        assert not watcher._should_ignore('main.py')
        assert not watcher._should_ignore('src/app.py')

    def test_should_ignore_swap_files(self, tmp_path):
        """Test that swap files are ignored."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback)

        assert watcher._should_ignore('file.py.swp')
        assert watcher._should_ignore('file.py.swo')

    def test_should_ignore_tmp_files(self, tmp_path):
        """Test that temp files are ignored."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback)

        assert watcher._should_ignore('file.tmp')

    def test_should_ignore_by_extension(self, tmp_path):
        """Test that non-code extensions are ignored."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback)

        # Binary files should be ignored
        assert watcher._should_ignore('image.png')
        assert watcher._should_ignore('document.pdf')

    def test_handle_change_adds_to_pending(self, tmp_path):
        """Test that handling a change adds to pending set."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback, debounce_seconds=10.0)

        watcher._handle_change(str(tmp_path / 'test.py'))

        assert len(watcher.pending_changes) == 1

    def test_handle_change_ignores_filtered(self, tmp_path):
        """Test that ignored files are not added to pending."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback)

        watcher._handle_change(str(tmp_path / '__pycache__' / 'module.pyc'))

        assert len(watcher.pending_changes) == 0


class TestWatcherEvents:
    """Test watcher event handling."""

    @pytest.fixture
    def mock_event(self):
        """Create a mock file system event."""
        event = MagicMock()
        event.is_directory = False
        return event

    def test_on_modified(self, tmp_path, mock_event):
        """Test handling modified event."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback, debounce_seconds=10.0)

        mock_event.src_path = str(tmp_path / 'test.py')
        watcher.on_modified(mock_event)

        assert str(tmp_path / 'test.py') in watcher.pending_changes

    def test_on_modified_directory_ignored(self, tmp_path, mock_event):
        """Test that directory events are ignored."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback)

        mock_event.is_directory = True
        mock_event.src_path = str(tmp_path / 'subdir')
        watcher.on_modified(mock_event)

        assert len(watcher.pending_changes) == 0

    def test_on_created(self, tmp_path, mock_event):
        """Test handling created event."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback, debounce_seconds=10.0)

        mock_event.src_path = str(tmp_path / 'new_file.py')
        watcher.on_created(mock_event)

        assert str(tmp_path / 'new_file.py') in watcher.pending_changes

    def test_on_deleted(self, tmp_path, mock_event):
        """Test handling deleted event."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback, debounce_seconds=10.0)

        mock_event.src_path = str(tmp_path / 'deleted.py')
        watcher.on_deleted(mock_event)

        assert str(tmp_path / 'deleted.py') in watcher.pending_changes

    def test_on_moved(self, tmp_path, mock_event):
        """Test handling moved event."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback, debounce_seconds=10.0)

        mock_event.src_path = str(tmp_path / 'old_name.py')
        mock_event.dest_path = str(tmp_path / 'new_name.py')
        watcher.on_moved(mock_event)

        assert str(tmp_path / 'old_name.py') in watcher.pending_changes
        assert str(tmp_path / 'new_name.py') in watcher.pending_changes


class TestDebouncing:
    """Test debouncing functionality."""

    def test_debounce_triggers_callback(self, tmp_path):
        """Test that debouncing triggers callback after delay."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback, debounce_seconds=0.1)

        watcher._handle_change(str(tmp_path / 'test.py'))

        # Wait for debounce
        time.sleep(0.3)

        # Callback should have been called
        assert callback.called
        assert len(watcher.pending_changes) == 0

    def test_debounce_accumulates_changes(self, tmp_path):
        """Test that rapid changes are accumulated."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback, debounce_seconds=0.2)

        # Rapid changes
        watcher._handle_change(str(tmp_path / 'file1.py'))
        watcher._handle_change(str(tmp_path / 'file2.py'))
        watcher._handle_change(str(tmp_path / 'file3.py'))

        # Should have all pending
        assert len(watcher.pending_changes) == 3

        # Wait for debounce
        time.sleep(0.4)

        # Single callback with all files
        assert callback.call_count == 1
        called_files = callback.call_args[0][0]
        assert len(called_files) == 3


class TestStartWatch:
    """Test the start_watch function."""

    @pytest.mark.skipif(not is_watchdog_available(), reason="watchdog not available")
    def test_start_watch(self, tmp_path):
        """Test starting a watcher."""
        callback = Mock()
        observer = start_watch(str(tmp_path), callback)

        assert observer is not None
        assert observer.is_alive()

        observer.stop()
        observer.join(timeout=1)

    @pytest.mark.skipif(not is_watchdog_available(), reason="watchdog not available")
    def test_start_watch_with_debounce(self, tmp_path):
        """Test starting a watcher with custom debounce."""
        callback = Mock()
        observer = start_watch(str(tmp_path), callback, debounce_seconds=1.0)

        assert observer is not None

        observer.stop()
        observer.join(timeout=1)


class TestWatchManager:
    """Test the WatchManager class."""

    def test_init(self):
        """Test WatchManager initialization."""
        manager = WatchManager()
        assert len(manager.observers) == 0
        assert manager._running is False

    @pytest.mark.skipif(not is_watchdog_available(), reason="watchdog not available")
    def test_add_watch(self, tmp_path):
        """Test adding a watch."""
        manager = WatchManager()
        callback = Mock()

        manager.add_watch(str(tmp_path), callback)

        assert len(manager.observers) == 1

        manager.stop_all()

    @pytest.mark.skipif(not is_watchdog_available(), reason="watchdog not available")
    def test_stop_all(self, tmp_path):
        """Test stopping all watchers."""
        manager = WatchManager()
        callback = Mock()

        manager.add_watch(str(tmp_path), callback)
        manager.stop_all()

        assert len(manager.observers) == 0


class TestIsWatchdogAvailable:
    """Test the is_watchdog_available function."""

    def test_returns_bool(self):
        """Test that function returns a boolean."""
        result = is_watchdog_available()
        assert isinstance(result, bool)


class TestWatchExtensions:
    """Test that watcher respects file extensions."""

    def test_watch_extensions_include_python(self, tmp_path):
        """Test that Python files are watched."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback)

        assert '.py' in watcher.WATCH_EXTENSIONS

    def test_watch_extensions_include_javascript(self, tmp_path):
        """Test that JavaScript files are watched."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback)

        assert '.js' in watcher.WATCH_EXTENSIONS
        assert '.ts' in watcher.WATCH_EXTENSIONS
        assert '.jsx' in watcher.WATCH_EXTENSIONS
        assert '.tsx' in watcher.WATCH_EXTENSIONS

    def test_watch_extensions_include_config(self, tmp_path):
        """Test that config files are watched."""
        callback = Mock()
        watcher = CodebaseWatcher(str(tmp_path), callback)

        assert '.yaml' in watcher.WATCH_EXTENSIONS
        assert '.json' in watcher.WATCH_EXTENSIONS
        assert '.toml' in watcher.WATCH_EXTENSIONS
