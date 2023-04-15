import csv
import os
import sys
from io import StringIO
from pathlib import Path

import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="wallmart_store_db",
    user=os.environ["DB_USERNAME"],
    password=os.environ["DB_PASSWORD"]
)

# Open a cursor to perform database operations
cur = conn.cursor()

# Delete existing data from tables
cur.execute("DELETE FROM products;")
cur.execute("DELETE FROM products_stage;")
cur.execute("DELETE FROM categories;")



# Populate the categories table
categories_list_data = Path("./data/CategoriesList.csv")
with open(categories_list_data, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    next(reader)  # Skip the header row.
    for row in reader:
        cur.execute(
            """INSERT INTO categories(primary_category, sub_category_1, sub_category_2)
                        VALUES (%s, %s, %s);""",
            row
            )

# Create a temporary staging table for the products
cur.execute("DROP TABLE IF EXISTS products_stage;")
cur.execute(
    """CREATE TABLE products_stage(
                SKU             VARCHAR(12) PRIMARY KEY,
                title           VARCHAR(250),
                description     VARCHAR,
                currency        CHAR(3),
                price           NUMERIC(10, 2),
                brand           VARCHAR(30),
                url             VARCHAR,
                primary_category  VARCHAR(50),
                sub_category_1    VARCHAR(50),
                sub_category_2    VARCHAR(50)
            );"""
)

# Populate the products_stage table with data
products_list_data = Path("./data/ProductsList.csv")
with open(products_list_data) as csv_file:
    cur.copy_expert("copy products_stage from stdin with csv header", csv_file)

# Populate the products table with data
cur.execute(""" INSERT INTO products(SKU, category_id, title, description, currency, price, brand, available_stock, url)
                SELECT SKU, categories.category_id, title, description, currency, price, brand, floor(random() * (500+1))::int, url
                FROM products_stage, categories
                WHERE products_stage.primary_category = categories.primary_category
                        AND products_stage.sub_category_1 = categories.sub_category_1
                        AND products_stage.sub_category_2 = categories.sub_category_2;""")


# cur.execute("DROP TABLE IF EXISTS products_stage;")

conn.commit()

cur.close()
conn.close()
