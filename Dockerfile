FROM anasty17/mltb:latest

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

COPY . .
RUN pip3 install --no-cache-dir -r requirements.txt && \
    mkdir /usr/src/app/storage && mkdir /usr/src/app/config && \
    curl https://rclone.org/install.sh | bash

CMD ["bash", "start.sh"]
