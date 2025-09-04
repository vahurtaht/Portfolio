-- Leia müügisummad toodete kaupa
select product_id, SUM (salestable.unit_price * salestable.quantity * (1-discount)) as totalsize
from salestable
group by product_id; 

select product_id, round(sum(sales_sum),2)
from salestable
group by product_id 
order by product_id; 

-- Leia müügisummad klientide kaupa
select customer_id, SUM (salestable.unit_price * salestable.quantity * (1-discount)) as sale_sume
from salestable
group by customer_id; 

-- Leia müügisummad müügiesindajate kaupa
select sales_rep_id, SUM (salestable.unit_price * salestable.quantity * (1-discount)) as totalsize
from salestable
group by sales_rep_id
order by sales_rep_id;  

select sales_rep_id, round(sum(sales_sum)) as sales_sum
from salestable s 
group by sales_rep_id
order by sales_rep_id; 

-- Leia müügisummad aastate kaupa
select TO_CHAR(sale_date, 'YYYY') as year, SUM (salestable.unit_price * salestable.quantity * (1-discount)) as sales_sum
from salestable
group by TO_CHAR(sale_date, 'YYYY')
order by sales_sum asc;

select TO_CHAR(sale_date, 'YYYY') as year, round(sum(sales_sum)) as sales_sum
from salestable
group by TO_CHAR(sale_date, 'YYYY')
order by sales_sum asc;

-- Lisa müükidele müügisumma kategooriad

-- Large Sale > 500
-- Medium Sale <= 500 and >= 250
-- Small Sale < 250
select sales_sum, 
case when sales_sum < 250 then 'Small Sale'
	when sales_sum >= 250 and sales_sum >= 500 then 'Medium Sale'
	else 'Large Sale' end as sales_category
	from salestable;
	

-- Leia müükide arv ja müügisumma müügisumma kategooriate kaupa
select case	when sales_sum > 500 then 'Large Sale'
	when sales_sum >= 250 then 'Medium Sale'
	else 'Small Sale' end as sales_category,
	count(*) as number_of_sales,
	round(sum(sales_sum)::numeric, 0) as sales_sum
	from salestable
	group by sales_category
	order by sales_category desc; 


-- Mida veel võiks leida?