DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS photo;

CREATE TABLE users (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  first_name           TEXT NOT NULL,
  last_name            TEXT NOT NULL,
  email                TEXT NOT NULL,
  dob                  TEXT NOT NULL,
  institution          TEXT NOT NULL,
  address              TEXT,
  arrival_time         TEXT,
  departure_time       TEXT,

  is_talk              INTEGER,
  talk_title           TEXT,
  talk_url             TEXT,

  is_visa              INTEGER,
  visa_fullname        TEXT,
  visa_citizenship     TEXT,
  visa_gender          TEXT,
  visa_passport_id     TEXT,
  visa_dob             TEXT,

  visa_relation        TEXT,
  visa_dep_fullname    TEXT,
  visa_dep_citizenship TEXT,
  visa_dep_gender      TEXT,
  visa_dep_passport_id TEXT,
  visa_dep_dob         TEXT,

  submit_time          TEXT NOT NULL,
  password_hash             NOT NULL
);
CREATE TABLE photo (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  url         TEXT NOT NULL,
  caption     TEXT,
  update_time TEXT NOT NULL,
  'order'     INTEGER
);