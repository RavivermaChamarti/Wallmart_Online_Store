import csv
import os
from io import StringIO
from pathlib import Path

import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="wallmart_store_db",
    user=os.environ["DB_USERNAME"],
    password=os.environ["DB_PASSWORD"],
)

# Open a cursor to perform database operations
cur = conn.cursor()

categories_list_data = Path("./data/CategoriesList.csv")

with open(categories_list_data, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    next(reader)  # Skip the header row.
    for row in reader:
        cur.execute(
            """INSERT INTO categories(primary_category, sub_category_1, sub_category_2)
                        VALUES (%s, %s, %s)""",
            row,
        )

conn.commit()

cur.close()
conn.close()
