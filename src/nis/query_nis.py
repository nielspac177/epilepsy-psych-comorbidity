#!/usr/bin/env python3
"""
NIS Database Query Helper
Interactive querying of the NIS database

Usage:
    source venv/bin/activate
    python3 query_nis.py

Or use in Python:
    import duckdb
    con = duckdb.connect('NIS.duckdb', read_only=True)
    df = con.execute("SELECT * FROM nis_core LIMIT 10").df()
"""

import duckdb
from pathlib import Path

DB_PATH = Path("/Volumes/Niels 1/NIS/NIS.duckdb")

def get_connection(read_only=True):
    """Get a connection to the NIS database."""
    return duckdb.connect(str(DB_PATH), read_only=read_only)

def run_query(sql, limit=None):
    """Run a SQL query and return results as a pandas DataFrame."""
    con = get_connection()
    if limit:
        sql = f"{sql} LIMIT {limit}"
    result = con.execute(sql).df()
    con.close()
    return result

# Example queries for common analyses
EXAMPLE_QUERIES = {
    "total_records": "SELECT COUNT(*) as total FROM nis_core",

    "records_by_year": """
        SELECT YEAR, COUNT(*) as admissions,
               SUM(DIED) as deaths,
               ROUND(AVG(LOS), 1) as avg_length_of_stay,
               ROUND(AVG(TOTCHG), 0) as avg_total_charges
        FROM nis_core
        GROUP BY YEAR
        ORDER BY YEAR
    """,

    "mortality_by_age_group": """
        SELECT
            CASE
                WHEN AGE < 18 THEN '0-17 (Pediatric)'
                WHEN AGE < 45 THEN '18-44 (Young Adult)'
                WHEN AGE < 65 THEN '45-64 (Middle Age)'
                WHEN AGE < 85 THEN '65-84 (Senior)'
                ELSE '85+ (Elderly)'
            END as age_group,
            COUNT(*) as admissions,
            SUM(DIED) as deaths,
            ROUND(100.0 * SUM(DIED) / COUNT(*), 2) as mortality_rate
        FROM nis_core
        WHERE AGE IS NOT NULL
        GROUP BY 1
        ORDER BY 1
    """,

    "top_payers": """
        SELECT
            CASE PAY1
                WHEN 1 THEN 'Medicare'
                WHEN 2 THEN 'Medicaid'
                WHEN 3 THEN 'Private Insurance'
                WHEN 4 THEN 'Self-Pay'
                WHEN 5 THEN 'No Charge'
                WHEN 6 THEN 'Other'
                ELSE 'Unknown'
            END as payer,
            COUNT(*) as admissions,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) as pct
        FROM nis_core
        GROUP BY PAY1
        ORDER BY admissions DESC
    """,

    "charges_by_region": """
        SELECT
            CASE HOSP_REGION
                WHEN 1 THEN 'Northeast'
                WHEN 2 THEN 'Midwest'
                WHEN 3 THEN 'South'
                WHEN 4 THEN 'West'
            END as region,
            COUNT(*) as admissions,
            ROUND(AVG(TOTCHG), 0) as avg_charges,
            ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY TOTCHG), 0) as median_charges
        FROM nis_core
        WHERE TOTCHG IS NOT NULL AND HOSP_REGION IS NOT NULL
        GROUP BY HOSP_REGION
        ORDER BY HOSP_REGION
    """,

    "weekend_vs_weekday": """
        SELECT
            CASE AWEEKEND WHEN 1 THEN 'Weekend' ELSE 'Weekday' END as admission_day,
            COUNT(*) as admissions,
            ROUND(100.0 * SUM(DIED) / COUNT(*), 2) as mortality_rate,
            ROUND(AVG(LOS), 1) as avg_los
        FROM nis_core
        GROUP BY AWEEKEND
    """
}

def interactive_mode():
    """Run interactive query mode."""
    print("\n" + "="*60)
    print("NIS Database Interactive Query Tool")
    print("="*60)
    print(f"\nDatabase: {DB_PATH}")
    print("Total records: 56,300,566 hospitalizations (2013-2020)")
    print("\nAvailable tables:")
    print("  - nis_core    (unified view, 36 columns, all years)")
    print("  - nis_2013    (182 columns, ICD-9)")
    print("  - nis_2014    (194 columns, ICD-9)")
    print("  - nis_2015    (36 columns, core only)")
    print("  - nis_2016    (111 columns, ICD-10)")
    print("  - nis_2017    (135 columns, ICD-10)")
    print("  - nis_2018    (133 columns, ICD-10)")
    print("  - nis_2019    (139 columns, ICD-10)")
    print("  - nis_2020    (139 columns, ICD-10)")
    print("\nType 'examples' to see example queries")
    print("Type 'exit' or 'quit' to exit")
    print("-"*60)

    con = get_connection()

    while True:
        try:
            query = input("\nSQL> ").strip()

            if not query:
                continue
            if query.lower() in ('exit', 'quit', 'q'):
                break
            if query.lower() == 'examples':
                print("\nExample queries:")
                for name, sql in EXAMPLE_QUERIES.items():
                    print(f"\n-- {name}:")
                    print(sql.strip()[:200] + "..." if len(sql) > 200 else sql.strip())
                continue

            # Execute query
            import time
            start = time.time()
            result = con.execute(query).df()
            elapsed = time.time() - start

            print(f"\n{result.to_string()}")
            print(f"\n[{len(result)} rows in {elapsed:.2f}s]")

        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as e:
            print(f"Error: {e}")

    con.close()
    print("Goodbye!")

if __name__ == "__main__":
    interactive_mode()
