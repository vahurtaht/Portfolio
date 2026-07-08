-- Tagame, et sales_clean vaade on loodud
CREATE OR REPLACE VIEW sales_clean AS
SELECT * FROM sales
WHERE sales_amount < 10000
  AND quantity > 0;

-- Pareto: tooted, mis annavad 80% käibest (window-funktsioonid)
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