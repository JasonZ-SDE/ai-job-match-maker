import streamlit as st
import psycopg2
import pandas as pd
from dotenv import load_dotenv
import os

# Load .env
load_dotenv(override=True)

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

def load_jobs(offset, limit, sort_by_score=False, min_score=None, show_applied=False):
    conn = get_connection()
    cur = conn.cursor()
    
    # Build dynamic query based on filters
    order_clause = "ORDER BY match_score DESC, job_id DESC" if sort_by_score else "ORDER BY job_id DESC"
    score_filter = f"AND match_score >= {min_score}" if min_score is not None else ""
    applied_filter = "AND applied = TRUE" if show_applied else "AND applied = FALSE"
    
    cur.execute(f"""
        SELECT job_id, title, company, job_info, job_tags, job_description, 
               linkedin_url, apply_url, match_score, match_reasoning, applied, applied_at
        FROM job
        WHERE not_interested = FALSE {score_filter} {applied_filter}
        {order_clause}
        OFFSET %s LIMIT %s
    """, (offset, limit))
    rows = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return pd.DataFrame(rows, columns=colnames)

def mark_not_interested(job_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE job
        SET not_interested = TRUE
        WHERE job_id = %s
    """, (job_id,))
    conn.commit()
    cur.close()
    conn.close()

def mark_as_applied(job_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE job
        SET applied = TRUE, applied_at = CURRENT_DATE
        WHERE job_id = %s
    """, (job_id,))
    conn.commit()
    cur.close()
    conn.close()

def get_score_color(score):
    """Get color for match score display."""
    if score is None:
        return "#666"
    elif score >= 8:
        return "#28a745"  # Green
    elif score >= 6:
        return "#ffc107"  # Yellow
    elif score >= 4:
        return "#fd7e14"  # Orange
    else:
        return "#dc3545"  # Red

def show_jobs(jobs_df, show_applied=False):
    cols = st.columns(3)

    for idx, row in jobs_df.iterrows():
        col = cols[idx % 3]
        with col.container():
            # Prepare match score display
            score = row.get('match_score')
            score_display = f"🎯 {score}/10" if score is not None else "⚪ Not scored"
            score_color = get_score_color(score)
            
            # Prepare application status display
            applied_status = "<div> </div>"
            if row.get('applied'):
                applied_date = row.get('applied_at')
                applied_status = f"<div style='color: #28a745; font-size: 11px; font-weight: bold;'>✅ Applied {applied_date if applied_date else ''}</div>"
            
            # Prepare tag display
            tags_display = ", ".join(row['job_tags']) if isinstance(row['job_tags'], list) else str(row['job_tags'])
            
            st.markdown(
                f"""
                <div style='border: 1px solid #ddd; border-radius: 6px; padding: 8px; margin: 4px; height: 250px; overflow: hidden;'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;'>
                        <h5 style='margin: 0; flex-grow: 1;'>{row['title']}</h5>
                        <span style='color: {score_color}; font-weight: bold; font-size: 12px;'>{score_display}</span>
                    </div>
                    <p style='margin: 0; font-size: 12px;'><strong>{row['company']}</strong></p>
                    <p style='margin: 0; font-size: 11px; color: grey;'>{row['job_info']}</p>
                    <p style='margin: 0; font-size: 11px;'>Tags: {tags_display}</p>
                    <p style='margin: 4px 0;'>
                        <a href="{row['linkedin_url']}" target="_blank" style="font-size: 11px; text-decoration: none; color: #0077b5;">LinkedIn</a> | 
                        <a href="{row['apply_url']}" target="_blank" style="font-size: 11px; text-decoration: none; color: #28a745;">Apply</a>
                    </p>
                    {applied_status}
                </div>
                """,
                unsafe_allow_html=True
            )

            desc_key = f"show_desc_{row['job_id']}"

            if desc_key not in st.session_state:
                st.session_state[desc_key] = False

            if not st.session_state[desc_key]:
                if st.button(f"Show Description 📝 {row['job_id']}", key=f"show_{row['job_id']}"):
                    st.session_state[desc_key] = True
                    st.rerun()
            else:
                st.markdown(
                    f"""
                    <div style="border: 1px solid #ddd; padding: 4px; margin-top: 4px;">
                        {row['job_description']}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.button(f"Close Description ❌ {row['job_id']}", key=f"close_{row['job_id']}"):
                    st.session_state[desc_key] = False
                    st.rerun()

            # Show AI reasoning if available
            if row.get('match_reasoning') and score is not None:
                reasoning_key = f"show_reasoning_{row['job_id']}"
                if reasoning_key not in st.session_state:
                    st.session_state[reasoning_key] = False
                
                if not st.session_state[reasoning_key]:
                    if st.button(f"Show AI Analysis 🤖 {row['job_id']}", key=f"reason_{row['job_id']}"):
                        st.session_state[reasoning_key] = True
                        st.rerun()
                else:
                    st.markdown(
                        f"""
                        <div style="border: 1px solid #007bff; padding: 6px; margin-top: 4px; background-color: #f8f9fa;">
                            <strong>🤖 AI Analysis (Score: {score}/10):</strong><br>
                            {row['match_reasoning']}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    if st.button(f"Hide Analysis ❌ {row['job_id']}", key=f"hide_reason_{row['job_id']}"):
                        st.session_state[reasoning_key] = False
                        st.rerun()
            
            # Action buttons
            button_cols = st.columns(2)
            with button_cols[0]:
                if st.button(f"Not Interested 🚫 {row['job_id']}", key=f"notint_{row['job_id']}"):
                    mark_not_interested(row['job_id'])
                    st.rerun()
            
            # Only show "Mark as Applied" button for not applied jobs
            if not show_applied and not row.get('applied'):
                with button_cols[1]:
                    if st.button(f"Mark as Applied ✅ {row['job_id']}", key=f"applied_{row['job_id']}"):
                        mark_as_applied(row['job_id'])
                        st.rerun()

def main():
    st.set_page_config(page_title="Job Listings", layout="wide")
    st.title("Job Listings Dashboard")

    # Sidebar filters
    st.sidebar.header("Filters")
    limit = st.sidebar.selectbox("Jobs per page", [6, 9, 12, 15], index=1)
    page_num = st.sidebar.number_input("Page number", min_value=1, value=1, step=1)
    
    # Application status filter
    st.sidebar.subheader("Application Status")
    show_applied = st.sidebar.radio(
        "Show jobs:",
        ["Not Applied", "Applied"],
        index=0
    ) == "Applied"
    
    # Scoring filters
    st.sidebar.subheader("AI Match Scoring")
    sort_by_score = st.sidebar.checkbox("Sort by match score", value=False)
    min_score = st.sidebar.slider("Minimum match score", 0, 10, 0, help="Only show jobs with this score or higher")
    min_score = min_score if min_score > 0 else None
    
    offset = (page_num - 1) * limit

    jobs_df = load_jobs(offset, limit, sort_by_score=sort_by_score, min_score=min_score, show_applied=show_applied)
    
    # Display summary stats
    if not jobs_df.empty and 'match_score' in jobs_df.columns:
        scored_jobs = jobs_df['match_score'].notna().sum()
        if scored_jobs > 0:
            avg_score = jobs_df[jobs_df['match_score'].notna()]['match_score'].mean()
            st.info(f"📊 Showing {len(jobs_df)} jobs • {scored_jobs} have AI scores • Avg score: {avg_score:.1f}/10")
        else:
            st.info(f"📊 Showing {len(jobs_df)} jobs • No AI scores yet")
    
    if not jobs_df.empty:
        show_jobs(jobs_df, show_applied=show_applied)
    else:
        status_text = "applied" if show_applied else "not applied"
        st.info(f"No {status_text} jobs to display for this page.")

if __name__ == "__main__":
    main()
