import os

import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="wallmart_store_db",
    user=os.environ["DB_USERNAME"],
    password=os.environ["DB_PASSWORD"],
)

# Open a cursor to perform database operations
cur = conn.cursor()

# Drop Tables if they exists already
cur.execute("DROP TABLE IF EXISTS boughtBy;")
cur.execute("DROP TABLE IF EXISTS bookmarkedBy;")
cur.execute("DROP TABLE IF EXISTS notifyAvailability;")
cur.execute("DROP TABLE IF EXISTS credentials;")
cur.execute("DROP TABLE IF EXISTS persons;")
cur.execute("DROP TABLE IF EXISTS products;")
cur.execute("DROP TABLE IF EXISTS categories;")


# Create the categories table
cur.execute(
    """CREATE TABLE categories (
                category_id       SERIAL PRIMARY KEY,
                primary_category  VARCHAR(50),
                sub_category_1    VARCHAR(50),
                sub_category_2    VARCHAR(50)
            );"""
)

# Create the products table
cur.execute(
    """CREATE TABLE products (
                SKU             VARCHAR(12) PRIMARY KEY,
                category_id     INTEGER,
                title           VARCHAR(250),
                description     VARCHAR,
                currency        CHAR(3),
                price           NUMERIC(10, 2),
                brand           VARCHAR(30),
                available_stock INTEGER,
                url             VARCHAR,
                FOREIGN KEY (category_id) REFERENCES categories
            );"""
)

# Create the persons table
cur.execute(
    """CREATE TABLE persons (
                person_id   SERIAL PRIMARY KEY,
                first_name  VARCHAR,
                last_name   VARCHAR,
                email_id    VARCHAR(320) UNIQUE
            );"""
)

# Create the boughtBy table
cur.execute(
    """CREATE TABLE boughtBy (
                transaction_id      SERIAL PRIMARY KEY,
                SKU                 VARCHAR(12),
                person_id           INTEGER,
                bought_on           TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
                quantity            INTEGER,
                FOREIGN KEY (SKU) REFERENCES products,
                FOREIGN KEY (person_id) REFERENCES persons
            );"""
)

# Create the bookmarkedBy table
cur.execute(
    """CREATE TABLE bookmarkedBy (
                SKU                  VARCHAR(12),
                person_id            INTEGER,
                bookmarked_on        TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (SKU, person_id),
                FOREIGN KEY (SKU) REFERENCES products,
                FOREIGN KEY (person_id) REFERENCES persons
            );"""
)

# Create the notifyAvailability table
cur.execute(
    """CREATE TABLE notifyAvailability (
                SKU             VARCHAR(12),
                person_id        INTEGER,
                chosen_on       TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (SKU, person_id),
                FOREIGN KEY (SKU) REFERENCES products,
                FOREIGN KEY (person_id) REFERENCES persons
            );"""
)

# Create the credentials table
cur.execute(
    """CREATE TABLE credentials (
                username        VARCHAR PRIMARY KEY,
                person_iD        INTEGER,
                salt            VARCHAR,
                password_hash    VARCHAR,
                FOREIGN KEY (person_id) REFERENCES persons
            );"""
)

conn.commit()

cur.close()
conn.close()
