CREATE TABLE IF NOT EXISTS job (
    job_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    job_info TEXT,
    job_tags TEXT[],  -- This is an array of text for list[str]
    job_description TEXT,
    linkedin_url TEXT,
    apply_url TEXT
);