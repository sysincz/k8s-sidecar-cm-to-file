FROM       python:3.6-slim-stretch
RUN        pip install kubernetes==6.0.0
RUN        mkdir /app
RUN        apt-get update && apt-get -y install wget vim
RUN        wget https://github.com/prometheus/alertmanager/releases/download/v0.15.3/alertmanager-0.15.3.linux-amd64.tar.gz -P /tmp/ && cd /tmp/ && tar xvfz /tmp/alertmanager-0.15.3.linux-amd64.tar.gz &&  mv /tmp/alertmanager-0.15.3.linux-amd64/amtool /app/
RUN        rm -rf /tmp/* && apt-get clean
COPY       sidecar/sidecar.py /app/
ENV         PYTHONUNBUFFERED=1
WORKDIR    /app/
CMD [ "python", "-u", "/app/sidecar.py" ]
