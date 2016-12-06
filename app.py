#! /usr/bin/env python3

import os
import datetime
import json
import hmac
import base64

from flask import Flask, request, redirect, g, render_template, jsonify
from peewee import SqliteDatabase, Model, CharField, TextField, DateTimeField
from playhouse.shortcuts import model_to_dict
import requests
from itsdangerous import Serializer, URLSafeSerializer
from cryptography.fernet import Fernet, InvalidToken

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['APP_URL'] = os.environ.get('APP_URL')
app.config['MAILGUN_API_KEY'] = os.environ.get('MAILGUN_API_KEY')
app.config['MAILGUN_DOMAIN'] = os.environ.get('MAILGUN_DOMAIN')
app.config['FERNET_KEY'] = os.environ.get('FERNET_KEY')
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

def create_email_token(email, user_secret_key, app_secret_key, fernet_key):
    return URLSafeSerializer(app_secret_key).dumps(
        {
            'email': Serializer(user_secret_key).dumps(email),
            'secret_key': Fernet(fernet_key).encrypt(user_secret_key.encode()).decode()
        }
    )

def verify_email_token(email_token, app_secret_key, fernet_key):
    try:
        obj = URLSafeSerializer(app_secret_key).loads(email_token)
    except BadSignature:
        return None
    try:
        user_secret_key = Fernet(fernet_key).decrypt(obj['secret_key'].encode())
    except InvalidToken:
        return None
    try:
        return Serializer(user_secret_key).loads(obj['email'])
    except BadSignature:
        return None


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
        user_secret_key = user_secret_key.decode(),
        user_form_key = user_form_key.decode()
        )

@app.route('/get-key')
def get_key():
    user_secret_key = base64.urlsafe_b64encode(os.urandom(24))
    user_form_key = generate_form_key(user_secret_key)
    return jsonify(
        secret_key = user_secret_key.decode(),
        form_key = user_form_key.decode()
    ), {'Access-Control-Allow-Origin': '*'}

@app.route('/get-data', methods=['GET', 'POST'])
def get_form_data():
    if request.method == 'POST':
        if request.is_json:
            user_secret_key = request.get_json().get('secret_key').encode()
        else:
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
        ), {'Access-Control-Allow-Origin': '*'}
    else:
        return render_template('get_data_form.html')

@app.route('/email-token', methods=['POST'])
def email_token():
    if request.is_json:
        email = request.get_json().get('email')
        user_secret_key = request.get_json().get('secret_key')
    else:
        email = request.form.get('email')
        user_secret_key = request.form.get('secret_key')
    email_token = create_email_token(
        email,
        user_secret_key,
        app.config['SECRET_KEY'],
        app.config['FERNET_KEY']
    )
    return jsonify({'email_token': email_token})

@app.route('/test-email-token', methods=['POST'])
def test_email_token():
    if request.is_json:
        email_token = request.get_json().get('email_token')
    else:
        email_token = request.form.get('email_token')
    email = verify_email_token(
        email_token,
        app.config['SECRET_KEY'],
        app.config['FERNET_KEY'],
    )
    return jsonify({'email': email})

@app.route('/submit/<form_key>', methods=['POST'])
def signup(form_key):
    res_type = 'redirect'
    if 'res_type' in request.args:
        if request.args['res_type'] in ('redirect', 'json'):
            res_type = request.args['res_type']
    signup = Signup.create(
        form_key = form_key,
        form_data = json.dumps(request.form.to_dict()),
        time = datetime.datetime.utcnow()
        )
    if res_type == 'redirect':
        return redirect(
            request.args.get('next', request.referrer or 'https://www.google.com')
        )
    elif res_type == 'json':
        return jsonify(
            json.loads(model_to_dict(signup)['form_data'])
        ), {'Access-Control-Allow-Origin': '*'}

if __name__ == '__main__':
    app.run(host='0.0.0.0')
