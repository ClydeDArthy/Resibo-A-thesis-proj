"""Runtime face stage used by OBJ dispatch.

This stage performs face detection/cropping with the project's face YOLO
checkpoint when available and reads completed OSDFace/AdaFace candidate rows
from the existing FR SQLite store. It never invents an identity.
"""
import os
from pathlib import Path
from typing import Optional

import numpy as np


class FaceRuntime:
    def __init__(self, weights: Optional[str | Path] = None, fr_store=None):
        self.weights = Path(weights or os.getenv("RESIBO_FACE_WEIGHTS", "yolov11s-face.pt"))
        self.fr_store = fr_store
        self.model = None
        self.error = None
        self._load_detector()

    @property
    def detector_ready(self) -> bool:
        return self.model is not None

    @property
    def recognition_ready(self) -> bool:
        return self.fr_store is not None and self.fr_store.database_path.is_file()

    def _load_detector(self):
        try:
            if not self.weights.is_file():
                self.error = f"face checkpoint not found: {self.weights}"
                return
            from ultralytics import YOLO
            self.model = YOLO(str(self.weights))
        except Exception as exc:
            self.error = str(exc)

    def process(self, frame: np.ndarray, person_box, master_id: int, frame_index: int) -> dict:
        x1, y1, x2, y2 = [int(round(v)) for v in person_box]
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        crop = frame[y1:y2, x1:x2]
        result = {
            "master_id": int(master_id),
            "frame_index": int(frame_index),
            "detector": "ready" if self.detector_ready else "unavailable",
            "faces": 0,
            "quality": 0.0,
            "candidate": None,
            "score": None,
            "rank": None,
            "crop": None,
        }
        if crop.size == 0:
            return result
        if self.detector_ready:
            try:
                detections = self.model.predict(crop, verbose=False)
                best = None
                for item in detections:
                    boxes = getattr(item, "boxes", None)
                    if boxes is None:
                        continue
                    for i in range(len(boxes)):
                        conf = float(boxes.conf[i].item())
                        coords = boxes.xyxy[i].cpu().numpy().astype(int).tolist()
                        if best is None or conf > best[0]:
                            best = (conf, coords)
                if best is not None:
                    conf, (fx1, fy1, fx2, fy2) = best
                    result["faces"] = 1
                    result["quality"] = conf
                    result["crop"] = crop[max(0, fy1):max(0, fy2), max(0, fx1):max(0, fx2)]
            except Exception as exc:
                result["detector_error"] = str(exc)

        if self.recognition_ready:
            try:
                candidates = self.fr_store.candidates_for_track(str(master_id))
                if candidates:
                    top = candidates[0]
                    result["candidate"] = top.candidate_id
                    result["score"] = top.cosine_similarity
                    result["rank"] = top.rank
            except Exception as exc:
                result["recognition_error"] = str(exc)
        return result
