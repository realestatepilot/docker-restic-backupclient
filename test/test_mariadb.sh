#!/bin/bash

export MARIADB_USER=root
export MARIADB_PASSWORD=guest

# dependencies
sudo apt-get update
sudo apt-get install -y mariadb-server restic

# start mariadb
sudo systemctl start mariadb.service

# set password
sudo mysql -e "SET PASSWORD FOR 'root'@'localhost' = PASSWORD('guest');"
sudo mysql -e "FLUSH PRIVILEGES;"

# ingest data
mysql -u root -pguest -e "CREATE DATABASE IF NOT EXISTS testdb;"
mysql -u root -pguest testdb < test/data/artists.sql

# number of expected entries in restored table
EXPECTED=$(mysql -u root -pguest -e "SELECT COUNT(*) FROM testdb.artist;" -s -N)

# restic setup
mkdir backup
export RESTIC_REPOSITORY=restic_repo
export RESTIC_PASSWORD=guest
export RESTIC_PRUNE_TIMEOUT=12h
export BACKUP_HOSTNAME=restic_host
export BACKUP_ROOT=backup
export BACKUP_CONFIG=test/mariadb_config.yaml

# restic dependencies
pip3 install crontab
pip3 install pyyaml

python3 backup_client.py run

echo "Expected number of entries: ${EXPECTED}"

# get created snapshot
SNAPSHOT=$(restic list snapshots)

# restic reads password from file
echo "guest" > restic_password
restic restore ${SNAPSHOT} -p "restic_password" --target restore

# extract restore
gunzip -c restore/backup/mysqldump/MYSQL_testdb_DATA.sql.gz > testdb.sql

# re-ingest data
mysql -u root -pguest -e "DROP TABLE testdb.artist;"
mysql -u root -pguest testdb < testdb.sql

# test consistency
ACTUAL=$(mysql -u root -pguest -e "SELECT COUNT(*) FROM testdb.artist;" -s -N)

if [ $EXPECTED != $ACTUAL ]; then
    echo "Initial Rows != Restored Rows: ${EXPECTED} != ${ACTUAL}"
    echo "Test failed."
    exit 1
fi

echo "Initial Rows == Restored Rows: ${EXPECTED} == ${ACTUAL}"
echo "Test succeeded."

exit 0
