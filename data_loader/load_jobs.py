import argparse
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, Column, Text, ARRAY
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import insert
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

# DB config from env
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

# SQLAlchemy setup
Base = declarative_base()

class Job(Base):
    __tablename__ = 'job'
    job_id = Column(Text, primary_key=True)
    title = Column(Text, nullable=False)
    company = Column(Text, nullable=False)
    job_info = Column(Text)
    job_tags = Column(ARRAY(Text))
    job_description = Column(Text)
    linkedin_url = Column(Text)
    apply_url = Column(Text)

def main(csv_filename):
    csv_path = Path(__file__).resolve().parent.parent / '.scrapped_data' / csv_filename

    if not csv_path.exists():
        print(f"❌ File not found: {csv_path}")
        return

    engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    df = pd.read_csv(csv_path)

    for _, row in df.iterrows():
        stmt = insert(Job).values(
            job_id=row['job_id'],
            title=row['title'],
            company=row['company'],
            job_info=row.get('job_info'),
            job_tags=row.get('job_tags', '').split('|') if pd.notna(row.get('job_tags')) else [],
            job_description=row.get('job_description'),
            linkedin_url=row.get('linkedin_url'),
            apply_url=row.get('apply_url')
        ).on_conflict_do_nothing(index_elements=['job_id'])

        session.execute(stmt)

    session.commit()
    session.close()
    print(f"✅ Data loaded successfully from {csv_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Load jobs from CSV into Postgres DB")
    parser.add_argument('csv_filename', help="CSV file name in ../.scrapped_data/")
    args = parser.parse_args()

    main(args.csv_filename)
