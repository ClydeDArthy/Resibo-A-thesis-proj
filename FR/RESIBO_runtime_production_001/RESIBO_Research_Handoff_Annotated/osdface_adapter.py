"""Ito yung Colab-only file na nagre-restore ng research images using OSDFace.

It gets an original image path and writes an enhanced PNG plus its resized input.
Walang AdaFace, candidate matching, or CCTV identification dito.
"""
from pathlib import Path
from argparse import Namespace
import hashlib, json, os, subprocess, sys
from importlib.metadata import version

_MODEL = None
_PROVENANCE = None

def sha_file(path):
    """Compute a file hash without loading a large checkpoint into RAM."""
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20), b''): h.update(block)
    return h.hexdigest()

def get_model():
    """Load the verified OSDFace model once, then reuse it for the whole job."""
    global _MODEL, _PROVENANCE
    if _MODEL is not None: return _MODEL
    os.environ['USE_TF']='0'
    import torch
    setup_file=Path('/content/resibo_setup/ready.json')
    if not setup_file.is_file():
        raise RuntimeError('Run colab_setup_osdface.py successfully, then restart the session first.')
    setup=json.loads(setup_file.read_text())
    if setup.get('status')!='PASSED': raise RuntimeError('OSDFace preflight did not pass')
    if not torch.cuda.is_available(): raise RuntimeError('Select a Colab GPU runtime')
    for name,expected in setup['versions'].items():
        if version(name)!=expected: raise RuntimeError(f'{name} changed after preflight')
    for filename,expected in setup['hashes'].items():
        if not Path(filename).is_file() or sha_file(filename)!=expected:
            raise RuntimeError(f'Changed/missing preflight artifact: {filename}')
    repo=Path(setup['repo'])
    commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    if commit!=setup['osdface_commit']: raise RuntimeError('OSDFace source revision changed')
    sys.path.insert(0,str(repo))
    from infer import OSDFace_test
    weights=repo/'pretrained'
    args=Namespace(pretrained_model_name_or_path=setup['sd_local'],ckpt_path=str(weights),
                   img_encoder_weight=str(weights/'associate_2.ckpt'),merge_lora=False,
                   mixed_precision='fp16',cat_prompt_embedding=False,use_pos_embedding=False,
                   use_att_pool=False,lora_rank=16,lora_alpha=16)
    torch.cuda.set_device(0)
    _MODEL=OSDFace_test(args,0,None).to('cuda:0').eval()
    _PROVENANCE={'model':'OSDFace','checkpoint_sha256':sha_file(weights/'pytorch_lora_weights.safetensors'),
                 'setup':setup,'input_preparation':'OpenCV INTER_CUBIC RGB resize to 512x512; [-1,1] tensor',
                 'precision':'fp16','seed':114,'seed_policy':'same seed reset for each research image',
                 'note':'Seed recording does not guarantee bitwise reproducibility across GPU/library versions.'}
    return _MODEL

def restore(input_path, output_path):
    """Preserve the source, save its 512x512 model input, then save OSDFace output."""
    import cv2, numpy as np, torch
    from PIL import Image
    model=get_model()
    image=cv2.imread(str(input_path),cv2.IMREAD_COLOR)
    if image is None or min(image.shape[:2])<16:
        raise ValueError('Unreadable or smaller-than-16-pixel source crop')
    prepared=cv2.resize(image,(512,512),interpolation=cv2.INTER_CUBIC)
    prepared_path=Path(output_path).with_name(Path(output_path).stem+'_Resized512.png')
    if not cv2.imwrite(str(prepared_path),prepared): raise RuntimeError('Failed to save resized input')
    rgb=prepared[:,:,::-1].copy()
    tensor=torch.from_numpy(np.transpose(rgb,(2,0,1))).unsqueeze(0).to('cuda',dtype=torch.float16)/255
    tensor=tensor*2-1
    torch.manual_seed(114); torch.cuda.manual_seed_all(114)
    with torch.inference_mode(): result=model(tensor)
    if result.shape!=(1,3,512,512) or not bool(torch.isfinite(result).all()):
        raise RuntimeError('Invalid OSDFace output; do not create a successful result package')
    pixels=(result[0].detach().float().cpu().clamp(0,1).permute(1,2,0).numpy()*255).astype('uint8')
    Image.fromarray(pixels).save(output_path)

def export_metadata():
    """Return the actual source/checkpoint/setup provenance used for this job."""
    if _PROVENANCE is None: raise RuntimeError('OSDFace was not run')
    return _PROVENANCE
