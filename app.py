#! /usr/bin/env python3

import os

from flask import Flask, request, redirect

import database

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

db = database.Database('/data/data.db')

@app.route('/signup', methods=['POST'])
def signup():
    db.signup_create(request.form.to_dict())
    return redirect(request.form.get('next'))

if __name__ == '__main__':
    app.run(host='0.0.0.0')
