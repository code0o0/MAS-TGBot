FROM ubuntu:20.04

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

RUN apt-get -y update && DEBIAN_FRONTEND="noninteractive" \
    apt-get install -y python3 python3-pip aria2 wget qbittorrent-nox \
    tzdata p7zip-full p7zip-rar xz-utils curl ffmpeg \
    locales git unzip libmagic-dev  libpq-dev libffi-dev && \
    apt-get autoremove && locale-gen en_US.UTF-8 &&\
    curl https://rclone.org/install.sh | bash 

ENV LANG="en_US.UTF-8" LANGUAGE="en_US:en"

COPY . .
RUN pip3 install --no-cache-dir -r requirements.txt && \
    mkdir /usr/src/app/storage && mkdir /usr/src/app/config

CMD ["bash", "start.sh"]