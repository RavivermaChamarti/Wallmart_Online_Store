import contextlib
import itertools
import os
from secrets import token_hex

import psycopg2
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_bcrypt import Bcrypt
from psycopg2.extras import RealDictCursor

from forms import LoginForms, RegistrationForms

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ["WALLMART_SECRET_KEY"]
bcrypt = Bcrypt()


@contextlib.contextmanager
def open_db(dictCur=True):
    conn = psycopg2.connect(
        host="localhost",
        database="wallmart_store_db",
        user=os.environ["DB_USERNAME"],
        password=os.environ["DB_PASSWORD"],
    )
    # Open a cursor to perform database operations
    if dictCur:
        cur = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cur = conn.cursor()

    yield cur
    conn.commit()
    cur.close()
    conn.close()


@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html", title="Home")


@app.route("/store")
def store():
    if "username" in session:
        user = session["username"]
        with open_db() as cur:
            cur.execute(
                """ SELECT
                        SKU,
                        title,
                        url,
                        brand,
                        currency,
                        price,
                        description,
                        primary_category,
                        sub_category_1,
                        sub_category_2
                    FROM products, categories
                    WHERE products.category_id = categories.category_id
                    LIMIT 10"""
            )
            products = cur.fetchall()
            # products= cur.fetchmany(10)

        with open_db(dictCur=False) as cur:
            cur.execute(
                f"""SELECT SKU
                        FROM bookmarkedBy, credentials
                        WHERE bookmarkedBy.person_id = credentials.person_id
                                AND credentials.username = '{user}'"""
            )
            bookmarked_products_tuples = cur.fetchall()
            bookmarked_products = list(itertools.chain(*bookmarked_products_tuples))

            cur.execute(
                f"""SELECT SKU
                        FROM notifyAvailability, credentials
                        WHERE notifyAvailability.person_id = credentials.person_id
                                AND credentials.username = '{user}'"""
            )
            notify_availability_products_tuples = cur.fetchall()
            notify_availability_products = list(itertools.chain(*notify_availability_products_tuples))

        return render_template(
            "store.html",
            title="Store",
            products=products,
            bookmarked_products=bookmarked_products,
            notify_availability_products=notify_availability_products
        )
    return render_template("invalidUser.html", title="Invalid User")


@app.route("/admin")
def admin():
    if "username" in session:
        if session["username"] == "Ravi":
            with open_db() as cur:
                cur.execute(f"""SELECT primary_category, sub_category_1, sub_category_2, SUM(products.price * boughtby.quantity) AS total
                                FROM products, boughtby, categories
                                WHERE products.sku = boughtby.sku
                                        AND products.category_id = categories.category_id
                                GROUP BY primary_category, sub_category_1, sub_category_2
                            """)
                earnings_by_category = cur.fetchall()


                cur.execute(f"""SELECT SUM(boughtby.quantity * products.price) AS total
                                FROM products, boughtBy
                                WHERE products.sku = boughtby.sku
                            """)
                total_spent=cur.fetchone()

                cur.execute(f"""SELECT url, title, brand, sku
                                FROM products
                                WHERE available_stock = 0
                            """)
                out_of_stock = cur.fetchall()
        return render_template("admin.html", title="Admin", earnings_by_category=earnings_by_category,total_spent=total_spent, out_of_stock=out_of_stock)
    return render_template("invalidUser.html", title="Invalid User")


@app.route("/profile")
def profile():
    if "username" in session:
        with open_db() as cur:
            cur.execute(f""" SELECT url, title, price, currency,  quantity, (price * quantity) AS spent,
                                TO_CHAR(
                                    (bought_on AT TIME ZONE 'UTC'
                                        AT TIME ZONE 'America/New_York'),
                                        'Mon DD, YYYY, HH24:MI:SS ') AS transaction_time
                            FROM products, boughtby, credentials
                            WHERE credentials.username = '{session["username"]}'
                                    AND boughtby.person_id = credentials.person_id
                                    AND products.sku = boughtby.sku
                        """)
            purchased_items = cur.fetchall()

            cur.execute(f""" SELECT url, title
                            FROM products, bookmarkedBy, credentials
                            WHERE credentials.username = '{session["username"]}'
                                    AND bookmarkedBy.person_id = credentials.person_id
                                    AND products.sku = bookmarkedBy.sku
                        """)
            bookmarked_items = cur.fetchall()

            cur.execute(f""" SELECT url, title
                            FROM products, notifyAvailability, credentials
                            WHERE credentials.username = '{session["username"]}'
                                    AND notifyAvailability.person_id = credentials.person_id
                                    AND products.sku = notifyAvailability.sku
                        """)
            waitlist_items = cur.fetchall()

            cur.execute(f"""SELECT categories.primary_category, SUM(boughtby.quantity * products.price) as total
                            FROM products, boughtBy, credentials, categories
                            WHERE products.category_id = categories.category_id
                                    AND boughtBy.sku = products.sku
                                    AND boughtBy.person_iD = credentials.person_iD
                            GROUP BY categories.primary_category, credentials.username
                            HAVING credentials.username = '{session["username"]}'
                        """)
            transaction_breakdown = cur.fetchall()

            cur.execute(f"""SELECT SUM(boughtby.quantity * products.price) as total
                            FROM products, boughtBy, credentials, categories
                            WHERE products.category_id = categories.category_id
                                    AND boughtBy.sku = products.sku
                                    AND boughtBy.person_iD = credentials.person_iD
                            GROUP BY credentials.username
                            HAVING credentials.username = '{session["username"]}'
                        """)
            total_spent=cur.fetchone()
        return render_template("profile.html", title="Profile", purchased_items=purchased_items, bookmarked_items=bookmarked_items, waitlist_items=waitlist_items,transaction_breakdown=transaction_breakdown, total_spent=total_spent)
    return render_template("invalidUser.html", title="Invalid User")


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForms()
    if form.validate_on_submit():
        with open_db() as cur:
            cur.execute(
                f"""SELECT first_name, last_name, salt, password_hash, username
                            FROM persons, credentials
                            WHERE username='{form.username.data}'
                                    AND credentials.person_id=persons.person_id"""
            )
            user = cur.fetchone()
            if user and bcrypt.check_password_hash(
                user["password_hash"], user["salt"] + form.password.data
            ):
                session["username"] = user["username"]
                flash(
                    f"Welcome Back {user['first_name']} {user['last_name']}!", "success"
                )
                return redirect(url_for("store"))
            else:
                flash(
                    f"Login Unsuccessful! Use a valid Username and Password", "danger"
                )
    return render_template("login.html", title="Login", form=form)


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForms()
    if form.validate_on_submit():
        with open_db() as cur:
            cur.execute(
                f"""INSERT INTO persons(first_name, last_name, email_id)
                            VALUES ('{form.first_name.data}','{form.last_name.data}', '{form.email_id.data}' )"""
            )
            cur.execute(
                f"""SELECT person_id
                            FROM persons
                            WHERE first_name='{form.first_name.data}'
                                    AND last_name='{form.last_name.data}'
                                    AND email_id='{form.email_id.data}'"""
            )
            user = cur.fetchone()
            person_id = user["person_id"]
            salt = token_hex(16)
            password_hash = bcrypt.generate_password_hash(
                salt + form.password.data
            ).decode("utf-8")
            cur.execute(
                f"""INSERT INTO credentials(username, person_iD, salt, password_hash)
                            VALUES ('{form.username.data}','{person_id}', '{salt}', '{password_hash}' )"""
            )
            flash(
                f"Account Created for {form.first_name.data} {form.last_name.data}!",
                "success",
            )
            return redirect(url_for("store"))
    return render_template("register.html", title="Register", form=form)


@app.route("/logout")
def logout():
    session.clear()
    return render_template("home.html", title="Home")


@app.route("/buy", methods=["POST"])
def buy():
    if request.method == "POST":
        with open_db() as cur:
            cur.execute(f"""SELECT available_stock
                            FROM products
                            WHERE sku='{request.form["sku"]}'""")
            stock = (cur.fetchone())["available_stock"]

            cur.execute(f"""SELECT *
                FROM credentials
                WHERE username='{session["username"]}'""")
            user = cur.fetchone()

            if stock >= int(request.form["quantity"]):
                new_stock = stock - int(request.form["quantity"])
                cur.execute(f"""UPDATE products
                                SET available_stock={new_stock}
                                WHERE sku='{request.form["sku"]}'""")
                cur.execute(f"""INSERT INTO boughtBy(sku, person_id, quantity)
                                VALUES ('{request.form["sku"]}', '{user["person_id"]}','{request.form["quantity"]}' )""")
            else:
                flash(
                    f"Sorry! Only {stock} number of that product are available!", "danger"
                )
    return redirect(str(request.referrer)+ f'#{request.form["sku"]}')


@app.route("/bookmark", methods=["POST"])
def bookmark():
    if request.method == "POST":
        with open_db() as cur:
            cur.execute(f"""SELECT *
                            FROM credentials
                            WHERE username='{session["username"]}'""")
            user = cur.fetchone()
            cur.execute(f"""SELECT SKU, person_id
                            FROM bookmarkedBy
                            WHERE   sku='{request.form["sku"]}'
                                    AND person_id='{user["person_id"]}'""")
            bookmarked_product = cur.fetchone()
            if bookmarked_product is None:
                cur.execute(f"""INSERT INTO bookmarkedby(sku, person_id)
                                VALUES ('{request.form["sku"]}', '{user["person_id"]}')""")
            else:
                cur.execute(f"""DELETE FROM bookmarkedby
                            WHERE sku='{request.form["sku"]}'
                                    AND person_id='{user["person_id"]}'""")
    return redirect(request.referrer)

@app.route("/notify_availability", methods=["POST"])
def notify_availability():
    if request.method == "POST":
        with open_db() as cur:
            cur.execute(f"""SELECT *
                            FROM credentials
                            WHERE username='{session["username"]}'""")
            user = cur.fetchone()
            cur.execute(f"""SELECT SKU, person_id
                            FROM notifyAvailability
                            WHERE   sku='{request.form["sku"]}'
                                    AND person_id='{user["person_id"]}'""")
            waitlisted_products = cur.fetchone()
            if waitlisted_products is None:
                cur.execute(f"""INSERT INTO notifyAvailability(sku, person_id)
                                VALUES ('{request.form["sku"]}', '{user["person_id"]}')""")
            else:
                cur.execute(f"""DELETE FROM notifyAvailability
                                WHERE sku='{request.form["sku"]}'
                                    AND person_id='{user["person_id"]}'""")
    return redirect(request.referrer)



@app.route("/restock", methods=["POST"])
def restock():
    if request.method == "POST":
        with open_db() as cur:
            cur.execute(f"""SELECT available_stock, title
                            FROM products
                            WHERE sku='{request.form["restock_item"]}'""")
            stock = cur.fetchone()
            new_stock = stock["available_stock"] + 200
            cur.execute(f"""UPDATE products
                            SET available_stock={new_stock}
                            WHERE sku='{request.form["restock_item"]}'""")
        flash(
                f"{ stock['title'] } has been restocked", "success"
            )
    return redirect(request.referrer)

@app.route("/restock_all", methods=["POST"])
def restock_all():
    if request.method == "POST":
        with open_db() as cur:
            cur.execute(f"""UPDATE products
                            SET available_stock=200
                            WHERE available_stock=0""")
        flash(
                f"All necessary products have been restocked", "success"
            )
    return redirect(request.referrer)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port="2000", debug=True)
