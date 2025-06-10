from flask_bcrypt import Bcrypt 
from flask import Flask
import sqlite3
import bcrypt

conn = sqlite3.connect('database.sqlite3')
c = conn.cursor()
app = Flask(__name__)

c.execute("DROP TABLE IF EXISTS users")
c.execute("DROP TABLE IF EXISTS slot")
c.execute("DROP TRIGGER IF EXISTS updateAvls")

c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username varchar(255) NOT NULL,
    password TEXT NOT NULL,
    maxImp INTEGER,
    maxUnd INTEGER
    )
''')

c.execute('''
CREATE TABLE IF NOT EXISTS slot(
    id int,
    giorno varchar(255),
    ora_inizio varchar(255),
    ora_fine varchar(255),
    peso varchar(255),
    FOREIGN KEY (id) REFERENCES users (id),
    PRIMARY KEY (id, giorno, ora_inizio, ora_fine)
    )
''')

pwadmin = bcrypt.hashpw("admin".encode('utf-8'), bcrypt.gensalt())
pwusr = bcrypt.hashpw("prova".encode('utf-8'), bcrypt.gensalt())
c.execute("INSERT INTO users (id, username, password) VALUES (0, 'admin', ?)", (pwadmin,))

conn.commit()
conn.close()