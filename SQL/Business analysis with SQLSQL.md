# Using SQL Queries in Business Analysis

This example uses a Docker environment where a PostgreSQL and a Python container are launched to run SQL and Python scripts for data loading and analysis.

Starting Docker:

```bash
# Copying environment variables
cp .env.example .env

# All services (Postgre SQL, Python)
docker compose up -d --build
docker compose ps   # wait for "healthy" / "running"
```

Running SQL:

```text
docker compose exec db psql -U user -d postgresql
```

Creating SQL tabel:

```sql
\i /scripts/Create_SQL_table_sales.sql
```

Check the resultt:

```text
\dt
```

Check that the schemas were created:

```text
\dn
```

Loading CSV data with Python:

```text
docker compose exec python python //scripts/import_sales.py
```

PROFILING

-- Total number of rows

```sql
SELECT COUNT(*) AS rows_total FROM sales;
```

-- Unique values in dimensions

```sql
SELECT
    COUNT(DISTINCT product)  AS products,
    COUNT(DISTINCT customer) AS customers,
    COUNT(DISTINCT category) AS categories,
    COUNT(DISTINCT region)   AS regions
FROM sales;
```

-- Missing values by column

```sql
SELECT
    SUM(CASE WHEN customer     IS NULL THEN 1 ELSE 0 END) AS missing_customer,
    SUM(CASE WHEN sale_date    IS NULL THEN 1 ELSE 0 END) AS missing_date,
    SUM(CASE WHEN sales_amount IS NULL THEN 1 ELSE 0 END) AS missing_amount
FROM sales;
```

-- Statistical summary (equivalent to describe())

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

-- Mediaan.

```sql
SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sales_amount) AS median_amt
FROM sales;
```

DATA QUALITY AND ANOMALIES

-- Extreme sales amounts (outliers)

```sql
SELECT * FROM sales WHERE sales_amount > 10000 ORDER BY sales_amount DESC;
```

-- Invalid quantities

```sql
SELECT * FROM sales WHERE quantity = 0 OR quantity < 0;
```

-- Exact duplicates (all columns except id are the same)

```sql
SELECT sale_date, customer, product, category, quantity, sales_amount, region,
       COUNT(*) AS dup_count
FROM sales
GROUP BY sale_date, customer, product, category, quantity, sales_amount, region
HAVING COUNT(*) > 1;
```

-- Exact duplicates (all columns except id are the same)

```sql
CREATE VIEW sales_clean AS
SELECT * FROM sales
WHERE sales_amount < 10000
  AND quantity > 0;
```

AGGREGATION AND SEGMENTATION

-- Sales by region (sum, average, count – three views)

```sql
SELECT region,
       SUM(sales_amount)   AS total_sales,
       AVG(sales_amount)   AS avg_sale,
       COUNT(*)            AS tx_count
FROM sales_clean
GROUP BY region
ORDER BY total_sales DESC;
```

-- Sales by category

```sql
SELECT category,
       SUM(sales_amount) AS total_sales,
       AVG(sales_amount) AS avg_sale,
       COUNT(*)          AS tx_count
FROM sales_clean
GROUP BY category
ORDER BY total_sales DESC;
```

-- Cross-table / Pivot table: Region × Category (equivalent to pivot_table)

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

MULTIPLE CATEGORIES: Pareto / ABC Analysis

-- Pareto: products that generate 80% of revenue (window functions)

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

Running_total / grand_total gives the cumulative percentage; Class A = products that combined make up 80% of the revenue.

TIME TRENDS AND FORECASTING

-- Sales by month

```sql
SELECT DATE_TRUNC('month', sale_date) AS month,   -- PostgreSQL
       SUM(sales_amount)              AS monthly_sales,
       COUNT(*)                       AS tx_count
FROM sales_clean
GROUP BY DATE_TRUNC('month', sale_date)
ORDER BY month;
```

-- 3-month moving average (for smoothing)

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

-- Year-over-Year (YoY) comparison by month

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

-- Unit price by product (price analysis)

```sql
SELECT product,
       ROUND(SUM(sales_amount) / NULLIF(SUM(quantity), 0), 2) AS avg_unit_price
FROM sales_clean
GROUP BY product
ORDER BY avg_unit_price DESC;
```

-- Top customers (basic foundation for RFM)

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

