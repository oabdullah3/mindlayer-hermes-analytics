#!/usr/bin/env python3
"""
DEPRECATED: Hermes Analytics Data Collector has moved to userend/collector.py.
This wrapper exists for backward compatibility and will be removed
in a future release.
"""
import sys
import os

sys.stderr.write("[DEPRECATED] collector.py moved to userend/collector.py\n")
sys.path.insert(0, os.path.dirname(__file__))

from userend.collector import main

if __name__ == "__main__":
    main()
