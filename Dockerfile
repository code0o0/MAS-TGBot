FROM ubuntu:20.04

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

RUN apt-get -y update && DEBIAN_FRONTEND="noninteractive" \
    apt-get install -y python3.8 python3-pip aria2 wget qbittorrent-nox \
    tzdata p7zip-full p7zip-rar xz-utils curl pv jq ffmpeg \
    locales git unzip rtmpdump libmagic-dev libcurl4-openssl-dev \
    libssl-dev libc-ares-dev libsodium-dev libcrypto++-dev \
    libsqlite3-dev libfreeimage-dev libpq-dev libffi-dev && \
    apt-get autoremove && locale-gen en_US.UTF-8 &&\
    curl https://rclone.org/install.sh | bash 

ENV LANG="en_US.UTF-8" LANGUAGE="en_US:en" MEGA_SDK_VERSION="3.12.0" LD_LIBRARY_PATH="/usr/local/lib/python3.8/dist-packages/mega"

COPY . .
RUN pip3 install --no-cache-dir -r requirements.txt && \
    mkdir /usr/src/app/storage && mkdir /usr/src/app/config &&\
    pip3 install /usr/src/app/mega-sdk/megasdk-3.12.2-py2.py3-none-any.whl && \
    cd /usr/local/lib/python3.8/dist-packages/mega && ln -s libmega.so libmega.so.31202.0.0 && \
    ln -s libmega.so libmega.so.31202
VOLUME [/usr/src/app/storage /usr/src/app/config]

CMD ["bash", "start.sh"]
