#!/usr/bin/env python3
# =============================================================================
#  import_sales.py
#  Impordib powerbi_test_dataset.csv andmed PostgreSQL-i 'sales' tabelisse.
#
#  Kasutamine (Dockeris):
#      docker compose exec python python /scripts/import_sales.py
#
#  Eeldused:
#      pip install pandas psycopg2-binary
#
#  Seadistus loetakse keskkonnamuutujatest (docker-compose.yml environment-osa):
#      DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
#      CSV_PATH  (valikuline, vaikimisi /data/powerbi_test_dataset.csv)
#
#  Skript:
#      1. loeb ja puhastab CSV andmed (kuupäevad, NULL-id, tüübid),
#      2. loob tabeli 'sales' (kui pole olemas),
#      3. sisestab andmed kiire hulgimeetodiga (execute_values),
#      4. kontrollib tulemust.
# =============================================================================

import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# -----------------------------------------------------------------------------
#  SEADISTUS – loetakse keskkonnamuutujatest, vaikeväärtused sobivad Dockerile
# -----------------------------------------------------------------------------
CSV_PATH = os.environ.get("CSV_PATH", "/data/powerbi_test_dataset.csv")

DB_CONFIG = {
    "host":     os.environ.get("DB_HOST", "db"),
    "port":     int(os.environ.get("DB_PORT", "5432")),
    "dbname":   os.environ.get("DB_NAME", "postgres"),
    "user":     os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", ""),
}

TABLE_NAME = os.environ.get("TABLE_NAME", "sales")


# -----------------------------------------------------------------------------
#  1. CSV LUGEMINE JA PUHASTAMINE
# -----------------------------------------------------------------------------
def load_and_clean(path):
    """Loeb CSV-i ja teisendab andmed tabeli struktuuri jaoks sobivaks."""
    print(f"Loen faili: {path}")
    df = pd.read_csv(path)
    print(f"  Ridu failis: {len(df)}")

    # Veerud CSV-s: Date, Customer, Product, Category, Quantity, SalesAmount, Region
    # Nimetame ümber tabeli veergudele vastavaks.
    df = df.rename(columns={
        "Date":        "sale_date",
        "Customer":    "customer",
        "Product":     "product",
        "Category":    "category",
        "Quantity":    "quantity",
        "SalesAmount": "sales_amount",
        "Region":      "region",
    })

    # Kuupäev tekstist DATE-tüübiks. Vigased kuupäevad muutuvad NaT-iks.
    df["sale_date"] = pd.to_datetime(df["sale_date"], errors="coerce").dt.date

    # Numbrid kindlasse tüüpi; vigased -> NaN.
    df["quantity"]     = pd.to_numeric(df["quantity"], errors="coerce").astype("Int64")
    df["sales_amount"] = pd.to_numeric(df["sales_amount"], errors="coerce").round(2)

    # Tekstiveerud: eemalda üleliigsed tühikud.
    for col in ["customer", "product", "category", "region"]:
        df[col] = df[col].astype("string").str.strip()

    # Tühjad customer-väljad jäävad NULL-iks (pandas: <NA>).
    # Asenda kõik pandas-NA väärtused Pythoni None-iga, et psycopg2 sisestaks NULL.
    df = df.astype(object).where(pd.notnull(df), None)

    # Lisa tehniline primaarvõti id (1-st alates), kuna originaalis seda polnud.
    df.insert(0, "id", range(1, len(df) + 1))

    # Lühike kvaliteediülevaade enne sisestust.
    print("  Puuduvaid customer-välju:",
          sum(1 for v in df["customer"] if v is None))
    print("  Kuupäevavahemik:",
          min(d for d in df["sale_date"] if d is not None), "->",
          max(d for d in df["sale_date"] if d is not None))
    return df


# -----------------------------------------------------------------------------
#  2. TABELI LOOMINE
# -----------------------------------------------------------------------------
DDL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id           INTEGER PRIMARY KEY,
    sale_date    DATE,
    customer     VARCHAR(50),
    product      VARCHAR(50),
    category     VARCHAR(50),
    quantity     INTEGER,
    sales_amount NUMERIC(12,2),
    region       VARCHAR(20)
);
"""


def create_table(cur):
    """Loob sales-tabeli, kui seda veel pole."""
    cur.execute(DDL)
    print(f"Tabel '{TABLE_NAME}' on olemas/loodud.")


# -----------------------------------------------------------------------------
#  3. ANDMETE SISESTAMINE (kiire hulgimeetod)
# -----------------------------------------------------------------------------
def insert_rows(cur, df):
    """Sisestab kõik read ühe execute_values-kutsega (palju kiirem kui rea-haaval)."""
    cols = ["id", "sale_date", "customer", "product",
            "category", "quantity", "sales_amount", "region"]

    # Teisendame DataFrame'i ennikute listiks.
    rows = list(df[cols].itertuples(index=False, name=None))

    # ON CONFLICT väldib viga, kui sama id juba olemas (korduskäivitusel).
    sql = f"""INSERT INTO {TABLE_NAME} ({', '.join(cols)})
              VALUES %s
              ON CONFLICT (id) DO NOTHING"""

    execute_values(cur, sql, rows, page_size=1000)
    print(f"Sisestati {len(rows)} rida (olemasolevad id-d jäeti vahele).")


# -----------------------------------------------------------------------------
#  4. KONTROLL
# -----------------------------------------------------------------------------
def verify(cur):
    """Kontrollib sisestatud andmeid lihtsate päringutega."""
    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME};")
    print("Ridu tabelis kokku:", cur.fetchone()[0])

    cur.execute(f"""
        SELECT region, COUNT(*) AS n, ROUND(SUM(sales_amount), 2) AS total
        FROM {TABLE_NAME}
        GROUP BY region
        ORDER BY total DESC;
    """)
    print("Müük regiooniti:")
    for region, n, total in cur.fetchall():
        print(f"  {str(region):6} | ridu {n:4} | summa {total}")


# -----------------------------------------------------------------------------
#  PEAFUNKTSIOON
# -----------------------------------------------------------------------------
def main():
    # Loe ja puhasta andmed enne andmebaasiga ühendumist.
    df = load_and_clean(CSV_PATH)

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False          # käsitsi commit -> kõik-või-mitte-midagi
        with conn.cursor() as cur:
            create_table(cur)
            insert_rows(cur, df)
            verify(cur)
        conn.commit()                    # kinnita muudatused
        print("Valmis. Muudatused kinnitatud (COMMIT).")
    except (psycopg2.Error, FileNotFoundError) as e:
        if conn:
            conn.rollback()              # vea korral võta kõik tagasi
        print(f"VIGA: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
