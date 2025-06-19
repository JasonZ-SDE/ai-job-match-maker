# ai-job-match-maker

My dev application to help job search with AI.

# Scripts to run

```
docker compose --env-file .env up -d  # Start the Postgres server and n8n local server
python ./scrapper/linkedin_job_scrapper.py   # Scrap jobs from linkedIN
python ./data_loader/load_jobs.py  {CSV_FILENAME}    # Load scrapped jobs into the Postgres DB
streamlit run jobs_app.py    # View all the jobs in the Postgres DB
```
