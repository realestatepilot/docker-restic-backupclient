#!/bin/bash

# dependencies
sudo apt update
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg
sudo apt update
sudo apt install -y postgresql-17 restic

# start postgres
sudo systemctl start postgresql

# set password
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'guest';"

# ingest data
sudo -u postgres createdb testdb 
sudo -u postgres psql -d testdb -f test/data/artists-postgres.sql

# number of expected entries in restored table
EXPECTED=$(sudo -u postgres psql -d testdb -c "SELECT COUNT(*) FROM artist;" -t -A)

if [ -z "${EXPECTED}" ]; then
    echo "Failed to retrieve expected number."
    exit 1
fi

# restic setup
rm -rf backup
mkdir backup
export RESTIC_REPOSITORY=restic_repo
export RESTIC_PASSWORD=guest
export RESTIC_PRUNE_TIMEOUT=12h
export BACKUP_HOSTNAME=restic_host
export BACKUP_ROOT=backup
export BACKUP_CONFIG=test/postgres_config.yaml

# restic dependencies
pip3 install crontab
pip3 install pyyaml

python3 backup_client.py run

echo "Expected number of entries: ${EXPECTED}"

# get created snapshot
SNAPSHOT=$(restic snapshots --latest 1 -q | awk 'NR == 3 { print $1 }')

# restic reads password from file
echo "guest" > restic_password
rm -rf restore
restic restore ${SNAPSHOT} -p "restic_password" --target restore

# extract restore
gunzip -c restore/backup/pgdump/PGSQL_testdb.sql.gz > testdb.sql

# re-ingest data
sudo -u postgres psql -d testdb -c "DROP TABLE artist;"
sudo -u postgres psql -d testdb -f testdb.sql

# test consistency
ACTUAL=$(sudo -u postgres psql -d testdb -c "SELECT COUNT(*) FROM artist;" -t -A)

if [ "${EXPECTED}" != "${ACTUAL}" ]; then
    echo "Initial Rows != Restored Rows: ${EXPECTED} != ${ACTUAL}"
    echo "Test failed."
    exit 1
fi

echo "Initial Rows == Restored Rows: ${EXPECTED} == ${ACTUAL}"
echo "Test succeeded."

exit 0
