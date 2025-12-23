import sys
import os

# FIXED: Separate lines to prevent syntax errors
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if base_path not in sys.path:
    sys.path.insert(0, base_path)

import pytest
from unittest.mock import patch, MagicMock
import logging

# Standard imports (NO .py extension)
from ai_engine import _normalize_phone
import mailer

# ... (rest of your tests continue below)name: VerbaPost Safety Check

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  run-safety-tests:
    runs-on: ubuntu-latest
    # NEW: This sets the path for the entire job
    env:
      PYTHONPATH: ${{ github.workspace }}
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-mock

      - name: Run Tests
        run: |
          # Use "python -m pytest" to force the root folder into the path
          python -m pytest tests/test_hardening.py