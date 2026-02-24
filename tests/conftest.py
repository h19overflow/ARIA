"""Test configuration: patch broken top-level exports before package import."""
import sys
from unittest.mock import MagicMock

# src.agentic_system.__init__ tries to import build_aria_graph and
# compile_aria_graph from graph.py, which no longer exports them.
# We pre-populate sys.modules with a mock for the graph module so
# the __init__ import succeeds without touching the real graph.py.
_graph_mock = MagicMock()
_graph_mock.build_aria_graph = MagicMock()
_graph_mock.compile_aria_graph = MagicMock()
sys.modules.setdefault("src.agentic_system.graph", _graph_mock)
