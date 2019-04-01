FROM alpine:3.6

ENV KUBE_CLIENT_VERSION="8.0.0" \
    ALERTMANAGER_VERSION="0.15.3"
	
RUN apk add --update --no-cache \
		dumb-init \
		bash \
		python \
        curl \
	&& apk add --no-cache --virtual=build-dependencies \
		python-dev \
		py-pip \
        gcc \
        libc-dev \
        unixodbc-dev \
        libffi-dev \
        openssl-dev \
	&& pip install --no-cache-dir -U \
		passlib \
		kubernetes==${KUBE_CLIENT_VERSION} \
	&& apk del --purge build-dependencies \
	&& rm -fr \
		/var/cache/apk/* \
		/root/.cache \
        /tmp/*

RUN        mkdir /app

RUN        curl -LO https://github.com/prometheus/alertmanager/releases/download/v${ALERTMANAGER_VERSION}/alertmanager-${ALERTMANAGER_VERSION}.linux-amd64.tar.gz \
           && tar -xvzf alertmanager-${ALERTMANAGER_VERSION}.linux-amd64.tar.gz \
           && cp alertmanager-${ALERTMANAGER_VERSION}.linux-amd64/amtool /app \
           && rm -rf alertmanager-${ALERTMANAGER_VERSION}.linux-amd64 \
           && rm -rf alertmanager-${ALERTMANAGER_VERSION}.linux-amd64.tar.gz

COPY       sidecar/sidecar.py /app/
COPY       sidecar/files_to_cm.py /app/
COPY       sidecar/yaml_check.py /app/
ENV         PYTHONUNBUFFERED=1
WORKDIR    /app/
CMD [ "python", "-u", "/app/sidecar.py" ]
