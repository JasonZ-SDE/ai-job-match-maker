-- Add job scoring columns for AI match analysis
ALTER TABLE job
ADD COLUMN match_score INTEGER DEFAULT NULL,
ADD COLUMN match_reasoning TEXT DEFAULT NULL,
ADD COLUMN scored_at TIMESTAMP DEFAULT NULL;

-- Add index for efficient filtering by match score
CREATE INDEX IF NOT EXISTS idx_job_match_score ON job(match_score);

-- Add index for filtering scored vs unscored jobs
CREATE INDEX IF NOT EXISTS idx_job_scored_at ON job(scored_at);