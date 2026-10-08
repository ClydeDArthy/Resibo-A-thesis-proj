"""Real GaitBase runtime hooks. No synthetic recognition fallback."""
import importlib
import os
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


class SegmentationSilhouetteExtractor:
    def __init__(self, weights=None):
        self.weights = str(weights or os.getenv("RESIBO_SILHOUETTE_WEIGHTS", "yolo11n-seg.pt"))
        self.model = None
        self.error = None
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.weights)
        except Exception as exc:
            self.error = str(exc)

    @property
    def ready(self):
        return self.model is not None

    def __call__(self, crop):
        if self.model is None or crop is None or crop.size == 0:
            return None
        try:
            best = None
            best_area = 0
            for result in self.model.predict(crop, classes=[0], verbose=False):
                masks = getattr(result, "masks", None)
                boxes = getattr(result, "boxes", None)
                if masks is None or boxes is None:
                    continue
                data = masks.data.cpu().numpy()
                conf = boxes.conf.cpu().numpy()
                for i, mask in enumerate(data):
                    if float(conf[i]) < 0.25:
                        continue
                    area = int((mask > 0.5).sum())
                    if area > best_area:
                        best_area = area
                        best = (mask > 0.5).astype(np.uint8) * 255
            if best is None:
                return None
            return cv2.resize(best, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_NEAREST)
        except Exception as exc:
            self.error = str(exc)
            return None


class GaitGalleryScorer:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv("RESIBO_GAIT_GALLERY", "workspace/gait/gallery.npz"))
        self.ids = None
        self.embeddings = None
        if self.path.is_file():
            data = np.load(self.path, allow_pickle=False)
            self.ids = [str(v) for v in data["ids"].tolist()]
            self.embeddings = np.asarray(data["embeddings"], dtype=np.float32)
            if self.embeddings.ndim != 2 or len(self.ids) != len(self.embeddings):
                raise ValueError("Invalid gait gallery: ids[N] and embeddings[N,D] required")

    @property
    def ready(self):
        return self.embeddings is not None and len(self.ids) > 0

    def __call__(self, master_id, embedding):
        if not self.ready:
            return None
        vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
        if vector.shape[0] != self.embeddings.shape[1]:
            raise ValueError("Gait embedding dimension does not match gallery")
        denom = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(vector)
        scores = np.divide(self.embeddings @ vector, denom,
                           out=np.zeros(len(self.ids), dtype=np.float32), where=denom > 0)
        idx = int(np.argmax(scores))
        from resibo import BiometricObservation
        raw = float(scores[idx])
        return BiometricObservation(
            master_id=int(master_id), modality="gait", candidate_id=self.ids[idx],
            score=float((raw + 1.0) / 2.0),
            metadata={"raw_cosine_similarity": raw, "gallery": str(self.path),
                      "scoring": "cosine_to_unit_range_only_not_calibrated"},
        )


def load_callable(spec=None):
    value = spec or os.getenv("RESIBO_GAIT_BACKEND")
    if not value:
        return None
    if ":" not in value:
        raise ValueError("RESIBO_GAIT_BACKEND must be module:function")
    module, function = value.split(":", 1)
    fn = getattr(importlib.import_module(module), function)
    if not callable(fn):
        raise TypeError(value + " is not callable")
    return fn
