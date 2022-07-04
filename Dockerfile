FROM alpine:3.14

RUN \
    # install restic \
    apk add --update --no-cache restic bash restic-bash-completion curl && \
    # install python and tools \
    apk add --update --no-cache tzdata python3 py3-pip py3-requests py3-yaml gzip findutils && \
    pip3 install crontab && \
    # install elasticdump \
    apk add --update --no-cache npm && \
    npm install -g elasticdump && \
    # install mysql client
    apk add --update --no-cache mariadb-client  && \
    # install postgresql client
    apk add --update --no-cache postgresql-client && \
    # install mongodump \
    apk add --update --no-cache mongodb-tools && \
    # install influxdb \
    apk add --update --no-cache influxdb && \

COPY mongodump_rc /usr/bin/mongodump_rc

ENV BACKUP_ROOT=/backup

VOLUME /backup

ADD *.py /scripts/

CMD /scripts/backup_client.py schedule @daily
