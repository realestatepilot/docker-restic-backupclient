FROM alpine:3.13

RUN \
    # install restic \
    apk add --update --no-cache restic bash restic-bash-completion && \
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

VOLUME /backup

ADD *.py /scripts/

CMD /scripts/backup_client.py schedule @daily
