# test

Siin on testimise koht!

Dockeri käivitamine:

```text
docker compose up -d --build

```

SQL käivitamine:

```text
docker compose exec db psql -U user -d postgresql

```

SQL tabeli loomine:

```sql
\i /scripts/Create_SQL_table_sales.sql

```

Kontrolli tulemust:

```text
\dt

```

Kontrolli, et skeemid tekkisid:

```text
\dn

```

CSV andmete laadimine Pythoniga:

```text
docker compose exec python python //scripts/import_sales.py

```

PROFILEERIMINE

-- Ridade arv

```sql
SELECT COUNT(*) AS rows_total FROM sales;

```

-- Unikaalsed väärtused dimensioonides

```sql
SELECT
    COUNT(DISTINCT product)  AS products,
    COUNT(DISTINCT customer) AS customers,
    COUNT(DISTINCT category) AS categories,
    COUNT(DISTINCT region)   AS regions
FROM sales;

```

-- Puuduvad väärtused veergude lõikes

```sql
SELECT
    SUM(CASE WHEN customer     IS NULL THEN 1 ELSE 0 END) AS missing_customer,
    SUM(CASE WHEN sale_date    IS NULL THEN 1 ELSE 0 END) AS missing_date,
    SUM(CASE WHEN sales_amount IS NULL THEN 1 ELSE 0 END) AS missing_amount
FROM sales;

```

-- Statistiline kokkuvõte (vaste describe()-le)

```sql
SELECT
    MIN(sales_amount)    AS min_amt,
    MAX(sales_amount)    AS max_amt,
    AVG(sales_amount)    AS avg_amt,
    STDDEV(sales_amount) AS std_amt,
    MIN(sale_date)       AS first_date,
    MAX(sale_date)       AS last_date
FROM sales;

```

-- Mediaan (PostgreSQL/Oracle). MySQL-is mediaani otse pole.

```sql
SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sales_amount) AS median_amt
FROM sales;

```

ANDMEKVALITEET JA ANOMAALIAD

-- Äärmuslikud müügisummad (outlier'id)

```sql
SELECT * FROM sales WHERE sales_amount > 10000 ORDER BY sales_amount DESC;

```

-- Vigased kogused

```sql
SELECT * FROM sales WHERE quantity = 0 OR quantity < 0;

```

-- Täpsed duplikaadid (kõik veerud peale id sama)

```sql
SELECT sale_date, customer, product, category, quantity, sales_amount, region,
       COUNT(*) AS dup_count
FROM sales
GROUP BY sale_date, customer, product, category, quantity, sales_amount, region
HAVING COUNT(*) > 1;

```

-- Korduvkasutatav "puhastatud" vaade: jätame välja anomaalia

```sql
CREATE VIEW sales_clean AS
SELECT * FROM sales
WHERE sales_amount < 10000
  AND quantity > 0;

```

AGREGEERIMINE JA SEGMENTEERIMINE

-- Müük regiooniti (summa, keskmine, arv – kolm vaadet)

```sql
SELECT region,
       SUM(sales_amount)   AS total_sales,
       AVG(sales_amount)   AS avg_sale,
       COUNT(*)            AS tx_count
FROM sales_clean
GROUP BY region
ORDER BY total_sales DESC;

```

-- Müük kategooriati

```sql
SELECT category,
       SUM(sales_amount) AS total_sales,
       AVG(sales_amount) AS avg_sale,
       COUNT(*)          AS tx_count
FROM sales_clean
GROUP BY category
ORDER BY total_sales DESC;

```

-- Risttabel: Regioon × Kategooria (vaste pivot_table-le)

```sql
SELECT region,
       SUM(CASE WHEN category = 'Cosmetics'  THEN sales_amount ELSE 0 END) AS cosmetics,
       SUM(CASE WHEN category = 'Drinks'     THEN sales_amount ELSE 0 END) AS drinks,
       SUM(CASE WHEN category = 'Food'       THEN sales_amount ELSE 0 END) AS food,
       SUM(CASE WHEN category = 'Handicraft' THEN sales_amount ELSE 0 END) AS handicraft
FROM sales_clean
GROUP BY region
ORDER BY region;

```

PALJUD KATEGOORIAD: Pareto / ABC-analüüs

-- Pareto: tooted, mis annavad 80% käibest (window-funktsioonid)

```sql
\i /scripts/pairing.sql

```

```sql
WITH product_sales AS (
    SELECT product, SUM(sales_amount) AS total
    FROM sales_clean
    GROUP BY product
),
ranked AS (
    SELECT product, total,
           SUM(total) OVER (ORDER BY total DESC) AS running_total,
           SUM(total) OVER ()                    AS grand_total
    FROM product_sales
)
SELECT product, total,
       ROUND(100.0 * running_total / grand_total, 1) AS cum_percent,
       CASE
           WHEN 100.0 * running_total / grand_total <= 80 THEN 'A'
           WHEN 100.0 * running_total / grand_total <= 95 THEN 'B'
           ELSE 'C'
       END AS abc_class
FROM ranked
ORDER BY total DESC;

```

running_total / grand_total annab kumulatiivse protsendi; A-klass = tooted, mis kokku moodustavad 80% käibest.

AJATRENDID JA PROGNOOS

-- Müük kuude lõikes

```sql
SELECT DATE_TRUNC('month', sale_date) AS month,   -- PostgreSQL
       SUM(sales_amount)              AS monthly_sales,
       COUNT(*)                       AS tx_count
FROM sales_clean
GROUP BY DATE_TRUNC('month', sale_date)
ORDER BY month;

```

-- 3-kuu liikuv keskmine (silumiseks)

```sql
WITH monthly AS (
    SELECT DATE_TRUNC('month', sale_date) AS month,
           SUM(sales_amount)              AS monthly_sales
    FROM sales_clean
    GROUP BY DATE_TRUNC('month', sale_date)
)
SELECT month, monthly_sales,
       ROUND(AVG(monthly_sales) OVER (
           ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
       ), 0) AS moving_avg_3m
FROM monthly
ORDER BY month;

```

-- Aasta-üle-aasta (YoY) võrdlus kuu kaupa

```sql
WITH monthly AS (
    SELECT DATE_TRUNC('month', sale_date) AS month,
           SUM(sales_amount)              AS monthly_sales
    FROM sales_clean
    GROUP BY DATE_TRUNC('month', sale_date)
)
SELECT month, monthly_sales,
       LAG(monthly_sales, 12) OVER (ORDER BY month) AS same_month_last_year,
       ROUND(100.0 * (monthly_sales - LAG(monthly_sales,12) OVER (ORDER BY month))
             / NULLIF(LAG(monthly_sales,12) OVER (ORDER BY month), 0), 1) AS yoy_percent
FROM monthly
ORDER BY month;

```

-- Ühikuhind toote kaupa (hinnaanalüüs)

```sql
SELECT product,
       ROUND(SUM(sales_amount) / NULLIF(SUM(quantity), 0), 2) AS avg_unit_price
FROM sales_clean
GROUP BY product
ORDER BY avg_unit_price DESC;

```

-- Top kliendid (lihtne RFM-i alus)

```sql
SELECT customer,
       COUNT(*)                            AS frequency,
       SUM(sales_amount)                   AS monetary,
       MAX(sale_date)                      AS last_purchase,
       CURRENT_DATE - MAX(sale_date)       AS recency_days
FROM sales_clean
WHERE customer IS NOT NULL
GROUP BY customer
ORDER BY monetary DESC
LIMIT 10;

```
