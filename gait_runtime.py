"""Runtime helpers for the real GaitBase path."""
import importlib
import os
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


class SegmentationSilhouetteExtractor:
    """Extract a person mask from each OBJ crop with YOLO11-seg."""

    def __init__(self, weights: str | Path | None = None):
        self.weights = str(weights or os.getenv(
            "RESIBO_SILHOUETTE_WEIGHTS", "yolo11n-seg.pt"
        ))
        self.model = None
        self.error = None
        try:
            from ultralytics import YOLO
            # Official Ultralytics weights are downloaded on first use when
            # they are not already present locally.
            self.model = YOLO(self.weights)
        except Exception as exc:
            self.error = str(exc)

    @property
    def ready(self) -> bool:
        return self.model is not None

    def __call__(self, crop: np.ndarray) -> Optional[np.ndarray]:
        if crop is None or crop.size == 0 or self.model is None:
            return None
        try:
            results = self.model.predict(crop, classes=[0], verbose=False)
            best_mask = None
            best_area = 0
            for result in results:
                masks = getattr(result, "masks", None)
                boxes = getattr(result, "boxes", None)
                if masks is None or boxes is None:
                    continue
                data = masks.data.cpu().numpy()
                confs = boxes.conf.cpu().numpy()
                for idx, mask in enumerate(data):
                    area = int((mask > 0.5).sum())
                    if area > best_area and float(confs[idx]) >= 0.25:
                        best_area = area
                        best_mask = (mask > 0.5).astype(np.uint8) * 255
            if best_mask is None:
                return None
            return cv2.resize(
                best_mask,
                (crop.shape[1], crop.shape[0]),
                interpolation=cv2.INTER_NEAREST,
            )
        except Exception as exc:
            self.error = str(exc)
            return None


def silhouette_from_person_crop(crop: np.ndarray) -> Optional[np.ndarray]:
    """Backward-compatible entry point; uses the segmentation extractor."""
    return SegmentationSilhouetteExtractor()(crop)


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


class GaitGalleryScorer:
    """Cosine-match a GaitBase embedding against a local reference gallery."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.getenv(
            "RESIBO_GAIT_GALLERY", "workspace/gait/gallery.npz"
        ))
        self.ids = None
        self.embeddings = None
        if self.path.is_file():
            data = np.load(self.path, allow_pickle=False)
            self.ids = [str(v) for v in data["ids"].tolist()]
            self.embeddings = np.asarray(data["embeddings"], dtype=np.float32)
            if self.embeddings.ndim != 2 or len(self.ids) != len(self.embeddings):
                raise ValueError("Gait gallery must contain ids[N] and embeddings[N,D]")

    @property
    def ready(self) -> bool:
        return self.embeddings is not None and len(self.ids) > 0

    def __call__(self, master_id: int, embedding: np.ndarray):
        if not self.ready:
            return None
        vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
        if vector.shape[0] != self.embeddings.shape[1]:
            raise ValueError("Gait embedding dimension does not match the gallery")
        denom = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(vector)
        scores = np.divide(
            self.embeddings @ vector,
            denom,
            out=np.zeros(len(self.ids), dtype=np.float32),
            where=denom > 0,
        )
        idx = int(np.argmax(scores))
        from resibo import BiometricObservation
        return BiometricObservation(
            master_id=int(master_id),
            modality="gait",
            candidate_id=self.ids[idx],
            score=float((scores[idx] + 1.0) / 2.0),
            metadata={
                "raw_cosine_similarity": float(scores[idx]),
                "gallery": str(self.path),
                "scoring": "cosine_to_unit_range_only_not_calibrated",
            },
        )
