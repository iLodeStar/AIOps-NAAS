#!/usr/bin/env python3
"""
Test suite for user-friendly diagnostic tools
"""

import unittest
import sys
import os
import subprocess
import tempfile
import json
from pathlib import Path

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'system-compatibility-monitor'))

class TestUserFriendlyDiagnostics(unittest.TestCase):
    """Test the user-friendly diagnostics tool"""
    
    def setUp(self):
        self.script_path = Path(__file__).parent.parent / "scripts" / "user_friendly_diagnostics.py"
        self.assertTrue(self.script_path.exists(), "Diagnostic script not found")
    
    def test_help_output(self):
        """Test that help command works"""
        result = subprocess.run([
            "python3", str(self.script_path), "--help"
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("sanity", result.stdout)
        self.assertIn("regression", result.stdout)
        self.assertIn("surveillance", result.stdout)
        self.assertIn("automation", result.stdout)
    
    def test_script_executable(self):
        """Test that the script is executable"""
        self.assertTrue(os.access(self.script_path, os.X_OK), "Script is not executable")
    
    def test_import_works(self):
        """Test that we can import the diagnostic module"""
        try:
            sys.path.insert(0, str(self.script_path.parent))
            # Try to import and instantiate the main class
            from user_friendly_diagnostics import UserFriendlyDiagnostics, Colors
            
            diagnostics = UserFriendlyDiagnostics()
            self.assertTrue(diagnostics.session_id.startswith("DIAG-"))
            self.assertEqual(diagnostics.session.mode, "")
            
        except ImportError as e:
            self.fail(f"Could not import user_friendly_diagnostics: {e}")

class TestCompatibilityMonitor(unittest.TestCase):
    """Test the compatibility monitor"""
    
    def setUp(self):
        self.monitor_path = Path(__file__).parent.parent / "services" / "system-compatibility-monitor" / "compatibility_monitor.py"
        self.config_path = Path(__file__).parent.parent / "services" / "system-compatibility-monitor" / "config.json"
        self.assertTrue(self.monitor_path.exists(), "Compatibility monitor script not found")
        self.assertTrue(self.config_path.exists(), "Compatibility monitor config not found")
    
    def test_monitor_test_mode(self):
        """Test compatibility monitor in test mode"""
        result = subprocess.run([
            "python3", str(self.monitor_path), "--test-mode"
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("Compatibility Test Results", result.stdout)
        self.assertIn("Passed:", result.stdout)
    
    def test_config_file_valid(self):
        """Test that configuration file is valid JSON"""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        # Check required keys
        required_keys = ["monitoring_interval", "syslog_port", "snmp_targets", "test_message_formats"]
        for key in required_keys:
            self.assertIn(key, config, f"Missing required config key: {key}")
    
    def test_import_monitor_works(self):
        """Test that we can import the compatibility monitor"""
        try:
            sys.path.insert(0, str(self.monitor_path.parent))
            from compatibility_monitor import CompatibilityMonitor, OSMessageFormats
            
            monitor = CompatibilityMonitor()
            self.assertIsNotNone(monitor.config)
            self.assertIn("monitoring_interval", monitor.config)
            
            # Test OS message formats are defined
            self.assertIsInstance(OSMessageFormats.FORMATS, dict)
            self.assertIn("debian", OSMessageFormats.FORMATS)
            self.assertIn("windows", OSMessageFormats.FORMATS)
            
        except ImportError as e:
            self.fail(f"Could not import compatibility_monitor: {e}")

class TestDocumentation(unittest.TestCase):
    """Test that documentation files exist and are well-formed"""
    
    def setUp(self):
        self.docs_root = Path(__file__).parent.parent / "docs"
        self.user_guides = self.docs_root / "user-guides"
    
    def test_user_guide_exists(self):
        """Test that user guide exists"""
        guide_path = self.user_guides / "diagnostic-tool-guide.md"
        self.assertTrue(guide_path.exists(), "User guide not found")
        
        # Check file has content
        with open(guide_path, 'r') as f:
            content = f.read()
        
        self.assertGreater(len(content), 1000, "User guide seems too short")
        self.assertIn("Sanity Mode", content)
        self.assertIn("Regression Mode", content)
        self.assertIn("non-technical", content.lower())
    
    def test_quick_reference_exists(self):
        """Test that quick reference card exists"""
        ref_path = self.user_guides / "quick-reference-card.md"
        self.assertTrue(ref_path.exists(), "Quick reference card not found")
        
        with open(ref_path, 'r') as f:
            content = f.read()
        
        self.assertIn("sanity", content.lower())
        self.assertIn("regression", content.lower())
        self.assertIn("troubleshooting", content.lower())

class TestMakefileIntegration(unittest.TestCase):
    """Test Makefile integration"""
    
    def setUp(self):
        self.makefile_path = Path(__file__).parent.parent / "Makefile"
        self.assertTrue(self.makefile_path.exists(), "Makefile not found")
    
    def test_makefile_has_new_targets(self):
        """Test that Makefile includes new targets"""
        with open(self.makefile_path, 'r') as f:
            makefile_content = f.read()
        
        self.assertIn("diagnose:", makefile_content)
        self.assertIn("compatibility-monitor:", makefile_content)
        self.assertIn("User-friendly diagnostic tool", makefile_content)
        self.assertIn("compatibility monitoring", makefile_content)

if __name__ == "__main__":
    # Change to repository root for testing
    repo_root = Path(__file__).parent.parent
    os.chdir(repo_root)
    
    # Run tests
    unittest.main(verbosity=2)