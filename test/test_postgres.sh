#!/bin/bash

# dependencies
sudo apt update
sudo apt install -y postgresql-17 restic

# start postgres
sudo systemctl start postgresql

# set password
sudo -u postgres psql -c "CREATE USER root WITH PASSWORD 'guest';"

# ingest data
sudo -u postgres createdb testdb 
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE testdb TO root;"
sudo -u postgres psql -U root -d testdb -f test/data/artists.sql

# number of expected entries in restored table
EXPECTED=$(sudo -u postgres psql -d testdb -c "SELECT COUNT(*) FROM artist;" -t -A)

echo "Expected: ${EXPECTED}"
