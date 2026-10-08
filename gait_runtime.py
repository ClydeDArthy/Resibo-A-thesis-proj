"""Runtime Gait helpers.

The silhouette extraction is local and deterministic. The recognition backend
is deliberately loaded from the project's existing trained GaitBase runtime;
there is no synthetic fallback embedding.
"""
import importlib
import os
from typing import Optional

import cv2
import numpy as np


def silhouette_from_person_crop(crop: np.ndarray) -> Optional[np.ndarray]:
    if crop is None or crop.size == 0:
        return None
    if crop.ndim == 3:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = crop
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    # Person crops are already isolated by OBJ. A foreground estimate is used
    # only to create the silhouette input expected by GaitBase.
    mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    if np.mean(mask > 0) > 0.90:
        mask = cv2.bitwise_not(mask)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def load_callable(spec: Optional[str] = None):
    value = spec or os.getenv("RESIBO_GAIT_BACKEND")
    if not value:
        return None
    if ":" not in value:
        raise ValueError("RESIBO_GAIT_BACKEND must be module:function")
    module_name, function_name = value.split(":", 1)
    module = importlib.import_module(module_name)
    fn = getattr(module, function_name)
    if not callable(fn):
        raise TypeError(f"{value} is not callable")
    return fn
