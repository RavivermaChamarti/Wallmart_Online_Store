import os
import psycopg2

conn = psycopg2.connect(
        host="localhost",
        database="wallmart_store_db",
        user=os.environ['DB_USERNAME'],
        password=os.environ['DB_PASSWORD'])

# Open a cursor to perform database operations
cur = conn.cursor()

# Drop Tables if they exists already
cur.execute('DROP TABLE IF EXISTS boughtBy;')
cur.execute('DROP TABLE IF EXISTS bookmarkedBy;')
cur.execute('DROP TABLE IF EXISTS notifyAvailability;')
cur.execute('DROP TABLE IF EXISTS credentials;')
cur.execute('DROP TABLE IF EXISTS persons;')
cur.execute('DROP TABLE IF EXISTS products;')
cur.execute('DROP TABLE IF EXISTS categories;')


# Create the categories table
cur.execute('''CREATE TABLE categories (
                categoryId      SERIAL PRIMARY KEY,
                primaryCategory VARCHAR(50),
                subCategory1    VARCHAR(50),
                subCategory2    VARCHAR(50)
            );''')

# Create the products table
cur.execute('''CREATE TABLE products (
                SKU             VARCHAR(12) PRIMARY KEY,
                categoryId      INTEGER,
                title           VARCHAR(250),
                description     VARCHAR,
                currency        CHAR(3),
                price           NUMERIC(10, 2),
                brand           VARCHAR(30),
                available_stock INTEGER,
                url             VARCHAR,
                FOREIGN KEY (categoryId) REFERENCES categories
            );''')

# Create the persons table
cur.execute('''CREATE TABLE persons (
                personId    SERIAL PRIMARY KEY,
                first_name  VARCHAR,
                last_name   VARCHAR,
                email_id    VARCHAR(320) UNIQUE
            );''')

# Create the boughtBy table
cur.execute('''CREATE TABLE boughtBy (
                transactionId   SERIAL PRIMARY KEY,
                SKU             VARCHAR(12),
                personId        INTEGER,
                boughtOn        TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
                quantity        INTEGER,
                FOREIGN KEY (SKU) REFERENCES products,
                FOREIGN KEY (personId) REFERENCES persons
            );''')

# Create the bookmarkedBy table
cur.execute('''CREATE TABLE bookmarkedBy (
                SKU                 VARCHAR(12),
                personId            INTEGER,
                bookmarkedOn        TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (SKU, personId),
                FOREIGN KEY (SKU) REFERENCES products,
                FOREIGN KEY (personId) REFERENCES persons
            );''')

# Create the notifyAvailability table
cur.execute('''CREATE TABLE notifyAvailability (
                SKU             VARCHAR(12),
                personId        INTEGER,
                chosenOn       TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (SKU, personId),
                FOREIGN KEY (SKU) REFERENCES products,
                FOREIGN KEY (personId) REFERENCES persons
            );''')

# Create the credentials table
cur.execute('''CREATE TABLE credentials (
                username        VARCHAR,
                personID        INTEGER,
                salt            VARCHAR,
                passwordHash    VARCHAR,
                PRIMARY KEY (username),
                FOREIGN KEY (personId) REFERENCES persons
            );''')

conn.commit()

cur.close()
conn.close()