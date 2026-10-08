from pathlib import Path

import face_runtime


def test_face_weight_discovery_prefers_local_checkpoint(tmp_path, monkeypatch):
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    checkpoint = model_dir / "yolov11s-face.pt"
    checkpoint.write_bytes(b"test")
    monkeypatch.chdir(tmp_path)
    assert face_runtime._discover_face_weights() == checkpoint


def test_face_weight_discovery_honors_environment(tmp_path, monkeypatch):
    checkpoint = tmp_path / "custom-face.pt"
    checkpoint.write_bytes(b"test")
    monkeypatch.setenv("RESIBO_FACE_WEIGHTS", str(checkpoint))
    assert face_runtime._discover_face_weights() == checkpoint
