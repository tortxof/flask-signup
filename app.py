import os
import time
from datetime import datetime
import json
import hmac
import base64
import secrets

from flask import (
    Flask, request, redirect, url_for, g, render_template, jsonify
)
import boto3
import requests
from itsdangerous import Serializer, URLSafeSerializer, BadSignature
from cryptography.fernet import Fernet, InvalidToken

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['APP_URL'] = os.environ.get('APP_URL')
app.config['MAILGUN_API_KEY'] = os.environ.get('MAILGUN_API_KEY')
app.config['MAILGUN_DOMAIN'] = os.environ.get('MAILGUN_DOMAIN')
app.config['FERNET_KEY'] = os.environ.get('FERNET_KEY')
app.config['DDB_TABLE_NAME'] = os.environ.get('DDB_TABLE_NAME')

def create_record(record):
    client = boto3.client('dynamodb')
    record_id = secrets.token_urlsafe(12)
    client.put_item(
        TableName = app.config['DDB_TABLE_NAME'],
        Item = {
            'id': {
                'S': record_id
            },
            'form_key': {
                'S': record['form_key']
            },
            'date': {
                'N': str(record['date'])
            },
            'form_data': {
                'S': record['form_data']
            },
        },
    )
    return get_record(record_id)

def get_record(record_id):
    client = boto3.client('dynamodb')
    return client.get_item(
        TableName = app.config['DDB_TABLE_NAME'],
        Key = {
            'id': {'S': record_id},
        },
        ConsistentRead = True,
    )


def query_records(form_key):
    client = boto3.client('dynamodb', region_name='us-east-1')
    return client.query(
        TableName = app.config['DDB_TABLE_NAME'],
        IndexName = 'form_key-date-index',
        ExpressionAttributeValues = {
            ':form_key': {'S': form_key}
        },
        KeyConditionExpression = 'form_key = :form_key',
    )


def generate_secret_key():
    """Generate a random secret key."""
    return base64.urlsafe_b64encode(os.urandom(24)).decode()

def generate_form_key(user_secret_key):
    """Generate user's public form key from their secret key."""
    user_form_key = hmac.new(
        app.config['SECRET_KEY'].encode(),
        msg=user_secret_key.encode(),
        digestmod='sha256'
        ).digest()
    return base64.urlsafe_b64encode(user_form_key[:24]).decode()

def create_email_token(email, user_secret_key, fernet_key):
    return Fernet(fernet_key).encrypt(json.dumps(
        {
            'email': email,
            'form_key': generate_form_key(user_secret_key)
        }
    ).encode()).decode()

def verify_email_token(email_token, fernet_key):
    try:
        return json.loads(
            Fernet(fernet_key).decrypt(email_token.encode()).decode()
        )
    except InvalidToken:
        return None

def send_email_token(email_address, email_token):
    requests.post(
        (
            'https://api.mailgun.net/v3/{domain}/messages'
            .format(domain=app.config['MAILGUN_DOMAIN'])
        ),
        auth = ('api', app.config['MAILGUN_API_KEY']),
        data = {
            'from': (
                '{app_url} <signup@{mailgun_domain}>'
                .format(
                    app_url=app.config['APP_URL'],
                    mailgun_domain=app.config['MAILGUN_DOMAIN'],
                )
            ),
            'to': email_address,
            'subject': 'Email Token',
            'text': 'Email Token:\n\n' + email_token,
            'html': render_template(
                'email_token.html',
                title='Email Token',
                email_token=email_token,
            )
        },
    )

def send_form_email(email_address, form_key, form_data, date):
    requests.post(
        (
            'https://api.mailgun.net/v3/{domain}/messages'
            .format(domain=app.config['MAILGUN_DOMAIN'])
        ),
        auth = ('api', app.config['MAILGUN_API_KEY']),
        data = {
            'from': (
                '{app_url} <signup@{mailgun_domain}>'
                .format(
                    app_url=app.config['APP_URL'],
                    mailgun_domain=app.config['MAILGUN_DOMAIN'],
                )
            ),
            'to': email_address,
            'subject': 'New Form Submission',
            'text': form_data_to_text(form_data),
        },
    )

def form_data_to_text(form_data):
    return ''.join(
        k + ':\n' + v + '\n\n' for k, v in form_data.items()
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/new-key')
def new_key():
    user_secret_key = generate_secret_key()
    user_form_key = generate_form_key(user_secret_key)
    return render_template(
        'new_key.html',
        user_secret_key = user_secret_key,
        user_form_key = user_form_key
        )

@app.route('/get-key')
def get_key():
    user_secret_key = generate_secret_key()
    user_form_key = generate_form_key(user_secret_key)
    return jsonify(
        secret_key = user_secret_key,
        form_key = user_form_key
    ), {'Access-Control-Allow-Origin': '*'}

@app.route('/get-data', methods=['GET', 'POST'])
def get_form_data():
    if request.method == 'POST':
        if request.is_json:
            user_secret_key = request.get_json().get('secret_key')
        else:
            user_secret_key = request.form.get('secret_key')
        user_form_key = generate_form_key(user_secret_key)
        signups = query_records(user_form_key)
        return jsonify(
            records = [
                {
                    'form_data': json.loads(record['form_data']['S']),
                    'date': datetime.utcfromtimestamp(float(record['date']['N'])).isoformat(),
                }
                for record in signups['Items']
            ]
        ), {'Access-Control-Allow-Origin': '*'}
    else:
        return render_template('get_data_form.html')

@app.route('/email-token', methods=['GET', 'POST'])
def email_token():
    if request.method == 'POST':
        if request.is_json:
            email = request.get_json().get('email')
            user_secret_key = request.get_json().get('secret_key')
        else:
            email = request.form.get('email')
            user_secret_key = request.form.get('secret_key')
        email_token = create_email_token(
            email,
            user_secret_key,
            app.config['FERNET_KEY']
        )
        send_email_token(email, email_token)
        return redirect(url_for('index'))
    else:
        return render_template('get_email_token.html')

@app.route('/test-email-token', methods=['POST'])
def test_email_token():
    if request.is_json:
        email_token = request.get_json().get('email_token')
    else:
        email_token = request.form.get('email_token')
    email = verify_email_token(
        email_token,
        app.config['FERNET_KEY'],
    )
    return jsonify({'email': email})

@app.route('/submit/<form_key>', methods=['POST'])
def signup(form_key):
    res_type = 'redirect'
    if 'res_type' in request.args:
        if request.args['res_type'] in ('redirect', 'json'):
            res_type = request.args['res_type']
    if 'email' in request.args:
        verified_email_token = verify_email_token(
            request.args['email'],
            app.config['FERNET_KEY'],
        )
    else:
        verified_email_token = False
    signup = create_record({
        'form_key': form_key,
        'form_data': json.dumps(request.form.to_dict()),
        'date': time.time(),
    })
    if verified_email_token and verified_email_token['form_key'] == form_key:
        send_form_email(
            email_address = verified_email_token['email'],
            form_key = verified_email_token['form_key'],
            form_data = json.loads(signup['Item']['form_data']['S']),
            date = signup['Item']['date']['N'],
        )
    if res_type == 'redirect':
        return redirect(
            request.args.get(
                'next',
                request.referrer or 'https://www.google.com'
            )
        )
    elif res_type == 'json':
        return jsonify(
            json.loads(signup['Item']['form_data']['S'])
        ), {'Access-Control-Allow-Origin': '*'}

if __name__ == '__main__':
    app.run(host='0.0.0.0')
