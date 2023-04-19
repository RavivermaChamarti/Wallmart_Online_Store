import contextlib
import os
from secrets import token_hex

import psycopg2
from flask import Flask, flash, redirect, render_template, session, url_for
from flask_bcrypt import Bcrypt
from psycopg2.extras import RealDictCursor

from forms import LoginForms, RegistrationForms

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ["WALLMART_SECRET_KEY"]
bcrypt = Bcrypt()

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
    return render_template("home.html", title="Home")

@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForms()
    if form.validate_on_submit():
        with open_db() as cur:
            cur.execute(f"""SELECT first_name, last_name, salt, password_hash, username
                            FROM persons, credentials
                            WHERE username='{form.username.data}'
                                    AND credentials.person_id=persons.person_id""")
            user = cur.fetchone()
            if user and bcrypt.check_password_hash(user['password_hash'], user['salt'] + form.password.data):
                session["user"] = user['username']
                flash(f"Welcome Back {user['first_name']} {user['last_name']}!", "success")
                return redirect(url_for('store'))
            else:
                flash(f"Login Unsuccessful! Use a valid Username and Password", "danger")
    return render_template("login.html", title="Login", form=form)


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForms()
    if form.validate_on_submit():
        with open_db() as cur:
            cur.execute(f"""INSERT INTO persons(first_name, last_name, email_id)
                            VALUES ('{form.first_name.data}','{form.last_name.data}', '{form.email_id.data}' )""")
            cur.execute(f"""SELECT person_id
                            FROM persons
                            WHERE first_name='{form.first_name.data}'
                                    AND last_name='{form.last_name.data}'
                                    AND email_id='{form.email_id.data}'""")
            user = cur.fetchone()
            person_id = user['person_id']
            salt = token_hex(16)
            password_hash = bcrypt.generate_password_hash(salt+form.password.data).decode("utf-8")
            cur.execute(f"""INSERT INTO credentials(username, person_iD, salt, password_hash)
                            VALUES ('{form.username.data}','{person_id}', '{salt}', '{password_hash}' )""")
            flash(f"Account Created for {form.first_name.data} {form.last_name.data}!", "success")
            return redirect(url_for('store'))
    return render_template("register.html", title="Register", form=form)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/store")
def store():
    if "user" in session:
        user = session["user"]
        with open_db() as cur:
            cur.execute("""SELECT SKU, title, url, brand, currency, price, description, primary_category, sub_category_1, sub_category_2
                        FROM products, categories
                        WHERE products.category_id = categories.category_id""")
            products = cur.fetchall()
        return render_template("store.html", title="Store", products=products, user=user)
    return render_template("invalidUser.html", title="Invalid User")

@app.route("/admin")
def admin():
    return render_template("admin.html", title="Admin")


@app.route("/profile")
def profile():
    return render_template("profile.html", title="Profile")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port='2000')
