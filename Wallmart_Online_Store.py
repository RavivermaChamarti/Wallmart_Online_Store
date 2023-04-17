import os

import psycopg2
from flask import Flask, render_template
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

import contextlib


@contextlib.contextmanager
def open_db():
    conn = psycopg2.connect(
        host="localhost",
        database="wallmart_store_db",
        user=os.environ["DB_USERNAME"],
        password=os.environ["DB_PASSWORD"]
        )

    # Open a cursor to perform database operations
    cur = conn.cursor(cursor_factory=RealDictCursor)

    yield cur

    conn.commit()
    cur.close()
    conn.close()


@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html", title="home")

@app.route("/login")
def login():
    return render_template("login.html", title="login")


@app.route("/register")
def register():
    return render_template("register.html", title="register")


@app.route("/logout")
def logout():
    return render_template("invalidUser.html", title="logout")


@app.route("/store")
def store():
    with open_db() as cur:
        cur.execute("SELECT SKU, category_id, title, url, brand, currency, price, description FROM products")
        products = cur.fetchall()
    products_list = []
    for row in products:
        products_list.append(dict(row))

    print(len(products_list))

    return render_template("store.html", title="store", products=products_list)


@app.route("/admin")
def admin():
    return render_template("admin.html", title="admin")


@app.route("/profile")
def profile():
    return render_template("profile.html", title="profile")


if __name__ == "__main__":
    app.run(host='0.0.0.0')
