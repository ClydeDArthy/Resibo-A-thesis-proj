"""Live face detection boundary used by the FE runtime."""
import os
from pathlib import Path

import numpy as np


class FaceRuntime:
    def __init__(self, fr_store=None, weights=None):
        self.fr_store = fr_store
        self.weights = str(weights or os.getenv("RESIBO_FACE_WEIGHTS", "yolov11s-face.pt"))
        self.model = None
        self.error = None
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.weights)
        except Exception as exc:
            self.error = str(exc)

    @property
    def detector_ready(self):
        return self.model is not None

    def process(self, frame, person_box, master_id, frame_index):
        x1, y1, x2, y2 = [int(v) for v in person_box]
        h, w = frame.shape[:2]
        x1, x2 = max(0, x1), min(w, x2)
        y1, y2 = max(0, y1), min(h, y2)
        crop = frame[y1:y2, x1:x2]
        faces = []
        if self.model is not None and crop.size:
            try:
                results = self.model.predict(crop, verbose=False)
                for result in results:
                    boxes = getattr(result, "boxes", None)
                    if boxes is None:
                        continue
                    xyxy = boxes.xyxy.cpu().numpy()
                    conf = boxes.conf.cpu().numpy()
                    for box, score in zip(xyxy, conf):
                        fx1, fy1, fx2, fy2 = box.tolist()
                        faces.append({
                            "box": [x1 + fx1, y1 + fy1, x1 + fx2, y1 + fy2],
                            "confidence": float(score),
                        })
            except Exception as exc:
                self.error = str(exc)

        top = None
        if self.fr_store is not None:
            try:
                candidates = self.fr_store.candidates_for_track(str(master_id))
                if candidates:
                    top = candidates[0]
            except Exception as exc:
                self.error = str(exc)

        return {
            "detector": "ready" if self.detector_ready else "error",
            "faces": len(faces),
            "detections": faces,
            "quality": float(max([f["confidence"] for f in faces], default=0.0)),
            "candidate": getattr(top, "candidate_id", None) if top else None,
            "score": getattr(top, "cosine_similarity", None) if top else None,
            "error": self.error,
            "frame_index": int(frame_index),
        }
