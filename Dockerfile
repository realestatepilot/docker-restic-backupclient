FROM alpine:3.9

RUN \
    # install restic \
    wget -O- https://github.com/restic/restic/releases/download/v0.9.5/restic_0.9.5_linux_amd64.bz2 | bzip2 -d > /usr/local/bin/restic && \
    chmod 0755 /usr/local/bin/restic && \
    # install python \
    apk add --update --no-cache tzdata python3 py3-pip py3-requests py3-yaml && \
    pip3 install crontab && \
    # install elasticdump \
    apk add --update --no-cache npm && \
    npm install -g elasticdump && \
	apk add --update --no-cache mariadb-client gzip && \
    # install mongodump \
    apk add --update --no-cache mongodb-tools && \
    apk add --update --no-cache findutils

ENV BACKUP_ROOT=/backup

ADD *.py /scripts/

CMD /scripts/backup_client.py schedule @daily
