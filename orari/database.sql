-- create_database.sql

-- Creazione della tabella 'users'
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    maxUndesired INTEGER DEFAULT 10,
    maxImpossible INTEGER DEFAULT 10
);

-- Inserimento dell'utente amministratore
INSERT INTO users (id, username, password, maxUndesired, maxImpossible) VALUES (0, 'amministratore', 'amministratore', 0, 0);

-- Creazione della tabella 'orari'
CREATE TABLE IF NOT EXISTS orari (
    prof_id INTEGER,
    week_day TEXT,
    hour_begin TEXT,
    hour_end TEXT,
    level TEXT,
    note TEXT
);