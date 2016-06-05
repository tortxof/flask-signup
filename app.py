#! /usr/bin/env python3

import os
import datetime
import json
import hmac
import base64

from flask import Flask, request, redirect, g, render_template, jsonify
from peewee import SqliteDatabase, Model, CharField, TextField, DateTimeField

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

app.config['APP_URL'] = os.environ.get('APP_URL')

app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

db = SqliteDatabase('/data/data.db')

class BaseModel(Model):
    class Meta():
        database = db

class Signup(BaseModel):
    form_key = CharField(index=True)
    form_data = TextField()
    time = DateTimeField()

db.connect()
db.create_tables([Signup], safe=True)
db.close()

def generate_form_key(user_secret_key):
    """Generate user's public form key from their secret key."""
    user_form_key = hmac.new(
        app.config['SECRET_KEY'].encode(),
        msg=user_secret_key,
        digestmod='sha256'
        ).digest()
    return base64.urlsafe_b64encode(user_form_key[:24])

@app.before_request
def before_request():
    g.db = db
    g.db.connect()

@app.after_request
def after_request(request):
    g.db.close()
    return request

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/new-key')
def new_key():
    user_secret_key = base64.urlsafe_b64encode(os.urandom(24))
    user_form_key = generate_form_key(user_secret_key)
    return render_template(
        'new_key.html',
        user_secret_key=user_secret_key.decode(),
        user_form_key=user_form_key.decode()
        )

@app.route('/get-data', methods=['GET', 'POST'])
def get_form_data():
    if request.method == 'POST':
        user_secret_key = request.form.get('secret_key').encode()
        user_form_key = generate_form_key(user_secret_key)
        signups = (
            Signup.select()
            .where(Signup.form_key == user_form_key.decode())
        )
        return jsonify(
            records = [
                {
                    **json.loads(record.form_data),
                    **{'time': record.time.isoformat()}
                }
                for record in signups
            ]
        )
    else:
        return render_template('get_data_form.html')

@app.route('/submit/<form_key>', methods=['POST'])
def signup(form_key):
    Signup.create(
        form_key = form_key,
        form_data = json.dumps(
            {k:v for k,v in request.form.to_dict().items() if k != 'next'}
            ),
        time = datetime.datetime.utcnow()
        )
    return redirect(
        request.form.get('next', request.referrer or 'https://www.google.com')
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0')
