CREATE USER akvo WITH PASSWORD 'password';

CREATE DATABASE eswatini
WITH OWNER = akvo
     template = template0
     ENCODING = 'UTF-8'
     LC_COLLATE = 'en_US.UTF-8'
     LC_CTYPE = 'en_US.UTF-8';

\c eswatini

CREATE EXTENSION IF NOT EXISTS ltree WITH SCHEMA public;
