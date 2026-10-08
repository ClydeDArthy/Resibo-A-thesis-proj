"""Lightweight deterministic RESIBO demo backends for Dear PyGui deployment.

This mode is intentionally a UI/runtime simulator: it preserves the real
master_id -> face -> gait -> RESIBO -> diagnostic control flow without
pretending that missing research model weights were executed.
"""
from dataclasses import dataclass
import hashlib
import numpy as np
import cv2

from resibo import BiometricObservation


def _seed(master_id, frame_index=0):
    return int(hashlib.sha256(f"resibo:{master_id}:{frame_index}".encode()).hexdigest()[:8], 16)


def face_processor(face_crop, master_id, frame_index):
    quality = float(np.clip(0.72 + 0.08 * np.sin(frame_index / 11.0), 0.45, 0.95))
    # Stable candidate for a track; score varies slightly with frame quality.
    score = float(np.clip(0.86 - abs(np.sin(frame_index / 17.0)) * 0.05, 0.70, 0.95))
    return {
        "candidate": f"PERSON-{int(master_id):03d}",
        "score": score,
        "quality": quality,
        "demo": True,
    }


def silhouette(crop):
    if crop is None or crop.size == 0:
        return None
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    # Deterministic foreground-like mask for the deployment demo.
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, mask = cv2.threshold(blur, int(np.mean(blur)), 255, cv2.THRESH_BINARY)
    if float((mask > 0).mean()) < 0.05 or float((mask > 0).mean()) > 0.95:
        mask = np.full(gray.shape, 255, np.uint8)
        cv2.rectangle(mask, (gray.shape[1] // 4, 0),
                      (3 * gray.shape[1] // 4, gray.shape[0] - 1), 0, -1)
    return mask


def gait_backend(silhouettes, track_id):
    seq = np.asarray(silhouettes, dtype=np.float32)
    if seq.ndim != 3:
        raise ValueError("demo GaitBase expects [T,H,W]")
    # Fixed 256-D deterministic representation with shape/motion statistics.
    resized = np.stack([cv2.resize(x, (16, 16), interpolation=cv2.INTER_AREA)
                        for x in seq], axis=0) / 255.0
    mean = resized.mean(axis=0).reshape(-1)
    motion = np.abs(np.diff(resized, axis=0)).mean(axis=0).reshape(-1) if len(resized) > 1 else mean * 0
    base = np.concatenate([mean, motion]).astype(np.float32)
    rng = np.random.default_rng(_seed(track_id))
    proj = rng.normal(0, 0.08, (base.size, 256)).astype(np.float32)
    emb = base @ proj
    norm = np.linalg.norm(emb)
    return emb / norm if norm else emb


class DemoGaitScorer:
    ready = True

    def __call__(self, master_id, embedding):
        # Stable gallery of demo identities. Scores are deterministic and bounded.
        vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
        candidates = [f"PERSON-{int(master_id):03d}", "PERSON-002", "PERSON-003"]
        target = candidates[0]
        seed = _seed(master_id)
        rng = np.random.default_rng(seed)
        gallery = rng.normal(size=vector.size).astype(np.float32)
        gallery /= max(np.linalg.norm(gallery), 1e-8)
        sim = float(np.dot(vector, gallery))
        score = float(np.clip(0.74 + 0.12 * sim, 0.60, 0.92))
        return BiometricObservation(
            master_id=int(master_id), modality="gait",
            candidate_id=target, score=score, quality=0.82,
            metadata={"demo": True, "raw_cosine_similarity": sim},
        )


def condition_classifier(sequence, context=None):
    return "occlusion"


def intervention_builder(sequence, condition, context=None):
    seq = np.asarray(sequence).copy()
    if condition == "occlusion":
        h = seq.shape[1]
        seq[:, int(h * 0.30):int(h * 0.45), :] = 0
    return seq


def control_builder(sequence, condition, context=None):
    seq = np.asarray(sequence).copy()
    # Matched control removes a same-sized region from a different location.
    w = seq.shape[2]
    seq[:, :, int(w * 0.55):int(w * 0.70)] = 0
    return seq
