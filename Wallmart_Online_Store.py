from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html", title="home")

@app.route("/login")
def login():
    return render_template("login.html", title="login")


@app.route("/register")
def sign_up():
    return render_template("register.html", title="register")


@app.route("/logout")
def logout():
    return render_template("invalidUser.html", title="logout")


@app.route("/store")
def news():
    return render_template("store.html", title="store")


@app.route("/admin")
def admin():
    return render_template("admin.html", title="admin")


@app.route("/profile")
def profile():
    return render_template("profile.html", title="profile")


if __name__ == "__main__":
    app.run(host='0.0.0.0')
