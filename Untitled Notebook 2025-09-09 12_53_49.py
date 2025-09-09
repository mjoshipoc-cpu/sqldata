# Databricks notebook source
# MAGIC %sql
# MAGIC USE bronze;
# MAGIC CREATE TABLE bronze.customer_bronze AS
# MAGIC SELECT * FROM samples.tpch.customer;
# MAGIC

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT COUNT(*) FROM bronze.customer_bronze;
# MAGIC

# COMMAND ----------

# MAGIC %sql
# MAGIC use bronze;
# MAGIC create table nation_bronze as
# MAGIC select * from samples.tpch.nation

# COMMAND ----------

# MAGIC %sql
# MAGIC use bronze;
# MAGIC ALTER TABLE bronze.customer_bronze
# MAGIC ADD COLUMNS (
# MAGIC   created_date TIMESTAMP,
# MAGIC   updated_date TIMESTAMP
# MAGIC );
# MAGIC ALTER TABLE bronze.order_bronze
# MAGIC ADD COLUMNS (
# MAGIC   created_date TIMESTAMP,
# MAGIC   updated_date TIMESTAMP
# MAGIC );
# MAGIC ALTER TABLE nation_bronze
# MAGIC ADD COLUMNS (
# MAGIC   created_date TIMESTAMP,
# MAGIC   updated_date TIMESTAMP
# MAGIC );

# COMMAND ----------

# MAGIC %sql
# MAGIC use bronze;
# MAGIC update customer_bronze
# MAGIC set created_date = current_timestamp(), updated_date = current_timestamp();
# MAGIC update order_bronze
# MAGIC set created_date = current_timestamp(), updated_date = current_timestamp();
# MAGIC update nation_bronze
# MAGIC set created_date = current_timestamp(), updated_date = current_timestamp()

# COMMAND ----------

# MAGIC %sql
# MAGIC
# MAGIC
# MAGIC DESCRIBE TABLE samples.tpch.customer;

# COMMAND ----------

# MAGIC %sql
# MAGIC WITH baseline AS (
# MAGIC   DESCRIBE TABLE samples.tpch.customer;
# MAGIC )

# COMMAND ----------

# MAGIC %sql
# MAGIC WITH baseline AS (
# MAGIC   SELECT column_name, data_type
# MAGIC   FROM information_schema.columns
# MAGIC   WHERE table_schema = 'samples.tpch' AND table_name = 'customer'
# MAGIC ),
# MAGIC target AS (
# MAGIC   SELECT column_name, data_type
# MAGIC   FROM information_schema.columns
# MAGIC   WHERE table_schema = 'bronze' AND table_name = 'customer_bronze'
# MAGIC )
# MAGIC
# MAGIC SELECT
# MAGIC   baseline.column_name AS baseline_column,
# MAGIC   baseline.data_type AS baseline_type,
# MAGIC   target.column_name AS target_column,
# MAGIC   target.data_type AS target_type,
# MAGIC   CASE
# MAGIC     WHEN baseline.column_name = target.column_name AND baseline.data_type = target.data_type THEN 'Match'
# MAGIC     ELSE 'Mismatch or Missing'
# MAGIC   END AS validation_result
# MAGIC FROM baseline
# MAGIC FULL OUTER JOIN target
# MAGIC   ON baseline.column_name = target.column_name
# MAGIC ORDER BY baseline.column_name;
# MAGIC

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE SCHEMA IF NOT EXISTS silver;
# MAGIC CREATE TABLE silver.customer_silver AS
# MAGIC SELECT *
# MAGIC FROM (
# MAGIC   SELECT *,
# MAGIC     ROW_NUMBER() OVER (PARTITION BY c_custkey ORDER BY c_custkey) AS rn
# MAGIC   FROM bronze.customer_bronze
# MAGIC   WHERE c_custkey IS NOT NULL
# MAGIC ) t
# MAGIC WHERE t.rn = 1;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE SCHEMA IF NOT EXISTS silver;
# MAGIC CREATE TABLE silver.order_silver AS
# MAGIC SELECT *
# MAGIC FROM (
# MAGIC   SELECT *,
# MAGIC     ROW_NUMBER() OVER (PARTITION BY o_orderkey ORDER BY o_orderkey) AS rn
# MAGIC   FROM bronze.order_bronze
# MAGIC   WHERE o_orderkey IS NOT NULL
# MAGIC ) t
# MAGIC WHERE t.rn = 1;
# MAGIC

# COMMAND ----------

# MAGIC %sql
# MAGIC create schema if not exists gold;
# MAGIC crEATE TABLE gold.customer_order_counts AS
# MAGIC SELECT
# MAGIC   c_custkey,
# MAGIC   COUNT(o_orderkey) AS order_count
# MAGIC FROM samples.tpch.customer c
# MAGIC LEFT JOIN samples.tpch.orders o ON c.c_custkey = o.o_custkey
# MAGIC GROUP BY c.c_custkey;

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from gold.customer_order_counts