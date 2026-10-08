"""Live adapter for the exact GaitBase checkpoint produced by rebigait.py.

The training notebook used the OpenGait Baseline architecture with:
ResNet9 -> SeparateFCs(512,256,16) -> 256x16 embedding.
The fine-tuned checkpoint is GaitBase_DA_CCGR_FT-10000.pt.

This adapter does not retrain anything. It loads that checkpoint once and
returns the same inference_feat['embeddings'] representation used by OpenGait.
"""
import os
import sys
from pathlib import Path
from threading import Lock

import numpy as np

_MODEL = None
_LOCK = Lock()


def _cfg():
    return {
        "model_cfg": {
            "model": "Baseline",
            "backbone_cfg": {
                "type": "ResNet9",
                "block": "BasicBlock",
                "channels": [64, 128, 256, 512],
                "layers": [1, 1, 1, 1],
                "strides": [1, 2, 2, 1],
                "maxpool": False,
            },
            "SeparateFCs": {
                "in_channels": 512,
                "out_channels": 256,
                "parts_num": 16,
            },
            "SeparateBNNecks": {
                "class_num": 679,
                "in_channels": 256,
                "parts_num": 16,
            },
            "bin_num": [16],
        }
    }


def _load():
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    with _LOCK:
        if _MODEL is not None:
            return _MODEL

        import torch

        root = Path(os.getenv("RESIBO_OPENGAIT_ROOT", "OpenGait")).expanduser()
        if root.is_dir() and str(root.resolve()) not in sys.path:
            sys.path.insert(0, str(root.resolve()))

        checkpoint = Path(
            os.getenv(
                "RESIBO_GAIT_CHECKPOINT",
                "workspace/gait/GaitBase_DA_CCGR_FT-10000.pt",
            )
        ).expanduser()
        if not checkpoint.is_file():
            raise FileNotFoundError(
                "GaitBase checkpoint not found: {}. "
                "Set RESIBO_GAIT_CHECKPOINT to the GaitBase_DA_CCGR_FT-10000.pt "
                "produced by rebigait.py.".format(checkpoint)
            )

        from opengait.modeling.models.baseline import Baseline

        # Build Baseline without BaseModel.__init__: OpenGait's normal
        # constructor assumes a distributed CUDA test process. RESIBO is a
        # single-process live runtime, so we construct the network directly.
        model = Baseline.__new__(Baseline)
        torch.nn.Module.__init__(model)
        model.build_network(_cfg()["model_cfg"])

        ckpt = torch.load(checkpoint, map_location="cpu", weights_only=False)
        state = ckpt.get("model", ckpt)
        if not isinstance(state, dict):
            raise ValueError("Unsupported OpenGait checkpoint structure")

        result = model.load_state_dict(state, strict=False)
        missing_core = [
            key for key in result.missing_keys
            if key.startswith(("Backbone.", "FCs."))
        ]
        if missing_core:
            raise RuntimeError(
                "GaitBase checkpoint is incompatible with the rebigait.py "
                "architecture; missing core weights: {}".format(missing_core[:10])
            )

        device_name = os.getenv("RESIBO_GAIT_DEVICE", "cuda")
        device = torch.device(
            device_name if device_name != "cuda" or torch.cuda.is_available() else "cpu"
        )
        model.to(device)
        model.eval()
        _MODEL = (model, device)
        return _MODEL


def infer_gaitbase(silhouettes):
    """Return one native GaitBase embedding tensor as a numpy array.

    Input: [T, 64, 64] binary silhouettes.
    Output: [16, 256], matching rebigait.py/OpenGait inference embeddings.
    """
    import torch

    seq = np.asarray(silhouettes)
    if seq.ndim != 3:
        raise ValueError("GaitBase expects silhouettes shaped [T, H, W]")
    if seq.shape[1:] != (64, 64):
        raise ValueError("GaitBase expects 64x64 silhouettes")

    seq = (seq > 0).astype(np.float32)
    model, device = _load()

    sils = torch.from_numpy(seq).unsqueeze(0).to(device)
    seq_len = int(sils.shape[1])
    seq_l = torch.tensor([seq_len], dtype=torch.int64, device=device)

    inputs = (
        [sils],
        torch.zeros((1,), dtype=torch.int64, device=device),
        ["RESIBO"],
        ["0"],
        seq_l,
    )

    with torch.no_grad():
        output = model(inputs)

    embeddings = output.get("inference_feat", {}).get("embeddings")
    if embeddings is None:
        raise RuntimeError("OpenGait did not return inference_feat.embeddings")

    return embeddings.detach().float().cpu().numpy()[0]


def backend_ready():
    try:
        _load()
        return True
    except Exception:
        return False
