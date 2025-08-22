"""Configure test suite environment"""
import os
import sys

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.dirname(project_root))  # Add parent directory for src imports
