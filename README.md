# Easy backups with docker and restic

## Features

* Auto-initialization of restic repositories
* config via env vars (basic config) and a simple yaml file (advanced config)
* schedule backups to restic once or periodically
* delete old backups
* run pre-backup scripts, optionally fail on errors
* dump elasticsearch prior to run a backup (with option to include/exclude indices via regular expressions)
* dump mysql prior to run a backup (with option to include/exclude databases via regular expressions)
* dump postgresql prior to run a backup (with option to include/exclude databases via regular expressions)
* dump mongodb prior to run a backup
* dump influxdb prior to run a backup
* Excluding caches from being backed up. See http://bford.info/cachedir/spec.html on how to mark a cache dir
* support restic cache-dir in advanced config

## Volumes

* /etc/localtime from host should be mounted readonly to get the correct time zone
* /backup is an anonymous volume
* /restic-cache is writeable directory for cache if this config is set
* if you want to backup other files, just mount the volumes to /backup/something
* Elasticdump will write to /backup/elasticdump. This folder is deleted and re-created before each backup run
* Mysqldump will write to /backup/mysqldump. This folder is deleted and re-created before each backup run
* Pgdump will write to /backup/pgdump. This folder is deleted and re-created before each backup run
* Mongodump will write to /backup/mongodump. This folder is deleted and re-created before each backup run
* Influxdump will write to /backup/influxdump. This folder is deleted and re-created before each backup run

## Command and Arguments

* The default command is "/scripts/backup_client.py schedule @daily" which performs a backup every day at 00:00
* Possible args are
  * `run` - runs a backup immediatelly, rotate and prune afterwards
  * `rotate` - rotate a backup immediatelly
  * `prune` - prune the repository immediatelly
  * `schedule` - runs periodic backups. One or more cron expressions are required as further arguments (see https://pypi.org/project/crontab/)
    * `--prune` - An optional cron expressions for pruning the repo. If set, pruning is scheduled separately and not ather the backup.
      If a backup is running when the prune is scheduled, prune will be skipped and vice

### Scheduling example 

```
/scripts/backup_client.py schedule --prune '0 23 00 * * SUN' '@daily'
```

This would schedule a backup every day at 00:00. On end of Sunday, a prune would be scheduled (if the previous backup is not runing anymore). If the
prune takes more than 1 hour, the backup at Monday would be skipped.


## Env vars

* RESTIC_REPOSITORY (required): repository to backup to
* RESTIC_PASSWORD (required): password to encrypt the backups
* RESTIC_PRUNE_TIMEOUT (optional): Timeout for the "prune" command, e.g. 1d2h3m4s or 24h
* BACKUP_HOSTNAME (required): A hostname to use for backups
* BACKUP_CONFIG (optional): path to a yaml file containing advanced backup options
* restic specific env vars (optional): e.g. AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
* Keep options (only have affect if there is no "keep" section in config: KEEP_LAST, KEEP_DAILY, ...

### Env var substitution

Env vars may contain placeholders like `$(OTHER_ENV_VAR)` which will be resolved recusively up to 10 levels. If resolution is not possible, the placeholder would be kept.

## Yaml configuration examples

```
---

# if set, old backups will be deleted according to the rules below.
# At least one of [last, daily, weekly, monthly, yearly] needs to be set to make this work
keep:
  last: 1
  daily: 7
  weekly: 4
  monthly: 3
  yearly: 1

# Caches are excluded by default. See http://bford.info/cachedir/spec.html on hot to mark a cache dir
exclude-caches: false

# Exclude some files from backup. See https://restic.readthedocs.io/en/latest/040_backup.html#including-and-excluding-files for details
exclude:
  - *.bak
  - .cache/*

# Include files 
# a file contains paths (with patterns) which to backup for
# if use include-from define ALL backup paths inside file. Also backup paths from database dumps!
include-from: 
  - /tmp/backupset.txt

# define restic cache-dir
# dir has to match with container environment if used
# cache-dir: /restic-cache

# Run some script(s) before backup
pre-backup-scripts:
  - description: Doing some pre-backup stuff
    script: |
      echo "x"
      exit 1
    fail-on-error: true

# File changed are by default done by mtime and size, inode changes are ignored.
# set ignore-inode to false to thread files as changed if the inode is changed
ignore-inode: false

# Perform a dump of elasticsearch
# * url is required
# * username and password for basic auth are optional
# * either include or exclude can be set to a list of regular expressions to include/exclude indices
elasticdump:
  url: https://es.local:9200/
  username: esuser
  password: s3cr3t
  exclude:
    - ^.kibana

# Perform a dump of mysql
# * host is required
# * port defaults to 3306
# * username and password are required
# * either include or exclude can be set to a list of regular expressions to include/exclude databases
mysqldump:
  host: database.local
  username: root
  password: s3cr3t
  exclude:
    - ^test
  mysqldump-extra-args:
    - --skip-lock-tables
    - --single-transaction

# Perform a dump of postgresql
# * host is required
# * port defaults to 5432
# * username and password are required
# * either include or exclude can be set to a list of regular expressions to include/exclude databases
pgdump:
  host: database.local
  username: root
  password: s3cr3t
  exclude:
    - ^test

# Perform a dump of mongodb
# * host is required
# * port defaults to 27017
# * username and password are required
# * dump_version defaults to 3. Choose between mongodump version 3.x.x and 4.x.x. Implemented to avoid failing dumps due to version mismatch.
mongodump:
  host: mongodb.local
  username: root
  password: s3cr3t
  dump_version: 4

# Perform a dump of influxdb
# * host is required
# * port defaults to 8088
# * database is optional, without all databases are dumped
influxdump:
  host: influxdb.local

```

