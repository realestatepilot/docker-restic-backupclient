FROM alpine:3.8

RUN \
    # install restic \
    wget -O- https://github.com/restic/restic/releases/download/v0.9.4/restic_0.9.4_linux_amd64.bz2 | bzip2 -d > /usr/local/bin/restic && \
    chmod 0755 /usr/local/bin/restic && \
    # install python \
    apk add --update --no-cache python3 py3-pip py3-requests py3-yaml && \
    pip3 install crontab && \
    # install elasticdump \
    apk add --update --no-cache npm && \
    npm install -g elasticdump

ENV BACKUP_ROOT=/backup

ADD *.py /scripts/

CMD /scripts/backup_client.py schedule @daily
