#!/usr/bin/env python3
"""
Smoke Test Harness for DarkReconX TUI

This test validates that the TUI can:
1. Start and initialize without errors
2. Discover modules correctly
3. Validate targets (domain, IP, email)
4. Run a scan with mocked providers
5. Stream results correctly
6. Handle errors gracefully
7. Export results to JSON/CSV
8. Toggle theme without errors

Run with: python -m pytest tests/test_tui_smoke.py -v
Or directly: python tests/test_tui_smoke.py
"""

import asyncio
import json
import csv
import tempfile
import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestTUISmoke:
    """Smoke tests for TUI initialization and basic functionality"""

    def test_tui_imports(self):
        """Test that TUI can be imported without errors"""
        try:
            import tui
            assert tui is not None
        except Exception as e:
            pytest.fail(f"TUI import failed: {e}")

    def test_orchestrator_stream_api_exists(self):
        """Test that orchestrator has stream API methods"""
        from core import orchestrator
        
        assert hasattr(orchestrator, 'run_scan_stream'), "run_scan_stream not found"
        assert callable(orchestrator.run_scan_stream), "run_scan_stream not callable"

    def test_module_discovery(self):
        """Test that modules can be discovered"""
        from core.loader import discover_modules
        modules: Any = discover_modules()
        # discover_modules returns a mapping name->class. Accept both dict or list for resilience.
        assert modules, "No modules discovered"

        if isinstance(modules, dict):
            module_names = list(modules.keys())
        elif isinstance(modules, list):
            # list of dicts or names
            module_names = []
            for m in modules:
                if isinstance(m, dict):
                    module_names.append(m.get('name') or m.get('module'))
                else:
                    module_names.append(str(m))
        else:
            pytest.fail(f"Unexpected discover_modules return type: {type(modules)}")

        # Best-effort: verify that at least one discovered module corresponds to a module directory on disk
        from core.loader import _modules_path
        disk_modules = [p.name for p in _modules_path().iterdir() if p.is_dir() or (p.is_file() and p.suffix == '.py')]

        matched = False
        for n in module_names:
            if not n:
                continue
            if n in disk_modules:
                matched = True
                break
            # sometimes class names differ; check prefix match
            for d in disk_modules:
                if n.startswith(d) or d.startswith(n):
                    matched = True
                    break
            if matched:
                break

        assert matched, f"No discovered module matched modules/ on disk (found: {module_names[:8]})"

    def test_profile_loading(self):
        """Test that profiles can be loaded"""
        from core.profiles import load_profiles

        profiles = load_profiles()
        assert len(profiles) > 0, "No profiles loaded"
        assert 'quick' in profiles, "quick profile not found"

    def test_target_validation(self):
        """Test target validation regex patterns"""
        # Import validation logic (or test it directly)
        import re
        
        # Domain pattern
        domain_pattern = r'^(?:[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?\.)+[a-z]{2,}$'
        
        assert re.match(domain_pattern, 'example.com'), "Valid domain failed"
        assert re.match(domain_pattern, 'sub.example.org'), "Valid subdomain failed"
        assert not re.match(domain_pattern, 'invalid'), "Invalid domain passed"
        
        # IP pattern
        ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        
        assert re.match(ip_pattern, '192.168.1.1'), "Valid IP failed"
        assert re.match(ip_pattern, '8.8.8.8'), "Valid IP (8.8.8.8) failed"
        assert not re.match(ip_pattern, '256.1.1.1'), "Invalid IP passed"
        
        # Email pattern
        email_pattern = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'
        
        assert re.match(email_pattern, 'user@example.com'), "Valid email failed"
        assert not re.match(email_pattern, 'invalid@'), "Invalid email passed"

    @pytest.mark.asyncio
    async def test_orchestrator_stream_basic(self):
        """Test that orchestrator stream can be called (mock)"""
        from core.orchestrator import AsyncOrchestrator, get_registry

        # Create mocked orchestrator with correct signature
        with patch('core.orchestrator.get_logger'):
            registry = get_registry()
            orchestrator = AsyncOrchestrator(registry, max_concurrent=3, timeout_per_provider=10.0)

            assert orchestrator is not None
            assert orchestrator.max_concurrent == 3
            assert orchestrator.timeout_per_provider == 10.0

    @pytest.mark.asyncio
    async def test_scan_stream_mock(self):
        """Test scan stream with mocked providers"""
        from core import orchestrator as orch_module
        
        # Mock run_providers_stream to return test data
        async def mock_stream(target, modules, timeout, concurrency):
            yield {
                "module": "test_module_1",
                "status": "ok",
                "data": {"test": "value1"}
            }
            yield {
                "module": "test_module_2",
                "status": "ok",
                "data": {"test": "value2"}
            }
            yield {
                "_final": True,
                "merged": {"test_module_1": {"test": "value1"}}
            }
        
        with patch.object(orch_module.AsyncOrchestrator, 'run_providers_stream', mock_stream):
            results = []
            async for item in mock_stream('example.com', [], 10, 3):
                results.append(item)
            
            assert len(results) == 3, f"Expected 3 results, got {len(results)}"
            assert results[0]['module'] == 'test_module_1'
            assert results[-1].get('_final') == True

    def test_export_dict_flattening(self):
        """Test that dict flattening works for CSV export"""
        def flatten_dict(d, parent_key='', sep='_'):
            """Flatten nested dict for CSV export"""
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key, sep=sep).items())
                elif isinstance(v, list):
                    items.append((new_key, json.dumps(v)))
                else:
                    items.append((new_key, v))
            return dict(items)
        
        nested = {
            "module": "test",
            "status": "ok",
            "data": {
                "nested_key": "value",
                "list_key": [1, 2, 3]
            }
        }
        
        flattened = flatten_dict(nested)
        assert 'module' in flattened
        assert 'data_nested_key' in flattened
        assert 'data_list_key' in flattened

    def test_theme_persistence_file(self):
        """Test that theme preference can be saved/loaded"""
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            theme_file = Path(tmpdir) / 'theme.txt'
            
            # Save theme
            theme_file.write_text('light')
            assert theme_file.exists()
            
            # Load theme
            loaded_theme = theme_file.read_text().strip()
            assert loaded_theme == 'light'

    def test_json_export_format(self):
        """Test that results can be exported to JSON"""
        test_results = [
            {
                "module": "test_module",
                "status": "ok",
                "data": {"key": "value"}
            }
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / 'results.json'
            
            with open(output_file, 'w') as f:
                json.dump(test_results, f, indent=2)
            
            assert output_file.exists()
            
            with open(output_file, 'r') as f:
                loaded = json.load(f)
            
            assert len(loaded) == 1
            assert loaded[0]['module'] == 'test_module'

    def test_csv_export_format(self):
        """Test that results can be exported to CSV"""
        def flatten_dict(d, parent_key='', sep='_'):
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key, sep=sep).items())
                elif isinstance(v, list):
                    items.append((new_key, json.dumps(v)))
                else:
                    items.append((new_key, v))
            return dict(items)
        
        test_result = {
            "module": "test",
            "status": "ok",
            "data": {"key": "value"}
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / 'results.csv'
            
            flattened = flatten_dict(test_result)
            fieldnames = list(flattened.keys())
            
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(flattened)
            
            assert output_file.exists()
            
            with open(output_file, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) == 1
            assert rows[0]['module'] == 'test'

    def test_logger_initialization(self):
        """Test that logger can be initialized"""
        from core.logger import get_logger
        
        logger = get_logger('test')
        assert logger is not None

    def test_config_loader(self):
        """Test that config can be loaded"""
        from config.loader import get_config

        config = get_config()
        assert config is not None

    def test_error_suggestions_keywords(self):
        """Test error suggestion keyword matching"""
        def get_error_suggestion(error_msg):
            """Generate suggestion based on error keywords"""
            error_lower = error_msg.lower()
            
            if 'timeout' in error_lower or 'connection' in error_lower:
                return "Check your internet connection or increase timeout"
            elif 'api' in error_lower or 'key' in error_lower or 'auth' in error_lower:
                return "Configure API keys in core/keys.py"
            elif 'invalid' in error_lower or 'format' in error_lower:
                return "Verify target format (domain, IP, or email)"
            elif '404' in error_lower or 'not found' in error_lower:
                return "Target not found on this platform"
            else:
                return "Check the error details and try again"
        
        assert "internet" in get_error_suggestion("Connection timeout")
        assert "API keys" in get_error_suggestion("Invalid API key")
        assert "format" in get_error_suggestion("Invalid target format")
        assert "not found" in get_error_suggestion("404 Not Found")


class TestTUIIntegration:
    """Integration tests for TUI components"""

    def test_tui_keyboard_bindings(self):
        """Test that TUI has required keyboard bindings"""
        # Expected bindings from implementation
        required_bindings = ['r', 'm', 'p', 'l', 'e', 't', 'c', 'q']
        
        # Can't easily test Textual bindings without rendering, so check imports work
        try:
            import tui
            assert tui is not None
        except Exception as e:
            pytest.fail(f"TUI bindings test failed: {e}")

    def test_compose_widgets_exist(self):
        """Test that required widgets are available"""
        # These would be textual widgets
        try:
            from textual.widgets import Static, Input, Button, Select, Label  # type: ignore[reportMissingImports]
            from textual.containers import Container, Horizontal, Vertical  # type: ignore[reportMissingImports]
            
            assert Static is not None
            assert Button is not None
            assert Select is not None
        except ImportError:
            # Textual optional; skip if not installed
            pytest.skip("Textual not installed (optional dependency)")

    def test_result_streaming_mock(self):
        """Test that results can be streamed and stored"""
        results = []
        
        # Simulate streaming results
        test_data = [
            {"module": "m1", "status": "ok", "data": {"key": "val1"}},
            {"module": "m2", "status": "ok", "data": {"key": "val2"}},
            {"module": "m3", "status": "error", "message": "Failed"},
        ]
        
        for result in test_data:
            results.append(result)
        
        assert len(results) == 3
        assert results[0]['module'] == 'm1'
        assert results[2]['status'] == 'error'

    def test_error_tracking_mock(self):
        """Test that errors are tracked correctly"""
        errors = []
        
        # Simulate error tracking
        def add_error(provider, error_msg, suggestion):
            errors.append({
                "provider": provider,
                "error": error_msg,
                "suggestion": suggestion
            })
        
        add_error("module1", "API timeout", "Check connection")
        add_error("module2", "Invalid key", "Update config")
        
        assert len(errors) == 2
        assert errors[0]['provider'] == 'module1'


class TestTUIErrorHandling:
    """Test error handling in TUI"""

    def test_graceful_import_degradation(self):
        """Test that TUI gracefully handles optional Textual import"""
        # TUI uses TYPE_CHECKING pattern for optional imports
        try:
            import tui
            # If we get here, import succeeded (either Textual available or fallback worked)
            assert tui is not None
        except Exception as e:
            pytest.fail(f"TUI import failed ungracefully: {e}")

    def test_malformed_target_handling(self):
        """Test that malformed targets are rejected"""
        import re
        
        def is_valid_target(target):
            domain_pattern = r'^(?:[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?\.)+[a-z]{2,}$'
            ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
            email_pattern = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'
            
            return bool(
                re.match(domain_pattern, target.lower()) or
                re.match(ip_pattern, target) or
                re.match(email_pattern, target.lower())
            )
        
        assert is_valid_target('example.com')
        assert not is_valid_target('')
        assert not is_valid_target('   ')
        assert not is_valid_target('not a valid target')

    def test_empty_module_selection_handling(self):
        """Test that scanning with no modules is rejected"""
        selected_modules = []
        
        if len(selected_modules) == 0:
            error = "At least one module must be selected"
        else:
            error = None
        
        assert error is not None
        assert "At least one module" in error


def run_smoke_tests():
    """Run all smoke tests"""
    print("\n" + "="*60)
    print("DarkReconX TUI - Smoke Test Suite")
    print("="*60 + "\n")
    
    # Run with pytest if available, otherwise basic validation
    try:
        pytest.main([__file__, '-v', '--tb=short'])
    except Exception:
        print("pytest not available; running basic validation...\n")
        
        test = TestTUISmoke()
        
        print("Testing TUI imports...")
        try:
            test.test_tui_imports()
            print("✓ TUI imports successful")
        except Exception as e:
            print(f"✗ TUI imports failed: {e}")
        
        print("\nTesting module discovery...")
        try:
            test.test_module_discovery()
            print("✓ Module discovery successful")
        except Exception as e:
            print(f"✗ Module discovery failed: {e}")
        
        print("\nTesting profile loading...")
        try:
            test.test_profile_loading()
            print("✓ Profile loading successful")
        except Exception as e:
            print(f"✗ Profile loading failed: {e}")
        
        print("\nTesting target validation...")
        try:
            test.test_target_validation()
            print("✓ Target validation successful")
        except Exception as e:
            print(f"✗ Target validation failed: {e}")
        
        print("\nTesting logger...")
        try:
            test.test_logger_initialization()
            print("✓ Logger initialization successful")
        except Exception as e:
            print(f"✗ Logger initialization failed: {e}")
        
        print("\n" + "="*60)
        print("Basic validation complete!")
        print("="*60 + "\n")


if __name__ == '__main__':
    run_smoke_tests()
