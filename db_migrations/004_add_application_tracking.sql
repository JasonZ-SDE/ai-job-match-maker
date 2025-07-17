-- Add application tracking columns
ALTER TABLE job
ADD COLUMN applied BOOLEAN DEFAULT FALSE,
ADD COLUMN applied_at DATE DEFAULT NULL;

-- Add index for efficient filtering by application status
CREATE INDEX IF NOT EXISTS idx_job_applied ON job(applied);

-- Add index for filtering by application date
CREATE INDEX IF NOT EXISTS idx_job_applied_at ON job(applied_at);