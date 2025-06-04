"""
PyRTFPA - Python Real-Time Fractal Path Analysis

A Python implementation of the FractalTracker system for real-time fractal
path analysis, originally designed for Ubisense RTLS or log files.
"""

__version__ = "0.9"
__author__ = "Dr. Jeffrey Craighead"

# Export main classes for easier imports
from .rtfpa import RTFPA
from .line_tools import LineToolsRT, Point3D
from .running_d import RunningD

__all__ = [
    'RTFPA',
    'LineToolsRT',
    'Point3D',
    'RunningD',
]