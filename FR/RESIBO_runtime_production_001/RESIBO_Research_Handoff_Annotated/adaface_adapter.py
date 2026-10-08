"""Colab AdaFace adapter for normalized 512-value research embeddings."""
from pathlib import Path
import json
import os
import sys

_MODEL = None
_PROVENANCE = None

PREPROCESSING = 'RGB_112_NORMALIZED_RESIZE_ONLY_UNALIGNED_v1'


def get_model():
    """Load the preflight-verified AdaFace model once per Colab worker."""
    global _MODEL, _PROVENANCE
    if _MODEL is not None:
        return _MODEL
    os.environ['USE_TF'] = '0'
    import torch
    from importlib.metadata import version
    from transformers import AutoModel

    setup_file = Path('/content/resibo_setup/ready.json')
    if not setup_file.is_file():
        raise RuntimeError('Run colab_setup_osdface.py successfully before AdaFace.')
    setup = json.loads(setup_file.read_text())
    if setup.get('status') != 'PASSED' or not setup.get('adaface_local'):
        raise RuntimeError('AdaFace preflight data is missing or did not pass.')
    if not torch.cuda.is_available():
        raise RuntimeError('Select a Colab GPU runtime before AdaFace inference.')
    if version('transformers') != setup['versions']['transformers']:
        raise RuntimeError('Transformers changed after preflight; rerun setup.')

    model_path = Path(setup['adaface_local'])
    old_directory = Path.cwd()
    try:
        os.chdir(model_path)
        if str(model_path) not in sys.path:
            sys.path.insert(0, str(model_path))
        _MODEL = AutoModel.from_pretrained(
            str(model_path), trust_remote_code=True, local_files_only=True
        ).to('cuda').eval()
    finally:
        os.chdir(old_directory)
    _PROVENANCE = {
        'model': 'AdaFace',
        'model_revision': setup['adaface_revision'],
        'checkpoint_sha256': setup['hashes'].get(str(model_path / 'model.safetensors')),
        'preprocessing': PREPROCESSING,
        'dimension': 512,
        'dtype': 'float32',
        'normalized': True,
    }
    return _MODEL


def embed(input_path):
    """Create one normalized 512-value AdaFace vector from an image path."""
    import cv2
    import numpy as np
    import torch

    image = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
    if image is None or min(image.shape[:2]) < 16:
        raise ValueError(f'Unreadable or tiny face crop: {input_path}')
    rgb = cv2.cvtColor(cv2.resize(image, (112, 112), interpolation=cv2.INTER_CUBIC),
                       cv2.COLOR_BGR2RGB)
    tensor = torch.from_numpy(np.transpose(rgb, (2, 0, 1))).float().unsqueeze(0).to('cuda')
    tensor = tensor / 255.0
    tensor = (tensor - 0.5) / 0.5
    with torch.inference_mode():
        output = get_model()(tensor)
    vector = output[0] if isinstance(output, (tuple, list)) else output
    vector = vector.detach().float().cpu().numpy().reshape(-1)
    norm = float(np.linalg.norm(vector))
    if vector.size != 512 or not np.isfinite(vector).all() or norm <= 0:
        raise RuntimeError(f'Invalid AdaFace embedding for {input_path}')
    return (vector / norm).astype(np.float32)


def export_metadata():
    if _PROVENANCE is None:
        raise RuntimeError('AdaFace has not generated an embedding yet.')
    return _PROVENANCE
