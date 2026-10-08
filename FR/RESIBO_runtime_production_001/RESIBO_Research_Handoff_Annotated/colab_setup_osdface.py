# Ito yung Colab setup file: downloads OSDFace weights, checks LoRA, and records ready.json.
# It does not process the datasets, run AdaFace, or write the laptop database.
# Colab-only setup: install OSDFace dependencies, verify checkpoints, and run a synthetic GPU check.
# Choose a GPU runtime first. This cell does NOT process the FRMDB dataset.
import sys, os, json, subprocess
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError
os.environ['USE_TF'] = '0'
BASE = Path('/content/resibo_setup')
BASE.mkdir(parents=True, exist_ok=True)
(BASE / 'ready.json').unlink(missing_ok=True)

# Preserve Colab's installed CUDA-enabled torch / torchvision pair.
constraints = BASE / 'torch_constraints.txt'
constraints.write_text(''.join(f'{name}=={version(name)}\n' for name in ['torch', 'torchvision']))
subprocess.run([sys.executable, '-c',
    "import torch, torchvision; assert torch.cuda.is_available(), 'Select a GPU runtime'; "
    "print('GPU:', torch.cuda.get_device_name(0), flush=True)"], check=True)

# torchao is an unused optional quantization backend in this OSDFace path.
subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'torchao'], check=True)
PACKAGES = [
    'diffusers==0.35.1', 'transformers==4.56.2', 'peft==0.17.1',
    'accelerate==1.10.1', 'huggingface-hub==0.35.3',
    'pytorch-lightning==2.6.6', 'omegaconf==2.3.0',
    'safetensors>=0.6.2,<1', 'einops>=0.8,<1',
    'fvcore==0.1.5.post20221221', 'iopath==0.1.10', 'PyYAML>=6,<7',
    'timm>=1.0,<2', 'torchmetrics>=1.8,<2', 'librosa>=0.11,<1',
    'opencv-python-headless>=4.11,<5', 'matplotlib>=3.10,<4',
    'pandas>=2.2,<3', 'pillow>=11,<13', 'scikit-image>=0.25,<1',
    'scipy>=1.15,<2', 'imageio>=2.37,<3', 'tqdm>=4.67,<5',
]
subprocess.run([sys.executable, '-m', 'pip', 'install',
    '--upgrade-strategy', 'only-if-needed', '-c', str(constraints), *PACKAGES], check=True)
subprocess.run([sys.executable, '-c', "import importlib.util; assert importlib.util.find_spec('torchao') is None, 'torchao is still installed'"], check=True)

PREFLIGHT_CODE = r"""


import os, sys, json, hashlib, subprocess, datetime, gc, io, sqlite3
os.environ['USE_TF'] = '0'
os.environ['MPLBACKEND'] = 'Agg'
from pathlib import Path
from importlib.metadata import version
import numpy as np, cv2, pandas as pd, matplotlib.pyplot as plt
import torch, torchvision, pytorch_lightning, omegaconf, yaml, einops
import fvcore, iopath, imageio, scipy, skimage, safetensors, peft, transformers, accelerate
from PIL import Image
from torchvision.ops import nms
from huggingface_hub import HfApi, hf_hub_download, snapshot_download
from transformers import AutoModel
from safetensors.torch import load_file

BASE = Path('/content/resibo_setup')
BASE.mkdir(exist_ok=True)
READY = BASE / 'ready.json'
assert torch.cuda.is_available(), 'Select a GPU runtime before Cell 1.'
assert nms(torch.tensor([[0.,0.,2.,2.]]), torch.tensor([1.]), .5).numel() == 1
print('Imports and torchvision operators: PASS', flush=True)
props = torch.cuda.get_device_properties(0)
print('GPU:', props.name, '| VRAM GiB:', round(props.total_memory / 2**30, 2), flush=True)

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda: f.read(2**20), b''):
            h.update(chunk)
    return h.hexdigest()

# Check the downstream image, plotting and SQLite BLOB operations now.
sample = np.full((112, 112, 3), 128, dtype=np.uint8)
ok, encoded = cv2.imencode('.png', sample)
assert ok
payload = encoded.tobytes()
Image.open(io.BytesIO(payload)).verify()
with sqlite3.connect(':memory:') as db:
    db.execute('CREATE TABLE test (image BLOB NOT NULL)')
    db.execute('INSERT INTO test VALUES (?)', (payload,))
    assert db.execute('SELECT image FROM test').fetchone()[0] == payload
fig, ax = plt.subplots()
ax.imshow(sample)
fig.savefig(BASE / 'plot_smoke.png')
plt.close(fig)
assert len(pd.DataFrame([{'ok': True}])) == 1
print('Image / plot / SQLite BLOB checks: PASS', flush=True)

REPO = Path('/content/OSDFace')
if not (REPO / 'infer.py').is_file():
    subprocess.run(['git', 'clone', 'https://github.com/jkwang28/OSDFace.git', str(REPO)], check=True)
assert (REPO / '.git').is_dir(), 'OSDFace folder must be a Git checkout.'
commit = subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip()

# Preserve the upstream file; propagate GPU-worker failures in future Section 5 runs.
infer_path = REPO / 'infer.py'
code = infer_path.read_text()
marker = '# RESIBO: propagate worker failures'
if marker not in code:
    old = '    for p in processes:\n        p.join()'
    assert code.count(old) == 1, 'Upstream process loop changed; inspect infer.py before patching.'
    new = old + '\n\n    ' + marker + '\n    failed = [p.exitcode for p in processes if p.exitcode != 0]\n    if failed:\n        raise RuntimeError(f"OSDFace GPU worker failed: {failed}")'
    backup = BASE / 'infer_upstream.py'
    if not backup.exists():
        backup.write_text(code)
    code = code.replace(old, new)
    infer_path.write_text(code)

LOADER_SOURCE = "\n# Strict OSDFace adapter loader for the supplied mixed-format LoRA checkpoint.\n# Retains dynamic, unmerged LoRA with the upstream rank/alpha. No training.\n# Uses PEFT's low-level API so Diffusers does not discard legacy attention keys.\nimport torch\nfrom safetensors.torch import load_file\nfrom peft import LoraConfig, inject_adapter_in_model, set_peft_model_state_dict, get_peft_model_state_dict\nfrom pathlib import Path\n\ndef canonical_key(key):\n    if key.startswith('unet.'):\n        key = key[5:]\n    return key.replace('.lora.down.weight', '.lora_A.weight').replace('.lora.up.weight', '.lora_B.weight')\n\ndef normalize_checkpoint(raw):\n    normalized = {}\n    for original, value in raw.items():\n        key = canonical_key(original)\n        if not key.endswith(('.lora_A.weight', '.lora_B.weight')):\n            raise ValueError(f'Unsupported OSDFace adapter key; stop rather than skip: {original}')\n        if key in normalized:\n            raise ValueError(f'Duplicate adapter mapping: {original} -> {key}')\n        normalized[key] = value\n    if not normalized:\n        raise ValueError('Empty OSDFace LoRA checkpoint.')\n    return normalized\n\ndef verify_adapter(model, expected, adapter):\n    actual = get_peft_model_state_dict(model, adapter_name=adapter)\n    if set(actual) != set(expected):\n        raise ValueError(f'LoRA keys differ: missing={sorted(set(expected)-set(actual))[:10]}, '\n                         f'extra={sorted(set(actual)-set(expected))[:10]}')\n    for key, source in expected.items():\n        target = actual[key].detach().cpu()\n        if source.shape != target.shape or not torch.equal(source.to(target.dtype), target):\n            raise ValueError(f'LoRA tensor value/shape mismatch: {key}')\n\ndef load_verified_osdface_lora(unet, checkpoint_dir, rank=16, alpha=16):\n    # The supplied infer.py uses rank=16 and alpha=16 by default.\n    raw = load_file(str(Path(checkpoint_dir) / 'pytorch_lora_weights.safetensors'), device='cpu')\n    state = normalize_checkpoint(raw)\n    targets = sorted(k[:-len('.lora_A.weight')] for k in state if k.endswith('.lora_A.weight'))\n    if not targets:\n        raise ValueError('No LoRA A/B pairs found.')\n    if len(state) != 2 * len(targets):\n        raise ValueError('Every LoRA module must have exactly one A and one B tensor.')\n    for name in targets:\n        a = state[name + '.lora_A.weight']\n        bkey = name + '.lora_B.weight'\n        if bkey not in state:\n            raise ValueError(f'Missing LoRA B tensor: {name}')\n        b = state[bkey]\n        module = unet.get_submodule(name)\n        if not isinstance(module, (torch.nn.Linear, torch.nn.Conv2d)):\n            raise ValueError(f'Unsupported target module type: {name}: {type(module).__name__}')\n        if a.ndim not in (2, 4) or b.ndim != a.ndim or a.shape[0] != rank or b.shape[1] != rank:\n            raise ValueError(f'Rank or tensor layout mismatch: {name}: {tuple(a.shape)}, {tuple(b.shape)}')\n    adapter = 'resibo_verified'\n    config = LoraConfig(r=rank, lora_alpha=alpha, target_modules=targets,\n                        lora_dropout=0., bias='none', inference_mode=True, use_rslora=False)\n    unet = inject_adapter_in_model(config, unet, adapter_name=adapter)\n    result = set_peft_model_state_dict(unet, state, adapter_name=adapter)\n    missing_adapter = [k for k in result.missing_keys if '.lora_' in k]\n    if result.unexpected_keys or missing_adapter:\n        raise ValueError(f'Incomplete LoRA assignment: missing={missing_adapter[:10]}, '\n                         f'unexpected={result.unexpected_keys[:10]}')\n    verify_adapter(unet, state, adapter)\n    # Also verify the effective multiplier; equality of A/B alone is insufficient.\n    for name in targets:\n        scale = float(unet.get_submodule(name).scaling[adapter])\n        if scale != float(alpha / rank):\n            raise ValueError(f'Wrong LoRA scaling for {name}: {scale}')\n    print(f'Verified OSDFace LoRA: {len(targets)} modules / {len(state)} tensors; '\n          f'rank={rank}, alpha={alpha}, scale={alpha/rank}', flush=True)\n    return unet\n"
# Keep the same dynamic LoRA branch, but load every legacy/PEFT tensor explicitly.
loader_path = REPO / 'resibo_lora_loader.py'
loader_path.write_text(LOADER_SOURCE)
loader_marker = '# RESIBO: strict mixed-format LoRA loader'
if loader_marker not in code:
    begin = code.find('            pipe = StableDiffusionPipeline(')
    end_text = '            self.unet = pipe.unet'
    end = code.find(end_text, begin)
    assert begin >= 0 and end > begin, 'Upstream LoRA loader changed; inspect infer.py.'
    replacement = (
        '            ' + loader_marker + '\n'
        '            from resibo_lora_loader import load_verified_osdface_lora\n'
        '            self.unet = load_verified_osdface_lora(\n'
        '                self.unet, ckpt_path, rank=self.args.lora_rank, alpha=self.args.lora_alpha)'
    )
    code = code[:begin] + replacement + code[end + len(end_text):]
    infer_path.write_text(code)

api = HfApi()
osd_revision = api.model_info('alecccdd/OSDFace').sha
sd_revision = api.model_info('Manojb/stable-diffusion-2-1-base').sha
ada_revision = api.model_info('minchul/cvlface_adaface_ir50_webface4m').sha
weights = REPO / 'pretrained'
weights.mkdir(exist_ok=True)
for name in ['associate_2.ckpt', 'embedding_change_weights.pth', 'pytorch_lora_weights.safetensors']:
    hf_hub_download('alecccdd/OSDFace', name, revision=osd_revision, local_dir=str(weights))

# Only OSDFace's scheduler / VAE / UNet are needed; no text encoder download.
SD_LOCAL = BASE / 'sd21'
snapshot_download('Manojb/stable-diffusion-2-1-base', revision=sd_revision,
                  local_dir=str(SD_LOCAL), allow_patterns=['scheduler/*', 'vae/*', 'unet/*'])
ADAFACE_LOCAL = BASE / 'adaface_ir50'
snapshot_download('minchul/cvlface_adaface_ir50_webface4m', revision=ada_revision,
                  local_dir=str(ADAFACE_LOCAL))
print('Required OSDFace and AdaFace files downloaded with recorded revisions.', flush=True)

# Same unmerged LoRA / fp16 / 512-pixel path as Section 5, on a synthetic gray image.
# This is a wiring test; it is not face-quality or recognition validation.
os.chdir(REPO)
sys.path.insert(0, str(REPO))
from argparse import Namespace
from infer import OSDFace_test
torch.manual_seed(114)
torch.cuda.manual_seed_all(114)
args = Namespace(pretrained_model_name_or_path=str(SD_LOCAL), ckpt_path=str(weights),
                 img_encoder_weight=str(weights / 'associate_2.ckpt'), merge_lora=False,
                 mixed_precision='fp16', cat_prompt_embedding=False,
                 use_pos_embedding=False, use_att_pool=False, lora_rank=16, lora_alpha=16)
print('OSDFace: loading actual checkpoint and LoRA...', flush=True)
restorer = OSDFace_test(args, 0, None).to('cuda:0').eval()

# Verify all LoRA tensor values against the downloaded file, instead of hiding warnings.
from peft import get_peft_model_state_dict
adapter = next(iter(restorer.unet.peft_config))
loaded = get_peft_model_state_dict(restorer.unet, adapter_name=adapter)
def canonical(key):
    if key.startswith('unet.'):
        key = key[5:]
    return key.replace('.lora.down.weight', '.lora_A.weight').replace('.lora.up.weight', '.lora_B.weight')
expected = {canonical(k): v for k, v in load_file(str(weights / 'pytorch_lora_weights.safetensors')).items()}
actual = {canonical(k): v for k, v in loaded.items()}
assert expected and set(expected) == set(actual), (
    f'LoRA key mismatch: missing={sorted(set(expected)-set(actual))[:8]}, '
    f'extra={sorted(set(actual)-set(expected))[:8]}. Stop; do not use results.')
for key, source in expected.items():
    target = actual[key].detach().cpu()
    assert source.shape == target.shape and torch.equal(source.to(target.dtype), target), f'LoRA tensor mismatch: {key}'
print('LoRA keys and tensor values: PASS', len(expected), 'tensors', flush=True)
del expected, actual, loaded
with torch.inference_mode():
    restored = restorer(torch.zeros((1, 3, 512, 512), device='cuda', dtype=torch.float16))
assert restored.shape == (1, 3, 512, 512) and bool(torch.isfinite(restored).all())
torchvision.transforms.ToPILImage()(restored[0].float().cpu()).save(BASE / 'osdface_synthetic_smoke.png')
del restorer, restored
gc.collect()
torch.cuda.empty_cache()
print('OSDFace single-image GPU smoke test: PASS', flush=True)

# Verify the AdaFace checkpoint and its 512-value normalized embedding contract.
old_directory = os.getcwd()
try:
    os.chdir(ADAFACE_LOCAL)
    sys.path.insert(0, str(ADAFACE_LOCAL))
    recognizer = AutoModel.from_pretrained(str(ADAFACE_LOCAL), trust_remote_code=True,
                                           local_files_only=True).to('cuda').eval()
finally:
    os.chdir(old_directory)
with torch.inference_mode():
    sample = torch.zeros((1, 3, 112, 112), device='cuda')
    output = recognizer(sample)
    vector = output[0] if isinstance(output, (tuple, list)) else output
    vector = vector.detach().float().cpu().numpy().reshape(-1)
assert vector.size == 512 and np.isfinite(vector).all() and np.linalg.norm(vector) > 0
del recognizer, sample, output, vector
gc.collect()
torch.cuda.empty_cache()
print('AdaFace load / 512-value GPU embedding smoke test: PASS', flush=True)

versions = {name: version(name) for name in [
    'torch', 'torchvision', 'diffusers', 'transformers', 'peft', 'accelerate',
    'huggingface-hub', 'pytorch-lightning', 'omegaconf', 'numpy', 'pandas',
    'opencv-python-headless', 'matplotlib', 'pillow', 'einops', 'fvcore',
    'iopath', 'safetensors', 'torchmetrics', 'imageio', 'scipy', 'scikit-image', 'timm']}
tracked = [infer_path, loader_path, *(weights / n for n in [
    'associate_2.ckpt', 'embedding_change_weights.pth', 'pytorch_lora_weights.safetensors'])]
tracked += [p for p in ADAFACE_LOCAL.rglob('*') if p.is_file() and '.cache' not in p.parts]
tracked += [p for p in SD_LOCAL.rglob('*') if p.is_file() and '.cache' not in p.parts]
manifest = dict(status='PASSED', versions=versions, python=sys.version,
                gpu=props.name, gpu_memory_bytes=props.total_memory,
                osdface_commit=commit, osdface_weights_revision=osd_revision,
                lora_loading='STRICT_MIXED_FORMAT_PEFT_UNMERGED_v1', lora_rank=16, lora_alpha=16,
                sd_revision=sd_revision, adaface_revision=ada_revision,
                repo=str(REPO), sd_local=str(SD_LOCAL), adaface_local=str(ADAFACE_LOCAL),
                hashes={str(p): sha(p) for p in tracked},
                completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                scope='Synthetic OSDFace/AdaFace wiring and dependency preflight; FRMDB run not executed.')
READY.write_text(json.dumps(manifest, indent=2))
print('PREFLIGHT PASSED. Restart the session once, then run the handoff job cells.', flush=True)


"""
preflight_path = BASE / 'preflight.py'
preflight_path.write_text(PREFLIGHT_CODE)
log_file = BASE / 'preflight.log'
print('Running import, checkpoint, LoRA and GPU smoke checks. Large model downloads may take several minutes.')
with log_file.open('w') as log:
    process = subprocess.Popen([sys.executable, '-u', str(preflight_path)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in process.stdout:
        print(line, end='')
        log.write(line)
        log.flush()
    result = process.wait()
if result != 0:
    raise RuntimeError(f'Cell 1 preflight FAILED. Stay here; do not run Section 2. Log: {log_file}')
assert (BASE / 'ready.json').is_file()
print('PREFLIGHT PASSED — Restart session, then continue with the handoff job cells. No extra dependency-fix cells are needed.')
