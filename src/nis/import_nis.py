#!/usr/bin/env python3
"""
NIS Database Import Script
Creates a DuckDB database from NIS CSV files (2013-2020)
"""

import duckdb
import os
import time
from pathlib import Path

# Configuration
BASE_DIR = Path("/Volumes/Niels 1/NIS")
RAW_DATA_DIR = BASE_DIR / "raw data"
DB_PATH = BASE_DIR / "NIS.duckdb"
YEARS = [2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020]

# Common columns across all years (for unified view)
COMMON_COLUMNS = [
    "AGE", "AGE_NEONATE", "AMONTH", "APRDRG", "APRDRG_Risk_Mortality",
    "APRDRG_Severity", "AWEEKEND", "DIED", "DISCWT", "DISPUNIFORM",
    "DQTR", "ELECTIVE", "FEMALE", "HCUP_ED", "HOSP_BEDSIZE",
    "HOSP_DIVISION", "HOSP_LOCTEACH", "HOSP_NIS", "HOSP_REGION",
    "H_CONTRL", "KEY_NIS", "LOS", "NIS_STRATUM", "N_DISC_U", "N_HOSP_U",
    "PAY1", "PL_NCHS", "RACE", "S_DISC_U", "S_HOSP_U", "TOTAL_DISC",
    "TOTCHG", "TRAN_IN", "TRAN_OUT", "YEAR", "ZIPINC_QRTL"
]

def main():
    # Remove existing database if exists
    if DB_PATH.exists():
        print(f"Removing existing database at {DB_PATH}")
        DB_PATH.unlink()

    # Create connection
    print(f"Creating database at {DB_PATH}")
    con = duckdb.connect(str(DB_PATH))

    # Configure for better performance on large imports
    con.execute("SET memory_limit='4GB'")
    con.execute("SET threads=4")

    total_start = time.time()

    # Import each year
    for year in YEARS:
        csv_path = RAW_DATA_DIR / str(year) / f"NIS_{year}_mega.csv"
        table_name = f"nis_{year}"

        if not csv_path.exists():
            print(f"Warning: {csv_path} not found, skipping")
            continue

        print(f"\n{'='*60}")
        print(f"Importing {year}...")
        print(f"Source: {csv_path}")

        start = time.time()

        # DuckDB can directly read CSV files efficiently
        con.execute(f"""
            CREATE TABLE {table_name} AS
            SELECT * FROM read_csv('{csv_path}',
                header=true,
                auto_detect=true,
                sample_size=100000
            )
        """)

        # Get row count
        count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        elapsed = time.time() - start

        print(f"  Imported {count:,} rows in {elapsed:.1f} seconds")
        print(f"  Rate: {count/elapsed:,.0f} rows/sec")

    # Create unified view with common columns
    print(f"\n{'='*60}")
    print("Creating unified view 'nis_core'...")

    cols = ", ".join(COMMON_COLUMNS)
    union_parts = []

    for year in YEARS:
        table_name = f"nis_{year}"
        # Check if table exists
        exists = con.execute(f"""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = '{table_name}'
        """).fetchone()[0]
        if exists:
            union_parts.append(f"SELECT {cols} FROM {table_name}")

    if union_parts:
        union_query = " UNION ALL ".join(union_parts)
        con.execute(f"CREATE VIEW nis_core AS {union_query}")

        # Get total count
        total_count = con.execute("SELECT COUNT(*) FROM nis_core").fetchone()[0]
        print(f"  Unified view created with {total_count:,} total records")

    # Create indexes for common query patterns
    print(f"\n{'='*60}")
    print("Creating indexes...")

    for year in YEARS:
        table_name = f"nis_{year}"
        try:
            # Indexes on commonly queried columns
            con.execute(f"CREATE INDEX idx_{year}_age ON {table_name}(AGE)")
            con.execute(f"CREATE INDEX idx_{year}_year ON {table_name}(YEAR)")
            con.execute(f"CREATE INDEX idx_{year}_died ON {table_name}(DIED)")
            print(f"  Created indexes for {table_name}")
        except Exception as e:
            print(f"  Warning: Could not create index for {table_name}: {e}")

    # Print summary
    total_elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print("IMPORT COMPLETE!")
    print(f"{'='*60}")
    print(f"Total time: {total_elapsed/60:.1f} minutes")
    print(f"Database location: {DB_PATH}")

    # Show database size
    db_size = DB_PATH.stat().st_size / (1024**3)
    print(f"Database size: {db_size:.2f} GB")

    # Show table summary
    print("\nTables created:")
    for year in YEARS:
        table_name = f"nis_{year}"
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            print(f"  {table_name}: {count:,} rows")
        except:
            pass

    con.close()
    print("\nDone! You can now query the database using:")
    print(f"  source venv/bin/activate")
    print(f"  python3 -c \"import duckdb; con = duckdb.connect('NIS.duckdb'); print(con.execute('SELECT COUNT(*) FROM nis_core').fetchone())\"")

if __name__ == "__main__":
    main()
