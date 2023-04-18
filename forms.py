import os

import psycopg2
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from psycopg2.extras import RealDictCursor
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError


class RegistrationForms(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email_id = StringField('Email Id', validators= [DataRequired(), Email()])
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=10)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign up')

    def validate_username(self, username):
        conn = psycopg2.connect(
        host="localhost",
        database="wallmart_store_db",
        user=os.environ["DB_USERNAME"],
        password=os.environ["DB_PASSWORD"]
        )
        # Open a cursor to perform database operations
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Check if username exists in database
        cur.execute(f"""SELECT username
                        FROM credentials
                        WHERE username='{username.data}'""")
        duplicate_username = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if duplicate_username:
            raise ValidationError('That username is taken. Please choose another one')

    def validate_email_id(self, email_id):
        conn = psycopg2.connect(
        host="localhost",
        database="wallmart_store_db",
        user=os.environ["DB_USERNAME"],
        password=os.environ["DB_PASSWORD"]
        )
        # Open a cursor to perform database operations
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Check if email id exists in database
        cur.execute(f"""SELECT email_id
                        FROM persons
                        WHERE email_id='{email_id.data}'""")
        duplicate_email_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if duplicate_email_id:
            raise ValidationError(f"There is an accounted linked to {email_id.data}! Please Log in if you already have an account")

class LoginForms(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=10)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Login')
