#!/usr/bin/env python3
"""
Integración de pruebas de conversation-audit en la suite central de tests/.
"""

import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(__file__)
SKILL_TEST_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "skills", "conversation-audit", "tests"))
if SKILL_TEST_DIR not in sys.path:
    sys.path.insert(0, SKILL_TEST_DIR)

from test_audit_engine import (
    TestAgentAuditCli,
    TestInlineEvalDetection,
    TestTerminalReplLoopAntipattern,
)

if __name__ == "__main__":
    unittest.main()
