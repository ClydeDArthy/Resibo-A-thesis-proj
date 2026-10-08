"""RESIBO gait module.

The module collects person-track observations and prepares normalized silhouette
sequences for the OpenGait/GaitBase backend.
"""

from .config import GaitConfig
from .pipeline import GaitPipeline, GaitResult

__all__ = ["GaitConfig", "GaitPipeline", "GaitResult"]
