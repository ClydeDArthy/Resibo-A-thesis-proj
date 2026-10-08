PRAGMA foreign_keys=ON;
PRAGMA integrity_check;
PRAGMA foreign_key_check;
SELECT * FROM v_dataset_counts;
SELECT * FROM reference_sets;
SELECT * FROM v_job_progress;
SELECT * FROM v_source_output;
SELECT asset_id,dataset_id,role,source_relpath,width,height,byte_count,
       length(image_blob) AS blob_bytes,sha256 FROM assets;
SELECT event_id,action,object_id,created_utc FROM audit_events ORDER BY event_id;

-- Ito yung model-input records returned separately from restored images.
SELECT p.job_id,p.input_asset_id,p.kind,a.sha256,a.width,a.height,a.storage_relpath
FROM processing_artifacts p JOIN assets a ON a.asset_id=p.artifact_asset_id;
