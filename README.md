# Easy backups with docker and restic

## Features

* Auto-initialization of restic repositories
* config via env vars (basic config) and a simple yaml file (advanced config)
* schedule backups to restic once or periodically
* delete old backups
* run pre-backup scripts, optionally fail on errors
* dump elasticsearch prior to run a backup (with option to include/exclude indices via regular expressions)
* dump mysql prior to run a backup (with option to include/exclude databases via regular expressions)
* dump mongodb prior to run a backup
* Excluding caches from being backed up. See http://bford.info/cachedir/spec.html on how to mark a cache dir

## Volumes

* /etc/localtime from host should be mounted readonly to get the correct time zone
* /backup is an anonymous volume
* if you want to backup other files, just mount the volumes to /backup/something
* Elasticdump will write to /backup/elasticdump. This folder is deleted and re-created before each backup run
* Mysqldump will write to /backup/mysqldump. This folder is deleted and re-created before each backup run
* Mongodump will write to /backup/mongodump. This folder is deleted and re-created before each backup run

## Command and Arguments

* The default command is "/scripts/backup_client.py schedule @daily" which performs a backup every day at 00:00
* Possible args are
  * run - runs a backup immediatelly
  * schedule - runs periodic backups. One or more cron expressions are required as further arguments

## Env vars

* RESTIC_REPOSITORY (required): repository to backup to
* RESTIC_PASSWORD (required): password to encrypt the backups
* BACKUP_HOSTNAME (required): A hostname to use for backups
* BACKUP_CONFIG (optional): path to a yaml file containing advanced backup options
* restic specific env vars (optional): e.g. AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY

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

# Run some script(s) before backup
pre-backup-scripts:
  - description: Doing some pre-backup stuff
    script: |
      echo "x"
      exit 1
    fail-on-error: true


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

# Perform a dump of mongodb
# * host is required
# * port defaults to 27017
# * username and password are required
mongodump:
  host: mongodb.local
  username: root
  password: s3cr3t

```

