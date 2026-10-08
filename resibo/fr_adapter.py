"""Read-only bridge from the existing FR SQLite result store into RESIBO.

This module does not run OSDFace/AdaFace and does not alter the FR database.
It only reads ranked candidate rows produced by the existing FR workflow.
"""
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Optional

from .types import BiometricObservation


@dataclass(frozen=True)
class FaceCandidate:
    track_id: str
    candidate_id: str
    cosine_similarity: float
    rank: int
    job_id: str
    input_asset_id: str
    branch: str


class FRCandidateStore:
    """Read ranked FR candidates associated with tracked face crops."""

    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        if not self.database_path.is_file():
            raise FileNotFoundError(
                f"FR result database not found: {self.database_path}"
            )
        db = sqlite3.connect(self.database_path)
        db.row_factory = sqlite3.Row
        return db

    def verify_read_only(self) -> dict:
        """Run SQLite integrity checks without modifying the database."""
        with self._connect() as db:
            integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
            foreign = db.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok" or foreign:
            raise RuntimeError("FR database integrity check failed")
        return {"integrity": "ok", "foreign_key_violations": 0}

    def candidates_for_track(
        self,
        track_id: str,
        branch: str = "ENHANCED",
        job_id: Optional[str] = None,
    ) -> list[FaceCandidate]:
        """Return ranked candidates for every input crop belonging to track_id."""
        query = """
            SELECT
                c.job_id,
                c.input_asset_id,
                c.reference_subject_id,
                c.reference_asset_id,
                c.candidate_rank,
                c.cosine_similarity,
                c.branch,
                a.metadata_json
            FROM candidate_matches c
            JOIN assets a ON a.asset_id = c.input_asset_id
            WHERE c.branch = ?
        """
        params: list[object] = [branch]
        if job_id is not None:
            query += " AND c.job_id = ?"
            params.append(job_id)

        candidates: list[FaceCandidate] = []
        with self._connect() as db:
            rows = db.execute(query, params).fetchall()

        for row in rows:
            try:
                metadata = json.loads(row["metadata_json"])
            except (TypeError, json.JSONDecodeError):
                continue
            if str(metadata.get("track_id")) != str(track_id):
                continue

            candidate_id = row["reference_subject_id"] or row["reference_asset_id"]
            candidates.append(
                FaceCandidate(
                    track_id=str(track_id),
                    candidate_id=str(candidate_id),
                    cosine_similarity=float(row["cosine_similarity"]),
                    rank=int(row["candidate_rank"]),
                    job_id=str(row["job_id"]),
                    input_asset_id=str(row["input_asset_id"]),
                    branch=str(row["branch"]),
                )
            )

        candidates.sort(key=lambda item: (item.rank, -item.cosine_similarity, item.input_asset_id))
        return candidates

    @staticmethod
    def cosine_to_unit_score(cosine_similarity: float) -> float:
        """Map cosine [-1, 1] to [0, 1] for the prototype fusion API.

        This is a range conversion, not a calibrated probability or LR.
        The original cosine value remains available in candidate metadata.
        """
        value = float(cosine_similarity)
        if not -1.000001 <= value <= 1.000001:
            raise ValueError("cosine similarity must be in [-1, 1]")
        return max(0.0, min(1.0, (value + 1.0) / 2.0))

    def observation_from_candidate(
        self,
        candidate: FaceCandidate,
        quality: float = 1.0,
    ) -> BiometricObservation:
        return BiometricObservation(
            master_id=int(candidate.track_id) if str(candidate.track_id).isdigit() else -1,
            modality="face",
            candidate_id=candidate.candidate_id,
            score=self.cosine_to_unit_score(candidate.cosine_similarity),
            quality=quality,
            metadata={
                "raw_cosine_similarity": candidate.cosine_similarity,
                "rank": candidate.rank,
                "job_id": candidate.job_id,
                "input_asset_id": candidate.input_asset_id,
                "branch": candidate.branch,
                "score_mapping": "cosine_to_unit_range_only_not_calibrated",
            },
        )
