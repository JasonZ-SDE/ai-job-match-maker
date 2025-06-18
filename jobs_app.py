import streamlit as st
import psycopg2
import pandas as pd
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def load_jobs(offset, limit):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT job_id, title, company, job_info, job_tags, job_description, linkedin_url, apply_url
        FROM job
        ORDER BY job_id
        OFFSET %s LIMIT %s
    """, (offset, limit))
    rows = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return pd.DataFrame(rows, columns=colnames)

def show_jobs(jobs_df):
    cols = st.columns(3)

    for idx, row in jobs_df.iterrows():
        col = cols[idx % 3]
        with col.container():
            st.markdown(
                f"""
                <div style='border: 1px solid #ddd; border-radius: 6px; padding: 8px; margin: 4px; height: 220px; overflow: hidden;'>
                    <h5 style='margin-bottom: 4px;'>{row['title']}</h5>
                    <p style='margin: 0; font-size: 12px;'><strong>{row['company']}</strong></p>
                    <p style='margin: 0; font-size: 11px; color: grey;'>{row['job_info']}</p>
                    <p style='margin: 0; font-size: 11px;'>Tags: {", ".join(row['job_tags']) if isinstance(row['job_tags'], list) else row['job_tags']}</p>
                    <a href="{row['linkedin_url']}" target="_blank" style="font-size: 11px;">LinkedIn</a> | 
                    <a href="{row['apply_url']}" target="_blank" style="font-size: 11px;">Apply</a>
                </div>
                """,
                unsafe_allow_html=True
            )
            with st.expander("Job Description"):
                st.write(row['job_description'])

def main():
    st.set_page_config(page_title="Job Listings", layout="wide")
    st.title("Job Listings Dashboard")

    limit = st.sidebar.selectbox("Jobs per page", [6, 9, 12, 15], index=1)
    page_num = st.sidebar.number_input("Page number", min_value=1, value=1, step=1)
    offset = (page_num - 1) * limit

    jobs_df = load_jobs(offset, limit)
    if not jobs_df.empty:
        show_jobs(jobs_df)
    else:
        st.info("No jobs to display for this page.")

if __name__ == "__main__":
    main()
