# Using backup script without Docker

Real old systems sometimes needs backup but can´t install docker anymore.

## Debian GNU/Linux 8.1

check python3 
```
$ check python3 --version
Python 3.4.2
```

install modules for python
```
$ apt-get install -y python3-pip  python3-yaml python3-requests
```
add -o Acquire::Check-Valid-Until=false; to command if your system is too old. update it at next oppertunity

```
pip3 install crontab
```

alternative if you get errors, find out real name for pip3 an if you get URL errrors, give a hint to use ssl for that
```
pip-3.2 install --index-url=https://pypi.python.org/simple/ crontab
```


If you run backup_client.py now some help information should be shown.

## Shell-Script for running

Write a simple script for starting restic backup
```
#!/bin/bash

export RESTIC_REPOSITORY="s3:https://yourVendor/yourBucket"
export RESTIC_PASSWORD="se3ret"
export BACKUP_HOSTNAME="my-hostname-tld"
export AWS_ACCESS_KEY_ID="accessKey"
export AWS_SECRET_ACCESS_KEY="se3ret"
export BACKUP_CONFIG="backup.conf"

export BACKUP_ROOT="/whateverYouBackup"

./backup_client.py run
```
