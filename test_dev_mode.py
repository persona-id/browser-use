#!/usr/bin/env python3
"""
Test development mode functionality
"""

import os
import tempfile
from pathlib import Path

# Set development mode
os.environ['DEV_MODE'] = 'true'

# Import after setting environment variable
from api_server import DEV_MODE, SCREENSHOTS_DIR

def test_dev_mode_setup():
    """Test that development mode sets up correctly"""
    print(f"DEV_MODE: {DEV_MODE}")
    print(f"SCREENSHOTS_DIR: {SCREENSHOTS_DIR}")
    print(f"Directory exists: {SCREENSHOTS_DIR.exists()}")
    
    # Test the directory was created
    assert DEV_MODE == True
    assert SCREENSHOTS_DIR.exists()
    print("✅ Development mode setup working correctly")

if __name__ == "__main__":
    test_dev_mode_setup()