import contextlib
import itertools
import os
import smtplib
from email.message import EmailMessage
from secrets import token_hex

import numpy as np
import pandas as pd
import psycopg2
import turicreate as tc
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_bcrypt import Bcrypt
from implicit.als import AlternatingLeastSquares
from psycopg2.extras import RealDictCursor
from scipy.sparse import coo_matrix

from forms import LoginForms, RegistrationForms

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ["WALLMART_SECRET_KEY"]
EMAIL_ADDRESS = os.environ["EMAIL_USER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
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
                    ORDER BY sku DESC"""
            )
            products = cur.fetchall()

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


@app.route("/reccomendations")
def reccomendations():
    if "username" in session:
        with open_db(dictCur=False) as cur:
            cur.execute(""" SELECT boughtBy.person_id, boughtBy.sku, categories.category_id
                            FROM boughtBy, products, categories
                            WHERE boughtBy.sku = products.sku
                                    AND products.category_id=categories.category_id;""")

            grouped_data = cur.fetchall()
            columns = ['user_id', 'product_id', 'category_id']
            data = pd.DataFrame(grouped_data, columns=columns)
            unique_user_ids = data['user_id'].nunique()

            if not data.empty and unique_user_ids >= 2:
                sf_data = tc.SFrame(data)
                # Create a model using the implicit collaborative filtering
                model = tc.item_similarity_recommender.create(sf_data, user_id='user_id', item_id='category_id', similarity_type='cosine')
                # Generate recommendations
                category_recommendations = model.recommend(k=10)

                model = tc.item_similarity_recommender.create(sf_data, user_id='user_id', item_id='product_id', similarity_type='cosine')
                # Generate recommendations
                product_recommendations = model.recommend(k=10)

                # Convert the recommendations to a DataFrame
                df_category_recommendations = category_recommendations.to_dataframe()
                df_product_recommendation = product_recommendations.to_dataframe()

                with open_db() as cur:
                    cur.execute(f"""SELECT person_id
                                    FROM credentials
                                    WHERE username='{session["username"]}'""")

                    user_id = (cur.fetchone())["person_id"]
                    current_user_category_reccomendations = df_category_recommendations[df_category_recommendations['user_id'] == user_id]
                    current_user_product_reccomendations = df_product_recommendation[df_product_recommendation['user_id'] == user_id]

                reccomended_categories =[]
                for i in current_user_category_reccomendations.to_dict('records'):
                    reccomended_categories.append(i['category_id'])

                reccomended_products =[]
                for i in current_user_product_reccomendations.to_dict('records'):
                    reccomended_products.append(i['product_id'])

                reccomended_products=tuple(reccomended_products)
                reccomended_categories=tuple(reccomended_categories)
                with open_db() as cur:
                    if (len(reccomended_categories) !=0 ) and (len(reccomended_products) !=0 ):
                        cur.execute(f"""SELECT url, title, sku, brand, price, currency, price, description, primary_category, sub_category_1, sub_category_2
                                        FROM products, categories
                                        WHERE (products.category_id IN {reccomended_categories}
                                                OR products.sku IN {reccomended_products})
                                                AND products.category_id=categories.category_id
                                        ORDER BY products.sku ASC;""")
                        products = cur.fetchall()
                        reccomendations_present=True

                        with open_db(dictCur=False) as cur:
                            user = session["username"]
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
                        return render_template("reccomendation.html", reccomendations_present=reccomendations_present, products=products,bookmarked_products=bookmarked_products,notify_availability_products=notify_availability_products)
                    else:
                        reccomendations_present=False
                        return render_template("reccomendation.html", reccomendations_present=reccomendations_present)
            else:
                reccomendations_present=False
                return render_template("reccomendation.html", reccomendations_present=reccomendations_present)
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
            return redirect(url_for("login"))
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
    return redirect(str(request.referrer)+ f'#{request.form["sku"]}')

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
    return redirect(str(request.referrer)+ f'#{request.form["sku"]}')



@app.route("/restock", methods=["POST"])
def restock():
    if request.method == "POST":
        with open_db() as cur:
            cur.execute(f"""SELECT available_stock, title
                            FROM products
                            WHERE sku='{request.form["restock_item"]}'""")
            stock = cur.fetchone()
            if stock["available_stock"]==0:
                new_stock = stock["available_stock"] + 200
                cur.execute(f"""UPDATE products
                                SET available_stock={new_stock}
                                WHERE sku='{request.form["restock_item"]}'""")

                cur.execute(f"""SELECT email_id
                                FROM notifyAvailability, persons
                                WHERE sku='{request.form["restock_item"]}'
                                        AND notifyAvailability.person_id=persons.person_id""")
                remind_users=cur.fetchall()

                with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.ehlo()

                    smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                    for person in remind_users:
                        msg = EmailMessage()
                        msg["Subject"]="Product back in stock"
                        msg["From"]=EMAIL_ADDRESS
                        msg["To"]=person["email_id"]
                        msg.set_content(f"""
                                        <!DOCTYPE html>
                                        <html>
                                            <p>Thank you for your interest in our <strong>{ stock['title'] }</strong>.</p>
                                            <p>We are happy to inform you that the product you have been waiting for is now back in stock!</p>
                                        </html>
                                        """
                        , subtype='html')
                        smtp.send_message(msg)

                    flash(f"{ stock['title'] } has been restocked", "success")
            else:
                flash(f"{ stock['title'] } is already in stock", "danger")
    return redirect(request.referrer)

@app.route("/restock_all", methods=["POST"])
def restock_all():
    if request.method == "POST":
        with open_db() as cur:
            cur.execute(f"""SELECT email_id, title
                            FROM products, persons, notifyAvailability
                            WHERE persons.person_id = notifyAvailability.person_id
                                    AND products.sku = notifyAvailability.sku
                                    AND products.available_stock=0""")
            remind_users=cur.fetchall()
            cur.execute(f"""UPDATE products
                            SET available_stock=200
                            WHERE available_stock=0""")
            with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()

                smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                for person in remind_users:
                    msg = EmailMessage()
                    msg["Subject"]="Product back in stock"
                    msg["From"]=EMAIL_ADDRESS
                    msg["To"]=person["email_id"]
                    msg.set_content(f"""
                                    <!DOCTYPE html>
                                    <html>
                                        <p>Thank you for your interest in our <strong>{ person['title'] }</strong>.</p>
                                        <p>We are happy to inform you that the product you have been waiting for is now back in stock!</p>
                                    </html>
                                    """
                    , subtype='html')
                    smtp.send_message(msg)
        flash(
                f"All necessary products have been restocked", "success"
            )
    return redirect(request.referrer)



def create_fake_users():
    with open_db() as cur:
        for i in range (36):
            cur.execute(
                f"""INSERT INTO persons(first_name, last_name, email_id)
                            VALUES ('FN{i}','LN{i}', 'fakeEmail{i}@gmail.com' )"""
            )
            cur.execute(
                f"""SELECT person_id
                            FROM persons
                            WHERE first_name='FN{i}'
                                    AND last_name='LN{i}'
                                    AND email_id='fakeEmail{i}@gmail.com'"""
            )
            user = cur.fetchone()
            person_id = user["person_id"]
            salt = token_hex(16)
            password_hash = bcrypt.generate_password_hash(
                salt + "abcdefgh"
            ).decode("utf-8")
            cur.execute(
                f"""INSERT INTO credentials(username, person_iD, salt, password_hash)
                            VALUES ('FN{i}','{person_id}', '{salt}', '{password_hash}' )"""
            )
            flash(
                f"Account Created for FN{i} LN{i}!",
                "success",
            )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port="5000", debug=True)
