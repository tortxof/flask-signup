#! /usr/bin/env python3

import os
import datetime
import json

from flask import Flask, request, redirect, g
from peewee import SqliteDatabase, Model, CharField, TextField, DateTimeField

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

db = SqliteDatabase('/data/data.db')

class BaseModel(Model):
    class Meta():
        database = db

class Signup(BaseModel):
    form_name = CharField(index=True)
    form_data = TextField()
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

@app.route('/signup/<form_name>', methods=['POST'])
def signup(form_name=''):
    Signup.create(
        form_name = form_name,
        form_data = json.dumps(request.form.to_dict()),
        time = datetime.datetime.now()
        )
    return redirect(request.form.get('next', 'https://www.google.com/'))

if __name__ == '__main__':
    app.run(host='0.0.0.0')
