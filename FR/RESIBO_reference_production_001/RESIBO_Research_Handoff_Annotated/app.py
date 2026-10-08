"""Ito yung local VSCode file: dataset intake -> SQLite -> Colab ZIP exchange -> reports.
It gets PNG/JPEG files and returned result ZIPs. It never runs GPU models locally.
"""
from pathlib import Path, PurePosixPath
import argparse, base64, datetime, hashlib, io, json, random, re, sqlite3, uuid, zipfile
from html import escape
from PIL import Image

BASE = Path(__file__).resolve().parent
EXTENSIONS = {'.png', '.jpg', '.jpeg'}

def now():
    """Return a UTC timestamp audit records are consistent."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def digest(data):
    """Compute SHA-256 of bytes."""
    return hashlib.sha256(data).hexdigest()

def json_bytes(value):
    """Serialize manifests consistently before hashing them."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def image_info(data):
    """Validate image bytes and read dimensions."""
    with Image.open(io.BytesIO(data)) as im:
        im.verify()
    with Image.open(io.BytesIO(data)) as im:
        if im.format not in {'PNG', 'JPEG'}:
            raise ValueError('Only PNG and JPEG images are supported')
        return im.width, im.height, 'image/png' if im.format == 'PNG' else 'image/jpeg'

def input_metadata(source_relpath, role):
    """Preserve future tracked-crop IDs without inventing them for flat datasets."""
    metadata = {'input_layout': 'dataset_relative', 'is_video_track': False}
    if role != 'input':
        return metadata
    parts = PurePosixPath(source_relpath).parts
    track_part = next((part for part in parts if part.startswith('TrackedIdentity')), None)
    frame_match = re.fullmatch(r'(TI[^/]+)_Frame(\d+)', PurePosixPath(source_relpath).stem)
    if track_part and frame_match:
        metadata.update({'input_layout': 'tracked_face_v1', 'is_video_track': True,
                         'track_id': track_part, 'track_image_id': frame_match.group(1),
                         'frame_number': int(frame_match.group(2))})
    else:
        metadata.update({'input_layout': 'single_image_sample',
                         'track_id': None, 'frame_number': None})
    return metadata

def connect(workspace):
    """Open the same SQLite file used by DBeaver and enable foreign-key checks."""
    workspace.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(workspace / 'research.sqlite', timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=30000')
    db.executescript((BASE / 'schema.sql').read_text())
    db.commit()
    return db

def audit(db, action, object_id, details):
    """Append an operation record. These are the history of the imports, jobs, and reports."""
    db.execute('INSERT INTO audit_events(action,object_id,details_json,created_utc) VALUES(?,?,?,?)',
               (action,object_id,json_bytes(details).decode(),now()))

def store_asset(db, workspace, asset_id, dataset_id, source_relpath, role, data, metadata, parent=None):
    """Save unchanged bytes as a file and image BLOB, with a separate hash and parent link."""
    width,height,mime = image_info(data)
    sha = digest(data)
    relative = f'objects/{sha[:2]}/{sha}.{"png" if mime=="image/png" else "jpg"}'
    path = workspace / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if digest(path.read_bytes()) != sha:
            raise ValueError(f'Corrupt local image: {path}')
    else:
        temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.part')
        temp.write_bytes(data)
        temp.replace(path)
    db.execute('INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
               (asset_id,dataset_id,source_relpath,role,parent,sha,mime,width,height,
                len(data),relative,data,json_bytes(metadata).decode(),now()))

def ingest(db, workspace, dataset_id, folder, role, version, url):
    """Intake of reference/input files: validates PNG/JPEG files and avoids duplicate reimports."""
    folder = folder.resolve()
    if not folder.is_dir():
        raise ValueError(f'Folder not found: {folder}')
    paths = sorted(p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in EXTENSIONS)
    if not paths:
        raise ValueError('No PNG/JPEG images found')
    existing = db.execute('SELECT * FROM datasets WHERE dataset_id=?',(dataset_id,)).fetchone()
    if existing and (existing['source_version']!=version or existing['source_url']!=url):
        raise ValueError('Dataset provenance changed; use a new dataset ID')
    # Validate every image before altering the database.
    new = []
    for path in paths:
        relative = path.relative_to(folder).as_posix()
        data = path.read_bytes()
        image_info(data)
        old = db.execute('SELECT sha256,role FROM assets WHERE dataset_id=? AND source_relpath=?',
                         (dataset_id,relative)).fetchone()
        if old:
            if old['sha256']!=digest(data) or old['role']!=role:
                raise ValueError(f'Changed source or role: {relative}; use a new dataset ID')
        else:
            new.append((relative,data))
    with db:
        if not existing:
            db.execute('INSERT INTO datasets VALUES(?,?,?,?,?)',
                       (dataset_id,url,version,'research_image_processing',now()))
        for relative,data in new:
            asset_id = uuid.uuid5(uuid.NAMESPACE_URL,dataset_id+'/'+relative).hex
            store_asset(db,workspace,asset_id,dataset_id,relative,role,data,
                        {'dataset_folder':relative.split('/')[0], **input_metadata(relative, role)})
        audit(db,'INGEST',dataset_id,{'added':len(new),'unchanged':len(paths)-len(new)})
    return {'added':len(new),'unchanged':len(paths)-len(new)}

def freeze(db, set_id, dataset_ids):
    """The fixed reference database membership; freezes selected images under a version ID."""
    if db.execute('SELECT 1 FROM reference_sets WHERE reference_set_id=?',(set_id,)).fetchone():
        raise ValueError('Reference set ID already exists; choose a new version name')
    for dataset_id in dataset_ids:
        if not db.execute("SELECT 1 FROM assets WHERE dataset_id=? AND role='reference'",(dataset_id,)).fetchone():
            raise ValueError(f'No reference assets for {dataset_id}')
    marks = ','.join('?' for _ in dataset_ids)
    rows = db.execute(f"SELECT asset_id,sha256 FROM assets WHERE role='reference' AND dataset_id IN ({marks}) ORDER BY asset_id",dataset_ids).fetchall()
    hashes = [r['sha256'] for r in rows]
    if len(hashes)!=len(set(hashes)):
        raise ValueError('Duplicate image bytes in reference selection')
    fingerprint = digest(json_bytes([dict(r) for r in rows]))
    with db:
        db.execute('INSERT INTO reference_sets VALUES(?,?,?,?,?)',
                   (set_id,fingerprint,'Frozen research references; no criminal status asserted',0,now()))
        db.executemany('INSERT INTO reference_members VALUES(?,?)',[(set_id,r['asset_id']) for r in rows])
        db.execute('UPDATE reference_sets SET sealed=1 WHERE reference_set_id=?',(set_id,))
        audit(db,'FREEZE_REFERENCES',set_id,{'count':len(rows),'fingerprint':fingerprint})
    return {'reference_set_id':set_id,'images':len(rows),'fingerprint':fingerprint}

def export_job(db, workspace, reference_set_id, dataset_ids, output, limit=None, seed=None,
               reference_stems=None):
    """Gets selected sample input BLOBs; creates request.json and a portable Colab request ZIP."""
    if output.exists():
        raise ValueError('Output ZIP exists; choose another filename')
    refs = db.execute('SELECT * FROM reference_sets WHERE reference_set_id=? AND sealed=1',(reference_set_id,)).fetchone()
    if not refs:
        raise ValueError('A frozen reference set is required')
    for dataset_id in dataset_ids:
        if not db.execute("SELECT 1 FROM assets WHERE dataset_id=? AND role='input'",(dataset_id,)).fetchone():
            raise ValueError(f'No input assets for {dataset_id}')
    marks = ','.join('?' for _ in dataset_ids)
    inputs = db.execute(f"SELECT * FROM assets WHERE role='input' AND dataset_id IN ({marks}) ORDER BY asset_id",dataset_ids).fetchall()
    if limit is not None:
        if limit < 1:
            raise ValueError('Input limit must be positive')
        rng = random.Random(seed)
        inputs = sorted(rng.sample(inputs, min(limit, len(inputs))), key=lambda row: row['asset_id'])
    reference_hashes = {r[0] for r in db.execute('SELECT a.sha256 FROM reference_members r JOIN assets a USING(asset_id) WHERE r.reference_set_id=?',(reference_set_id,))}
    if any(r['sha256'] in reference_hashes for r in inputs):
        raise ValueError('An input duplicates a frozen reference image')
    job_id = uuid.uuid4().hex
    reference_rows = db.execute(
        'SELECT a.* FROM reference_members m JOIN assets a ON a.asset_id=m.asset_id '
        'WHERE m.reference_set_id=? ORDER BY a.asset_id', (reference_set_id,)).fetchall()
    if reference_stems:
        wanted = set(reference_stems)
        reference_rows = [row for row in reference_rows if Path(row['source_relpath']).stem in wanted]
        if not reference_rows:
            raise ValueError('Reference stem selection returned no images')
    request = {'schema_version':1,'job_id':job_id,'reference_set_id':reference_set_id,
               'reference_fingerprint':refs['fingerprint'],'purpose':'research_image_processing',
               'created_utc':now(),'inputs':[],
               'selection':{'limit':limit,'seed':seed,
                             'reference_stems':sorted(reference_stems) if reference_stems else None}}
    for r in inputs:
        suffix = '.png' if r['mime']=='image/png' else '.jpg'
        request['inputs'].append({'asset_id':r['asset_id'],'dataset_id':r['dataset_id'],
                                 'source_relpath':r['source_relpath'],'sha256':r['sha256'],
                                 'metadata':json.loads(r['metadata_json']),
                                 'zip_path':'inputs/'+r['asset_id']+suffix})
    request['references'] = []
    for row in reference_rows:
        suffix = '.png' if row['mime']=='image/png' else '.jpg'
        request['references'].append({'asset_id':row['asset_id'],
                                     'dataset_id':row['dataset_id'],
                                     'source_relpath':row['source_relpath'],
                                     'sha256':row['sha256'],
                                     'metadata':json.loads(row['metadata_json']),
                                     'zip_path':'references/'+row['asset_id']+suffix})
    raw = json_bytes(request)
    output.parent.mkdir(parents=True,exist_ok=True)
    temp = output.with_name(output.name+'.'+job_id+'.part')
    try:
        with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('request.json',raw)
            for r,item in zip(inputs,request['inputs']):
                z.writestr(item['zip_path'],r['image_blob'])
            for row,item in zip(reference_rows,request['references']):
                z.writestr(item['zip_path'],row['image_blob'])
        with db:
            db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?)',
                       (job_id,reference_set_id,digest(raw),raw.decode(),'EXPORTED',now(),None))
            db.executemany('INSERT INTO job_inputs VALUES(?,?)',[(job_id,r['asset_id']) for r in inputs])
            audit(db,'EXPORT_JOB',job_id,{'images':len(inputs),'request_sha256':digest(raw)})
            temp.replace(output)
    finally:
        if temp.exists(): temp.unlink()
    return {'job_id':job_id,'images':len(inputs),'zip':str(output.resolve())}

def check_zip(z):
    """Reject duplicate or unsafe ZIP paths before reading the result package."""
    names = z.namelist()
    if len(names)!=len(set(names)):
        raise ValueError('Duplicate ZIP member names')
    for name in names:
        p = PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name:
            raise ValueError('Unsafe ZIP member name')

def import_results(db, workspace, filename):
    """Gets results.zip; verifies complete membership and hashes, then stores outputs transactionally."""
    with zipfile.ZipFile(filename) as z:
        check_zip(z)
        result = json.loads(z.read('results.json'))
        if result.get('schema_version')!=1:
            raise ValueError('Unsupported results schema')
        job = db.execute('SELECT * FROM jobs WHERE job_id=?',(result['job_id'],)).fetchone()
        if not job or result['request_sha256']!=job['request_sha256']:
            raise ValueError('Unknown job or request fingerprint mismatch')
        expected = {r['asset_id']:r for r in db.execute('SELECT a.* FROM job_inputs i JOIN assets a ON a.asset_id=i.input_asset_id WHERE i.job_id=?',(job['job_id'],))}
        items = result['outputs']
        returned = [i['input_asset_id'] for i in items]
        if len(returned)!=len(set(returned)) or set(returned)!=set(expected):
            raise ValueError('Missing, duplicate, or unexpected results; nothing imported')
        worker = result['worker']
        if not isinstance(worker,dict) or not worker.get('method'):
            raise ValueError('Worker metadata required')
        validated = []
        prepared_images = {}
        embedding_data = {}
        reference_embedding_data = {}
        for item in items:
            source = expected[item['input_asset_id']]
            if item['source_sha256']!=source['sha256']:
                raise ValueError('Original source fingerprint mismatch')
            data = z.read(item['zip_path'])
            image_info(data)
            if digest(data)!=item['sha256']:
                raise ValueError('Output hash mismatch; nothing imported')
            validated.append((source,data))
            if 'prepared' in item:
                prepared_data=z.read(item['prepared']['zip_path'])
                width,height,mime=image_info(prepared_data)
                if (width,height,mime)!=(512,512,'image/png') or digest(prepared_data)!=item['prepared']['sha256']:
                    raise ValueError('Invalid resized model input; nothing imported')
                prepared_images[source['asset_id']]=prepared_data
        if prepared_images and len(prepared_images)!=len(expected):
            raise ValueError('Incomplete resized-input derivatives; nothing imported')
        if result.get('references') or any('embedding' in item for item in items):
            provenance = worker.get('embedding_provenance')
            if not isinstance(provenance, dict) or provenance.get('model') != 'AdaFace':
                raise ValueError('AdaFace embedding provenance required')
            reference_assets = {r['asset_id']: r for r in db.execute(
                'SELECT a.* FROM reference_members m JOIN assets a ON a.asset_id=m.asset_id '
                'WHERE m.reference_set_id=?', (job['reference_set_id'],))}
            for row in result.get('references', []):
                source = reference_assets.get(row['asset_id'])
                if source is None:
                    raise ValueError('Reference embedding is outside the frozen reference set')
                data = z.read(row['zip_path'])
                if len(data) != 512 * 4 or digest(data) != row['sha256']:
                    raise ValueError('Reference embedding hash or dimension mismatch')
                reference_embedding_data[row['asset_id']] = (source, data, row)
            for item in items:
                row = item.get('embedding')
                if row is None:
                    raise ValueError('Incomplete query embeddings')
                data = z.read(row['zip_path'])
                if len(data) != 512 * 4 or digest(data) != row['sha256']:
                    raise ValueError('Query embedding hash or dimension mismatch')
                embedding_data[item['input_asset_id']] = (data, row, row.get('candidates', []))
            if len(reference_embedding_data) != len(result.get('references', [])):
                raise ValueError('Duplicate reference embeddings')
            if len(embedding_data) != len(expected):
                raise ValueError('Missing query embeddings')
    worker_json = json_bytes(worker).decode()
    if job['status']=='IMPORTED':
        prior = {r['input_asset_id']:(r['sha256'],r['worker_json']) for r in db.execute('SELECT r.input_asset_id,a.sha256,r.worker_json FROM results r JOIN assets a ON a.asset_id=r.output_asset_id WHERE r.job_id=?',(job['job_id'],))}
        if any(prior[s['asset_id']]!=(digest(data),worker_json) for s,data in validated):
            raise ValueError('Job already imported with different outputs or worker metadata')
        prior_prepared={r['input_asset_id']:r['sha256'] for r in db.execute('SELECT p.input_asset_id,a.sha256 FROM processing_artifacts p JOIN assets a ON a.asset_id=p.artifact_asset_id WHERE p.job_id=?',(job['job_id'],))}
        if prior_prepared!={key:digest(data) for key,data in prepared_images.items()}:
            raise ValueError('Job already imported with different resized-input artifacts')
        return {'already_imported':True,'images':len(validated)}
    with db:
        for source,data in validated:
            asset_id = uuid.uuid5(uuid.NAMESPACE_URL,job['job_id']+'/'+source['asset_id']).hex
            relative = '__derived__/'+job['job_id']+'/'+source['asset_id']+'.png'
            store_asset(db,workspace,asset_id,source['dataset_id'],relative,'derived',data,
                        {'job_id':job['job_id'],'worker':worker},source['asset_id'])
            db.execute('INSERT INTO results VALUES(?,?,?,?)',(job['job_id'],source['asset_id'],asset_id,worker_json))
            if source['asset_id'] in prepared_images:
                prepared_id=uuid.uuid5(uuid.NAMESPACE_URL,job['job_id']+'/'+source['asset_id']+'/MODEL_INPUT').hex
                prepared_relative='__prepared__/'+job['job_id']+'/'+source['asset_id']+'_Resized512.png'
                store_asset(db,workspace,prepared_id,source['dataset_id'],prepared_relative,'derived',
                            prepared_images[source['asset_id']],{'kind':'MODEL_INPUT','job_id':job['job_id']},source['asset_id'])
                db.execute('INSERT INTO processing_artifacts VALUES(?,?,?,?)',
                           (job['job_id'],source['asset_id'],'MODEL_INPUT',prepared_id))
            if source['asset_id'] in embedding_data:
                data, row, candidates = embedding_data[source['asset_id']]
                query_id = uuid.uuid5(uuid.NAMESPACE_URL, job['job_id']+'/'+source['asset_id']+'/AdaFace').hex
                db.execute('INSERT INTO embeddings VALUES(?,?,?,?,?,?,?,?,?,?)',
                           (query_id, source['asset_id'], 'AdaFace',
                            worker['embedding_provenance'].get('model_revision','unknown'),
                            worker['embedding_provenance'].get('preprocessing','unknown'),
                            row['dimension'], row['dtype'], data, row['sha256'], now()))
                for candidate in candidates:
                    reference = reference_embedding_data.get(candidate['reference_asset_id'])
                    if reference is None:
                        raise ValueError('Candidate references an unembedded asset')
                    reference_id = uuid.uuid5(uuid.NAMESPACE_URL,
                                              'reference/'+candidate['reference_asset_id']+'/AdaFace').hex
                    ref_data, ref_row, _ = reference
                    db.execute('INSERT OR IGNORE INTO embeddings VALUES(?,?,?,?,?,?,?,?,?,?)',
                               (reference_id, candidate['reference_asset_id'], 'AdaFace',
                                worker['embedding_provenance'].get('model_revision','unknown'),
                                worker['embedding_provenance'].get('preprocessing','unknown'),
                                ref_row.get('dimension',512), ref_row.get('dtype','float32'),
                                ref_data, ref_row['sha256'], now()))
                    db.execute('INSERT INTO candidate_matches VALUES(?,?,?,?,?,?,?,?,?,?)',
                               (job['job_id'], source['asset_id'], 'ENHANCED',
                                candidate['rank'], candidate['reference_asset_id'],
                                candidate.get('reference_subject_id'), candidate['cosine_similarity'],
                                query_id, reference_id, now()))
        db.execute("UPDATE jobs SET status='IMPORTED',imported_utc=? WHERE job_id=?",(now(),job['job_id']))
        audit(db,'IMPORT_RESULTS',job['job_id'],{'images':len(validated),'worker':worker})
    return {'imported':len(validated),'job_id':job['job_id']}

def verify(db, workspace):
    """Compare database BLOBs and local files against their recorded hashes."""
    if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('Database integrity/foreign key check failed')
    count = 0
    for row in db.execute('SELECT * FROM assets'):
        if digest(row['image_blob'])!=row['sha256']:
            raise ValueError('Corrupt image BLOB')
        path = workspace / row['storage_relpath']
        if not path.is_file() or digest(path.read_bytes())!=row['sha256']:
            raise ValueError(f'Missing or changed image file: {path}')
        count += 1
    return {'integrity':'ok','verified_images':count}

def hydrate(db, workspace):
    """Rebuild local image files from database BLOBs after handing over the database."""
    restored=0
    for row in db.execute('SELECT storage_relpath,sha256,image_blob FROM assets'):
        if digest(row['image_blob'])!=row['sha256']: raise ValueError('Corrupt image BLOB')
        relative=PurePosixPath(row['storage_relpath'])
        if relative.is_absolute() or '..' in relative.parts: raise ValueError('Unsafe stored path')
        path=workspace/row['storage_relpath']
        if path.exists():
            if digest(path.read_bytes())!=row['sha256']: raise ValueError('Changed local image')
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(row['image_blob']); restored+=1
    return {'files_restored_from_database':restored}

def report(db, job_id, output):
    """Gets original/processed image BLOBs; creates a portable side-by-side HTML report."""
    if output.exists(): raise ValueError('Report path exists')
    rows=db.execute('SELECT s.dataset_id,s.source_relpath,s.image_blob AS original,s.mime AS source_mime,o.image_blob AS processed,o.mime AS output_mime,r.worker_json FROM results r JOIN assets s ON s.asset_id=r.input_asset_id JOIN assets o ON o.asset_id=r.output_asset_id WHERE r.job_id=? ORDER BY s.dataset_id,s.source_relpath',(job_id,)).fetchall()
    if not rows: raise ValueError('No imported results for this job')
    parts=['<!doctype html><meta charset="utf-8"><title>Research image processing report</title>',
           '<style>body{font:16px sans-serif;margin:2em}img{width:230px;height:230px;object-fit:contain}section{border-top:1px solid #888;padding:1em 0}.pair{display:flex;gap:1em}figure{margin:0}</style>',
           '<h1>Research image processing report</h1><p>Dataset samples; no identity determination. Original bytes are preserved. Resize smoke outputs are not model restorations.</p>',
           '<p>Job '+escape(job_id)+'</p>']
    for row in rows:
        parts.append('<section><h2>'+escape(row['dataset_id']+' / '+row['source_relpath'])+'</h2><p>Method: '+escape(json.loads(row['worker_json'])['method'])+'</p><div class="pair">')
        for label,blob,mime in [('Original',row['original'],row['source_mime']),('Processed',row['processed'],row['output_mime'])]:
            parts.append('<figure><img src="data:'+mime+';base64,'+base64.b64encode(blob).decode()+'"><figcaption>'+label+'</figcaption></figure>')
        parts.append('</div></section>')
    raw=''.join(parts).encode()
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(raw)
    with db:
        db.execute('INSERT INTO reports VALUES(?,?,?,?,?)',(uuid.uuid4().hex,job_id,digest(raw),raw,now()))
        audit(db,'REPORT',job_id,{'images':len(rows),'sha256':digest(raw)})
    return {'report':str(output.resolve()),'images':len(rows)}

def main():
    """Read the terminal command and dispatch it to the corresponding local workflow function."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,default=BASE/'workspace')
    commands = p.add_subparsers(dest='command',required=True)
    commands.add_parser('init'); commands.add_parser('verify'); commands.add_parser('status'); commands.add_parser('hydrate')
    q=commands.add_parser('ingest'); q.add_argument('--dataset',required=True)
    q.add_argument('--folder',type=Path,required=True); q.add_argument('--role',choices=['reference','input'],required=True)
    q.add_argument('--version',required=True); q.add_argument('--url',required=True)
    q=commands.add_parser('freeze'); q.add_argument('--name',required=True); q.add_argument('--datasets',nargs='+',required=True)
    q=commands.add_parser('export'); q.add_argument('--references',required=True)
    q.add_argument('--datasets',nargs='+',required=True); q.add_argument('--out',type=Path,required=True)
    q.add_argument('--limit',type=int,help='Optional local sample size; omit for all inputs')
    q.add_argument('--seed',type=int,help='Seed for a reproducible local sample')
    q.add_argument('--reference-stems',help='Comma-separated reference filename stems for a test subset')
    q=commands.add_parser('import'); q.add_argument('--zip',type=Path,required=True)
    q=commands.add_parser('backup'); q.add_argument('--out',type=Path,required=True)
    q=commands.add_parser('report'); q.add_argument('--job',required=True); q.add_argument('--out',type=Path,required=True)
    args=p.parse_args(); workspace=args.workspace.resolve()
    db=connect(workspace)
    try:
        if args.command=='init': result={'database':str(workspace/'research.sqlite')}
        elif args.command=='ingest': result=ingest(db,workspace,args.dataset,args.folder,args.role,args.version,args.url)
        elif args.command=='freeze': result=freeze(db,args.name,args.datasets)
        elif args.command=='export':
            stems = [stem.strip() for stem in args.reference_stems.split(',') if stem.strip()] if args.reference_stems else None
            result=export_job(db,workspace,args.references,args.datasets,args.out,args.limit,args.seed,stems)
        elif args.command=='import': result=import_results(db,workspace,args.zip)
        elif args.command=='verify': result=verify(db,workspace)
        elif args.command=='hydrate': result=hydrate(db,workspace)
        elif args.command=='report': result=report(db,args.job,args.out)
        elif args.command=='status': result={'datasets':[dict(r) for r in db.execute('SELECT * FROM v_dataset_counts')], 'jobs':[dict(r) for r in db.execute('SELECT * FROM v_job_progress')]}
        elif args.command=='backup':
            if args.out.exists(): raise ValueError('Backup target exists')
            args.out.parent.mkdir(parents=True,exist_ok=True)
            target=sqlite3.connect(args.out)
            try: db.backup(target)
            finally: target.close()
            result={'backup':str(args.out.resolve())}
        print(json.dumps(result,indent=2))
    finally: db.close()

if __name__=='__main__':
    main()
