FROM mongo:4.4.15 AS mongo

FROM alpine:3.19

RUN \
    # install restic \
    apk add --update --no-cache tini restic bash restic-bash-completion curl && \
    # install python and tools \
    apk add --update --no-cache tzdata python3 py3-pip py3-requests py3-yaml gzip findutils && \
    pip3 install crontab --break-system-packages && \
    # install elasticdump \
    apk add --update --no-cache npm && \
    npm install -g elasticdump && \
    # install mysql client
    apk add --update --no-cache mariadb-client  && \
    # with modern authentication method
    apk add --update --no-cache mariadb-connector-c && \
    # install postgresql client
    apk add --update --no-cache postgresql-client && \
    # install mongodump \
    apk add --update --no-cache mongodb-tools && \
    # ensure glibc program compability for added mongodump_rc binary
    apk add --update --no-cache krb5-libs gcompat

WORKDIR /usr/bin/
COPY --from=mongo /usr/bin/mongodump ./mongodump_rc
RUN chown root:root /usr/bin/mongodump_rc

ENV BACKUP_ROOT=/backup

VOLUME /backup

ADD *.py /scripts/

ENTRYPOINT ["/sbin/tini","--"]
CMD /scripts/backup_client.py schedule @daily
