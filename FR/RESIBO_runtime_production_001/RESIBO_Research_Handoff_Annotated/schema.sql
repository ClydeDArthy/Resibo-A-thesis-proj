-- This SQL line enables relationship checks for this connection; Python also enables it on every connection.
PRAGMA foreign_keys = ON;
-- Ito yung schema version record, para identifiable ang database layout.
CREATE TABLE IF NOT EXISTS schema_info (
    version INTEGER PRIMARY KEY CHECK (version=1)
);
INSERT OR IGNORE INTO schema_info VALUES (1);

--dataset provenance: FRMDB/LNS source URL and source version.
CREATE TABLE IF NOT EXISTS datasets (
    dataset_id TEXT PRIMARY KEY,
    source_url TEXT NOT NULL,
    source_version TEXT NOT NULL,
    purpose TEXT NOT NULL DEFAULT 'research_image_processing',
    created_utc TEXT NOT NULL
);
-- table for reference, original, resized, and restored image bytes.
-- image_blob contains the picture itself; parent_asset_id links derivatives to the original.
CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL REFERENCES datasets(dataset_id),
    source_relpath TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('reference','input','derived')),
    parent_asset_id TEXT REFERENCES assets(asset_id),
    sha256 TEXT NOT NULL CHECK(length(sha256)=64),
    mime TEXT NOT NULL,
    width INTEGER NOT NULL CHECK(width>0),
    height INTEGER NOT NULL CHECK(height>0),
    byte_count INTEGER NOT NULL CHECK(byte_count>0),
    storage_relpath TEXT NOT NULL,
    image_blob BLOB NOT NULL,
    metadata_json TEXT NOT NULL,
    created_utc TEXT NOT NULL,
    UNIQUE(dataset_id,source_relpath),
    CHECK ((role='derived' AND parent_asset_id IS NOT NULL) OR
           (role<>'derived' AND parent_asset_id IS NULL)),
    CHECK(length(image_blob)=byte_count)
);
-- This index speeds up duplicate-image/hash checks.
CREATE INDEX IF NOT EXISTS assets_sha ON assets(sha256);
-- Ito yung fixed reference database version and membership fingerprint.
CREATE TABLE IF NOT EXISTS reference_sets (
    reference_set_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL CHECK(length(fingerprint)=64),
    note TEXT NOT NULL,
    sealed INTEGER NOT NULL DEFAULT 0 CHECK(sealed IN (0,1)),
    created_utc TEXT NOT NULL
);
-- This join table connects a fixed reference version to its exact image members.
CREATE TABLE IF NOT EXISTS reference_members (
    reference_set_id TEXT NOT NULL REFERENCES reference_sets(reference_set_id),
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    PRIMARY KEY(reference_set_id,asset_id)
);
-- Ito yung exported Colab job: stores the exact request and its hash.
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    reference_set_id TEXT NOT NULL REFERENCES reference_sets(reference_set_id),
    request_sha256 TEXT NOT NULL CHECK(length(request_sha256)=64),
    request_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('EXPORTED','IMPORTED')),
    created_utc TEXT NOT NULL,
    imported_utc TEXT
);
-- This table defines all expected inputs; imports must return the complete set.
CREATE TABLE IF NOT EXISTS job_inputs (
    job_id TEXT NOT NULL REFERENCES jobs(job_id),
    input_asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    PRIMARY KEY(job_id,input_asset_id)
);
-- Ito yung original-to-restored result link; no candidate matching is stored here.
CREATE TABLE IF NOT EXISTS results (
    job_id TEXT NOT NULL,
    input_asset_id TEXT NOT NULL,
    output_asset_id TEXT NOT NULL UNIQUE REFERENCES assets(asset_id),
    worker_json TEXT NOT NULL,
    PRIMARY KEY(job_id,input_asset_id),
    FOREIGN KEY(job_id,input_asset_id) REFERENCES job_inputs(job_id,input_asset_id)
);
-- Ito yung append-only operation history.
CREATE TABLE IF NOT EXISTS audit_events (
    event_id INTEGER PRIMARY KEY,
    action TEXT NOT NULL,
    object_id TEXT NOT NULL,
    details_json TEXT NOT NULL,
    created_utc TEXT NOT NULL
);
-- This table stores portable HTML report bytes inside the database.
CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(job_id),
    sha256 TEXT NOT NULL CHECK(length(sha256)=64),
    html_blob BLOB NOT NULL,
    created_utc TEXT NOT NULL
);
-- Ito yung separate record para sa resized model input; hindi ino-overwrite ang original.
CREATE TABLE IF NOT EXISTS processing_artifacts (
    job_id TEXT NOT NULL,
    input_asset_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind='MODEL_INPUT'),
    artifact_asset_id TEXT NOT NULL UNIQUE REFERENCES assets(asset_id),
    PRIMARY KEY(job_id,input_asset_id,kind),
    FOREIGN KEY(job_id,input_asset_id) REFERENCES job_inputs(job_id,input_asset_id)
);

-- AdaFace vectors are stored separately from image artifacts and are tied to the exact model/preprocessing.
CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    model TEXT NOT NULL,
    model_revision TEXT NOT NULL,
    preprocessing TEXT NOT NULL,
    dimension INTEGER NOT NULL CHECK(dimension>0),
    dtype TEXT NOT NULL,
    vector_blob BLOB NOT NULL,
    vector_sha256 TEXT NOT NULL CHECK(length(vector_sha256)=64),
    created_utc TEXT NOT NULL,
    UNIQUE(asset_id,model,model_revision,preprocessing)
);
CREATE INDEX IF NOT EXISTS embeddings_asset ON embeddings(asset_id);

-- Ranked recognition evidence links a processed query to one frozen reference image.
CREATE TABLE IF NOT EXISTS candidate_matches (
    job_id TEXT NOT NULL REFERENCES jobs(job_id),
    input_asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    branch TEXT NOT NULL CHECK(branch IN ('SOURCE_LR','ENHANCED')),
    candidate_rank INTEGER NOT NULL CHECK(candidate_rank>0),
    reference_asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    reference_subject_id TEXT,
    cosine_similarity REAL NOT NULL CHECK(cosine_similarity BETWEEN -1.000001 AND 1.000001),
    query_embedding_id TEXT NOT NULL REFERENCES embeddings(embedding_id),
    reference_embedding_id TEXT NOT NULL REFERENCES embeddings(embedding_id),
    created_utc TEXT NOT NULL,
    PRIMARY KEY(job_id,input_asset_id,branch,candidate_rank),
    UNIQUE(job_id,input_asset_id,branch,reference_asset_id),
    FOREIGN KEY(job_id,input_asset_id) REFERENCES job_inputs(job_id,input_asset_id)
);
CREATE INDEX IF NOT EXISTS candidate_matches_reference ON candidate_matches(reference_asset_id);

-- Research reference images are frozen; no identity matching is implemented.
CREATE TRIGGER IF NOT EXISTS member_requires_reference BEFORE INSERT ON reference_members
WHEN (SELECT role FROM assets WHERE asset_id=NEW.asset_id)<>'reference'
BEGIN SELECT RAISE(ABORT,'Only reference assets can be frozen'); END;
CREATE TRIGGER IF NOT EXISTS frozen_member_insert BEFORE INSERT ON reference_members
WHEN (SELECT sealed FROM reference_sets WHERE reference_set_id=NEW.reference_set_id)=1
BEGIN SELECT RAISE(ABORT,'Reference set is frozen'); END;
CREATE TRIGGER IF NOT EXISTS frozen_member_update BEFORE UPDATE ON reference_members
BEGIN SELECT RAISE(ABORT,'Reference members are immutable'); END;
CREATE TRIGGER IF NOT EXISTS frozen_member_delete BEFORE DELETE ON reference_members
WHEN (SELECT sealed FROM reference_sets WHERE reference_set_id=OLD.reference_set_id)=1
BEGIN SELECT RAISE(ABORT,'Reference set is frozen'); END;
CREATE TRIGGER IF NOT EXISTS frozen_set_update BEFORE UPDATE ON reference_sets
WHEN OLD.sealed=1
BEGIN SELECT RAISE(ABORT,'Reference set is frozen'); END;
CREATE TRIGGER IF NOT EXISTS frozen_set_delete BEFORE DELETE ON reference_sets
WHEN OLD.sealed=1
BEGIN SELECT RAISE(ABORT,'Reference set is frozen'); END;
CREATE TRIGGER IF NOT EXISTS assets_update BEFORE UPDATE ON assets
BEGIN SELECT RAISE(ABORT,'Assets are append-only'); END;
CREATE TRIGGER IF NOT EXISTS assets_delete BEFORE DELETE ON assets
BEGIN SELECT RAISE(ABORT,'Assets are append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_update BEFORE UPDATE ON audit_events
BEGIN SELECT RAISE(ABORT,'Audit events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_delete BEFORE DELETE ON audit_events
BEGIN SELECT RAISE(ABORT,'Audit events are append-only'); END;

-- This view gives DBeaver a readable summary without modifying source data.
CREATE VIEW IF NOT EXISTS v_dataset_counts AS
SELECT d.dataset_id,d.source_version,a.role,COUNT(a.asset_id) AS image_count
FROM datasets d LEFT JOIN assets a USING(dataset_id)
GROUP BY d.dataset_id,d.source_version,a.role;
-- This view compares expected inputs with imported outputs.
CREATE VIEW IF NOT EXISTS v_job_progress AS
SELECT j.job_id,j.status,j.reference_set_id,
 (SELECT COUNT(*) FROM job_inputs i WHERE i.job_id=j.job_id) AS expected_images,
 (SELECT COUNT(*) FROM results r WHERE r.job_id=j.job_id) AS returned_images
FROM jobs j;
-- This view connects original and processed paths/hashes for inspection.
CREATE VIEW IF NOT EXISTS v_source_output AS
SELECT r.job_id,s.asset_id AS source_id,s.dataset_id,s.source_relpath,
 s.sha256 AS source_sha256,o.sha256 AS output_sha256,
 s.storage_relpath AS source_file,o.storage_relpath AS output_file,
 r.worker_json
FROM results r JOIN assets s ON s.asset_id=r.input_asset_id
JOIN assets o ON o.asset_id=r.output_asset_id;

CREATE VIEW IF NOT EXISTS v_candidate_matches AS
SELECT c.job_id,c.input_asset_id,c.branch,c.candidate_rank,
       c.reference_asset_id,c.reference_subject_id,c.cosine_similarity,
       q.model AS query_model, r.model AS reference_model
FROM candidate_matches c
JOIN embeddings q ON q.embedding_id=c.query_embedding_id
JOIN embeddings r ON r.embedding_id=c.reference_embedding_id;
