"""RESIBO object detection and tracking module."""

from .config import ObjectConfig
from .pipeline import ObjectTrackingPipeline

__all__ = ["ObjectConfig", "ObjectTrackingPipeline"]

from .runner import ObjectRunner
