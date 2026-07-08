CREATE TABLE IF NOT EXISTS sales (
    id           INT PRIMARY KEY,        -- tehnilise võtmena lisatud
    sale_date    DATE,
    customer     VARCHAR(50),            -- võib olla NULL
    product      VARCHAR(50),
    category     VARCHAR(50),
    quantity     INT,
    sales_amount DECIMAL(12,2),
    region       VARCHAR(20)
);

-- Korduvkasutatav "puhastatud" vaade: jätame välja anomaaliad
CREATE OR REPLACE VIEW sales_clean AS
SELECT * FROM sales
WHERE sales_amount < 10000
  AND quantity > 0;