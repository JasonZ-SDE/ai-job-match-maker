# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered job search application that scrapes LinkedIn job postings, stores them in a PostgreSQL database, and provides a Streamlit interface for viewing and managing job listings. The application includes automation capabilities through n8n workflows.

## Core Components

- **Job Scraping**: Playwright-based LinkedIn scraper (`scrapper/linkedin_job_scrapper.py`)
- **Data Management**: PostgreSQL database with SQLAlchemy models (`data_loader/load_jobs.py`)
- **AI Job Matching**: OpenAI-powered job analysis and scoring system (`ai_agent/`)
- **User Profile**: Professional background and career goals management (`user_profile/`)
- **User Interface**: Streamlit web app with AI scoring features (`jobs_app.py`)
- **Infrastructure**: Docker Compose setup with PostgreSQL and n8n
- **Database Schema**: Enhanced job table with AI scoring columns

## Essential Commands

### Environment Setup
```bash
# Start database and n8n services
docker compose --env-file .env up -d

# Install Python dependencies (using uv)
uv sync

# Apply database migrations
psql -h localhost -U $DB_USER -d $DB_NAME -f db_migrations/003_add_job_scoring.sql
```

### Core Workflow
```bash
# 1. Scrape jobs from LinkedIn
python ./scrapper/linkedin_job_scrapper.py

# 2. Load scraped data into database
python ./data_loader/load_jobs.py {CSV_FILENAME}

# 3. Set up user profile for AI scoring
python ./ai_agent/score_jobs.py profile create

# 4. Score jobs using AI
python ./ai_agent/score_jobs.py score new

# 5. Launch job viewing interface with AI scores
streamlit run jobs_app.py
```

### AI Job Scoring Commands
```bash
# Profile management
python ./ai_agent/score_jobs.py profile create          # Create profile interactively
python ./ai_agent/score_jobs.py profile create --sample # Create sample profile
python ./ai_agent/score_jobs.py profile view           # View current profile

# Job scoring
python ./ai_agent/score_jobs.py score new              # Score unscored jobs
python ./ai_agent/score_jobs.py score all              # Re-score all jobs
python ./ai_agent/score_jobs.py score ids --job-ids "123,456" # Score specific jobs

# Statistics
python ./ai_agent/score_jobs.py stats                  # Show scoring statistics
```

### Database Management
- Database migrations are in `db_migrations/` directory
- Initial setup runs automatically via Docker init scripts
- Manual migrations can be applied to running PostgreSQL instance

## Architecture Details

### Data Flow
1. **Scraper** (`linkedin_job_scrapper.py`) uses Playwright to extract job data
   - Handles LinkedIn authentication with session persistence
   - Filters for experience levels (2-4 years) and remote positions
   - Skips "Easy Apply" jobs to focus on external applications
   - Saves data to CSV in `.scrapped_data/` directory

2. **Data Loader** (`load_jobs.py`) processes CSV files into PostgreSQL
   - Uses SQLAlchemy ORM with conflict resolution (upsert behavior)
   - Converts comma-separated tags to PostgreSQL arrays
   - Requires CSV filename as command argument

3. **Streamlit App** (`jobs_app.py`) provides user interface
   - Paginated job browsing with customizable page sizes
   - Expandable job descriptions and "Not Interested" functionality
   - Direct links to LinkedIn and external application pages

### Database Schema
- Primary table: `job` with fields for job metadata, descriptions, and URLs
- AI scoring fields: `match_score` (0-10), `match_reasoning` (text), `scored_at` (timestamp)
- User preference tracking via `not_interested` boolean column
- Job tags stored as PostgreSQL TEXT[] arrays

### External Services
- **PostgreSQL**: Primary data storage (port 5432)
- **n8n**: Workflow automation platform (accessible at localhost:3000)
- **LinkedIn**: Job data source (requires credentials in .env)

## Environment Configuration

Required `.env` variables:
- Database: `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`
- LinkedIn: `LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD`
- OpenAI: `OPENAI_API_KEY` (for AI job scoring)
- n8n: `N8N_BASIC_AUTH_USER`, `N8N_BASIC_AUTH_PASSWORD`, `GENERIC_TIMEZONE`

## Development Notes

- Scraper maintains session state in `.storage_state.json` for authentication persistence
- Job scraping is limited to 1000 jobs and 40 pages maximum
- AI scoring uses OpenAI GPT-4o-mini for cost-effective analysis
- User profiles stored as JSON files in project root (`user_profile.json`)
- Streamlit app filters out jobs marked as "not interested" and displays AI scores
- CSV files are automatically timestamped and stored in `.scrapped_data/`
- Database migrations should be applied manually when upgrading