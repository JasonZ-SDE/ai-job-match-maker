# ai-job-match-maker

My dev application to help job search with AI-powered matching and scoring.

## Features

- **LinkedIn Job Scraping**: Automated job data collection from LinkedIn
- **AI Job Matching**: OpenAI-powered job analysis and scoring (0-10 scale)
- **Smart Filtering**: Sort and filter jobs by AI match scores
- **Professional Profiles**: Detailed user profile management
- **Enhanced UI**: Streamlit interface with AI insights and reasoning

## Setup

### 1. Environment Setup
```bash
# Install dependencies
uv sync

# Start database and n8n services
docker compose --env-file .env up -d

# Apply database migrations
psql -h localhost -U $DB_USER -d $DB_NAME -f db_migrations/003_add_job_scoring.sql
```

### 2. Environment Variables
Copy `.env_example` to `.env` and fill in:
```
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password
OPENAI_API_KEY=your_openai_api_key
DB_USER=your_db_user
DB_PASSWORD=your_db_password
# ... other variables
```

## Usage

### Basic Workflow
```bash
# 1. Scrape jobs from LinkedIn
python ./scrapper/linkedin_job_scrapper.py

# 2. Load scraped data into database
python ./data_loader/load_jobs.py {CSV_FILENAME}

# 3. Set up your professional profile
python ./ai_agent/score_jobs.py profile create --from-json

# 4. Score jobs using AI
python ./ai_agent/score_jobs.py score new

# 5. Launch enhanced job viewing interface
streamlit run jobs_app.py
```

### AI Job Scoring Commands

#### Profile Management
```bash
# Create profile from your background JSON
python ./ai_agent/score_jobs.py profile create --from-json

# Create profile interactively
python ./ai_agent/score_jobs.py profile create

# Create sample profile for testing
python ./ai_agent/score_jobs.py profile create --sample

# View current profile
python ./ai_agent/score_jobs.py profile view

# Delete profile
python ./ai_agent/score_jobs.py profile delete
```

#### Job Scoring
```bash
# Score all unscored jobs
python ./ai_agent/score_jobs.py score new

# Score first 20 jobs (for testing)
python ./ai_agent/score_jobs.py score new --limit 20

# Re-score all jobs (if you updated your profile)
python ./ai_agent/score_jobs.py score all

# Score specific jobs by ID
python ./ai_agent/score_jobs.py score ids --job-ids "123,456,789"

# View scoring statistics
python ./ai_agent/score_jobs.py stats
```

### Streamlit Interface Features

- **🎯 AI Match Scores**: Color-coded job scores (0-10)
- **🤖 AI Analysis**: Detailed reasoning for each job match
- **🔍 Smart Filtering**: Filter by minimum score, sort by relevance
- **📊 Statistics**: View scoring progress and distributions
- **✅ Job Management**: Mark jobs as "not interested"

## AI Scoring System

The AI analyzes jobs across multiple dimensions:
- **Role Alignment**: Job title/responsibilities match
- **Skills Match**: Technical skills compatibility
- **Experience Level**: Appropriate for your experience
- **Location/Work Style**: Remote/location preferences
- **Career Growth**: Advancement opportunities
- **Compensation**: Salary expectations alignment

### Score Interpretation
- **9-10**: 🟢 Excellent matches (apply immediately!)
- **7-8**: 🟡 Good matches (strong candidates)
- **5-6**: 🟠 Average matches (consider carefully)
- **0-4**: 🔴 Poor matches (probably skip)

## Access Points

- **Streamlit UI**: `streamlit run jobs_app.py`
- **n8n Automation**: http://localhost:3000
- **Database**: PostgreSQL on localhost:5432

## Architecture

- **Scraping**: Playwright-based LinkedIn automation
- **Database**: PostgreSQL with enhanced job scoring schema
- **AI Engine**: OpenAI GPT-4o-mini for cost-effective analysis
- **Profile Management**: JSON-based user profiles
- **UI**: Streamlit with rich job insights
- **Automation**: n8n workflows for advanced scheduling

## Cost Optimization

- Uses GPT-4o-mini for ~$0.001-0.002 per job analysis
- Batch processing with rate limiting
- Efficient caching and data management
