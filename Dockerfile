FROM alpine:3.11

# mssql client install taken from https://github.com/dbamaster/mssql-tools-alpine/blob/master/Dockerfile

# MSSQL_VERSION can be changed, by passing `--build-arg MSSQL_VERSION=<new version>` during docker build
ARG MSSQL_VERSION=17.5.2.1-1
ENV MSSQL_VERSION=${MSSQL_VERSION}

WORKDIR /tmp 

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
RUN \    
    # install mssql client \
    apk add --no-cache curl gnupg --virtual .build-dependencies -- && \
    # Adding custom MS repository for mssql-tools and msodbcsql \
    curl -O https://download.microsoft.com/download/e/4/e/e4e67866-dffd-428c-aac7-8d28ddafb39b/msodbcsql17_${MSSQL_VERSION}_amd64.apk && \
    curl -O https://download.microsoft.com/download/e/4/e/e4e67866-dffd-428c-aac7-8d28ddafb39b/mssql-tools_${MSSQL_VERSION}_amd64.apk && \
    # Verifying signature \
    curl -O https://download.microsoft.com/download/e/4/e/e4e67866-dffd-428c-aac7-8d28ddafb39b/msodbcsql17_${MSSQL_VERSION}_amd64.sig && \
    curl -O https://download.microsoft.com/download/e/4/e/e4e67866-dffd-428c-aac7-8d28ddafb39b/mssql-tools_${MSSQL_VERSION}_amd64.sig && \
    # Importing gpg key \
    curl https://packages.microsoft.com/keys/microsoft.asc  | gpg --import - && \
    gpg --verify msodbcsql17_${MSSQL_VERSION}_amd64.sig msodbcsql17_${MSSQL_VERSION}_amd64.apk && \
    gpg --verify mssql-tools_${MSSQL_VERSION}_amd64.sig mssql-tools_${MSSQL_VERSION}_amd64.apk && \
    # Installing packages \
    echo y | apk add --allow-untrusted msodbcsql17_${MSSQL_VERSION}_amd64.apk mssql-tools_${MSSQL_VERSION}_amd64.apk && \
#     # Deleting packages \
    apk del .build-dependencies && rm -f msodbcsql*.sig mssql-tools*.apk

# Adding SQL Server tools to $PATH
ENV PATH=$PATH:/opt/mssql-tools/bin

ENV BACKUP_ROOT=/backup

VOLUME /backup

ADD *.py /scripts/
# CMD ["/bin/sh"]
CMD /scripts/backup_client.py schedule @daily
