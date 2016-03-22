#! /usr/bin/env python3

import sqlite3
import time

class Database(object):
    def __init__(self, dbfile):
        self.dbfile = dbfile
        conn = self.db_conn()
        conn.execute(
            'create table if not exists signups '
            '(name, email, time)'
            )
        conn.commit()
        conn.close()

    def db_conn(self):
        conn = sqlite3.connect(self.dbfile)
        conn.row_factory = sqlite3.Row
        return conn

    def signup_create(self, signup):
        signup['time'] = time.time()
        conn = sqlite3.connect(self.dbfile)
        conn.execute('insert into signups values (:name, :email, :time)', signup)
        conn.commit()
        conn.close
