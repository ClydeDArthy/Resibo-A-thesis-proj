"""Portable image-processing exchange. No recognition or CCTV identification."""
from pathlib import Path
import argparse, importlib, io, json, tempfile, zipfile
from PIL import Image, __version__ as pillow_version
from app import check_zip, digest, image_info, json_bytes, now

def run(request_zip, output_zip, method='resize512_smoke', adapter=None,
    checkpoint_sha256=None, embedding_adapter=None):
    """Ito yung function na gets request.zip, processes all images, returns results.zip."""
    if output_zip.exists(): raise ValueError('Output ZIP already exists')
    restore = None
    embed = None
    if method=='external_restoration':
        if not adapter or not checkpoint_sha256 or len(checkpoint_sha256)!=64:
            raise ValueError('External restoration needs module:function and checkpoint SHA-256')
        module,attribute=adapter.split(':',1)
        adapter_module=importlib.import_module(module)
        restore=getattr(adapter_module,attribute)
    elif method!='resize512_smoke':
        raise ValueError('Unsupported processing method')
    if embedding_adapter:
        module,attribute=embedding_adapter.split(':',1)
        embed_module=importlib.import_module(module)
        embed=getattr(embed_module,attribute)
    with zipfile.ZipFile(request_zip) as z:
        check_zip(z)
        raw=z.read('request.json'); request=json.loads(raw)
        if request.get('schema_version')!=1 or request.get('purpose')!='research_image_processing':
            raise ValueError('Not a supported research image job')
        items=request['inputs']
        if not items or len({i['asset_id'] for i in items})!=len(items):
            raise ValueError('Empty or duplicate inputs')
        outputs=[]
        embedding_outputs={}
        embedding_references=[]
        embedding_provenance=None
        # Validate all original bytes before invoking a GPU adapter.
        for item in items:
            data=z.read(item['zip_path']); image_info(data)
            if digest(data)!=item['sha256']: raise ValueError('Input hash mismatch')
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            for number,item in enumerate(items):
                data=z.read(item['zip_path'])
                source=folder/f'{number}_source.img'; destination=folder/f'{number}_output.png'
                source.write_bytes(data)
                if restore:
                    restore(source,destination)
                else:
                    with Image.open(io.BytesIO(data)) as image:
                        image.convert('RGB').resize((512,512),Image.Resampling.BICUBIC).save(destination)
                result=destination.read_bytes(); _,_,mime=image_info(result)
                if mime!='image/png': raise ValueError('Adapter must produce a PNG')
                # Save the resized derivative separately when the model adapter provides it.
                prepared=destination.with_name(destination.stem+'_Resized512.png')
                prepared_data=prepared.read_bytes() if prepared.is_file() else None
                if prepared_data is not None: image_info(prepared_data)
                outputs.append((item,result,prepared_data))
        if embed:
            import numpy as np
            references=request.get('references') or []
            if not references:
                raise ValueError('Embedding mode requires reference images in the request')
            with tempfile.TemporaryDirectory() as embedding_temp:
                folder=Path(embedding_temp)
                reference_vectors=[]
                for reference in references:
                    path=folder/(reference['asset_id']+'.img')
                    path.write_bytes(z.read(reference['zip_path']))
                    vector=np.asarray(embed(path),dtype=np.float32).reshape(-1)
                    if vector.size != 512 or not np.isfinite(vector).all():
                        raise ValueError('Embedding adapter must return a finite 512-value vector')
                    vector=vector/np.linalg.norm(vector)
                    data=vector.astype(np.float32).tobytes()
                    member='embeddings/references/'+reference['asset_id']+'.bin'
                    embedding_references.append({'asset_id':reference['asset_id'],
                        'source_relpath':reference['source_relpath'],
                        'subject_id':reference['source_relpath'].split('/')[0],
                        'zip_path':member,'sha256':digest(data),'data':data})
                    reference_vectors.append((reference,vector))
                for item,result,_ in outputs:
                    path=folder/(item['asset_id']+'.png'); path.write_bytes(result)
                    vector=np.asarray(embed(path),dtype=np.float32).reshape(-1)
                    if vector.size != 512 or not np.isfinite(vector).all():
                        raise ValueError('Embedding adapter must return a finite 512-value vector')
                    vector=vector/np.linalg.norm(vector)
                    data=vector.astype(np.float32).tobytes()
                    member='embeddings/queries/'+item['asset_id']+'.bin'
                    ranked=[]
                    for reference,reference_vector in reference_vectors:
                        ranked.append((float(np.dot(vector,reference_vector)),reference))
                    ranked.sort(key=lambda pair:(-pair[0],pair[1]['asset_id']))
                    embedding_outputs[item['asset_id']]={
                        'zip_path':member,'sha256':digest(data),'data':data,
                        'dimension':512,'dtype':'float32',
                        'candidates':[{'rank':rank,'reference_asset_id':reference['asset_id'],
                                      'reference_subject_id':reference['source_relpath'].split('/')[0],
                                      'cosine_similarity':score}
                                     for rank,(score,reference) in enumerate(ranked[:5],1)]}
            if hasattr(embed_module, 'export_metadata'):
                embedding_provenance=embed_module.export_metadata()
        worker={'method':method,'adapter':adapter,'checkpoint_sha256':checkpoint_sha256,
            'embedding_adapter':embedding_adapter,
            'embedding_provenance':embedding_provenance,
            'pillow_version':pillow_version,'completed_utc':now(),
            'is_model_inference':method=='external_restoration',
            'note':'Resize smoke test is not model enhancement or recognition.' if not restore else
                   'External research restoration adapter; caller supplies model environment.'}
    if restore and hasattr(adapter_module,'export_metadata'):
        worker['model_provenance']=adapter_module.export_metadata()
        actual=worker['model_provenance'].get('checkpoint_sha256')
        if actual is not None and actual!=checkpoint_sha256:
            raise ValueError('Declared checkpoint hash differs from the verified adapter checkpoint')
        if worker['model_provenance'].get('model')=='OSDFace' and any(prepared is None for _,_,prepared in outputs):
            raise ValueError('An OSDFace job must retain every resized input separately')
    manifest={'schema_version':1,'job_id':request['job_id'],'request_sha256':digest(raw),
              'worker':worker,'outputs':[],
              'references':[{key:value for key,value in row.items() if key!='data'}
                            for row in embedding_references]}
    output_zip.parent.mkdir(parents=True,exist_ok=True)
    temp_out=output_zip.with_name(output_zip.name+'.part')
    try:
        with zipfile.ZipFile(temp_out,'w',zipfile.ZIP_DEFLATED) as z:
            for item,result,prepared_data in outputs:
                name='outputs/'+item['asset_id']+'.png'
                z.writestr(name,result)
                record={'input_asset_id':item['asset_id'],'source_sha256':item['sha256'],
                        'zip_path':name,'sha256':digest(result)}
                if prepared_data is not None:
                    prepared_name='prepared/'+item['asset_id']+'_Resized512.png'
                    z.writestr(prepared_name,prepared_data)
                    record['prepared']={'zip_path':prepared_name,'sha256':digest(prepared_data)}
                if item['asset_id'] in embedding_outputs:
                    embedding={key:value for key,value in embedding_outputs[item['asset_id']].items()
                               if key!='data'}
                    record['embedding']=embedding
                manifest['outputs'].append(record)
            for row in embedding_references:
                z.writestr(row['zip_path'],row['data'])
            for row in embedding_outputs.values():
                z.writestr(row['zip_path'],row['data'])
            z.writestr('results.json',json_bytes(manifest))
        temp_out.replace(output_zip)
    finally:
        if temp_out.exists(): temp_out.unlink()
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--request',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--method',choices=['resize512_smoke','external_restoration'],default='resize512_smoke')
    p.add_argument('--adapter'); p.add_argument('--checkpoint-sha256')
    p.add_argument('--embedding-adapter', help='module:function returning a normalized 512-value vector')
    args=p.parse_args()
    result=run(args.request,args.out,args.method,args.adapter,args.checkpoint_sha256,args.embedding_adapter)
    print(json.dumps({'job_id':result['job_id'],'images':len(result['outputs']),'method':args.method},indent=2))
