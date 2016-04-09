#! /usr/bin/env python3

import os
import datetime

from flask import Flask, request, redirect, g
from peewee import *

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

db = SqliteDatabase('/data/data.db')

class BaseModel(Model):
    class Meta():
        database = db

class Signup(BaseModel):
    name = CharField()
    email = CharField()
    time = DateTimeField()

db.connect()
db.create_tables([Signup], safe=True)
db.close()

@app.before_request
def before_request():
    g.db = db
    g.db.connect()

@app.after_request
def after_request(request):
    g.db.close()
    return request

@app.route('/signup', methods=['POST'])
def signup():
    Signup.create(
        name = request.form.get('name', ''),
        email = request.form.get('email', ''),
        time = datetime.datetime.now()
        )
    return redirect(request.form.get('next'))

if __name__ == '__main__':
    app.run(host='0.0.0.0')
