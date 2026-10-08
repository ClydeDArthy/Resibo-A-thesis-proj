from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np


@dataclass
class GaitEmbedding:
    track_id: int
    embedding: np.ndarray
    model_name: str = "GaitBase"
    sequence_length: int = 0


class GaitBaseAdapter:
    """Small boundary around the existing OpenGait/GaitBase installation.

    We intentionally do not reimplement OpenGait's model internals here.
    The adapter accepts a callable backend so the exact OpenGait checkout,
    config, and checkpoint used by the project can be connected without
    changing the detector-facing Gait API.
    """

    def __init__(self, backend: Optional[Callable[[np.ndarray], np.ndarray]] = None):
        self.backend = backend

    @property
    def ready(self) -> bool:
        return self.backend is not None

    def infer(self, silhouettes: np.ndarray, track_id: int) -> GaitEmbedding:
        if silhouettes.ndim != 3:
            raise ValueError("Expected silhouette tensor shaped [T, H, W]")
        if not self.ready:
            raise RuntimeError(
                "GaitBase backend is not configured. Connect the project's "
                "OpenGait GaitBase checkpoint/config before inference."
            )

        vector = np.asarray(self.backend(silhouettes))
        if vector.ndim != 1:
            vector = vector.reshape(-1)
        return GaitEmbedding(
            track_id=track_id,
            embedding=vector.astype(np.float32),
            sequence_length=int(silhouettes.shape[0]),
        )
