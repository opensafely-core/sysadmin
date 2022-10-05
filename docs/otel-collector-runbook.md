# Deploy otel-collector 

## Deploy an open collector

Deploy an OpenTelemetry Collector [Gateway](https://opentelemetry.io/docs/concepts/data-collection/#deployment) on dokku2.

For interest, here is the [Dockerfile the distribution is built on](https://github.com/open-telemetry/opentelemetry-collector-releases/blob/main/distributions/otelcol/Dockerfile).

```bash
dokku apps:create otel-gateway
# include the -contrib extras inc. httpbasicauthextension
dokku git:from-image otel-gateway otel/opentelemetry-collector-contrib:0.54.0
# for the minimal image use:
# dokku git:from-image otel-gateway otel/opentelemetry-collector:0.54.0

dokku domains:add otel-gateway collector.opensafely.org
dokku domains:remove otel-gateway otel-gateway.dokku2.ebmdatalab.net

# create a place to store config files
dokku storage:ensure-directory otel-gateway

dokku config:set otel-gateway HONEYCOMB_API_KEY=...honeycomb_key...
```

Contents of `/var/lib/dokku/data/storage/otel-gateway/config.yaml`:

```yaml
receivers:
  otlp:
    protocols:
      http:

processors:
  batch:

exporters:
  logging:
    logLevel: info

  otlphttp:
    endpoint: "https://api.honeycomb.io"
    headers:
      "x-honeycomb-team": "${HONEYCOMB_API_KEY}"
# required to support metrics spans
#      "x-honeycomb-dataset": "gateway-test"

service:
  extensions: []
  pipelines:
    traces:
      receivers: [otlp]
      processors: []
      exporters: [otlphttp, logging]

```

Install the config & set-up https:

```bash
# if using the minimal image replace with /etc/otelcol/config.yaml
dokku storage:mount otel-gateway /var/lib/dokku/data/storage/otel-gateway/config.yaml:/etc/otelcol-contrib/config.yaml

# We need to generate a self-signed cert and expose port 443
# before we can enable letsencrypt
dokku certs:generate otel-gateway collector.opensafely.org
dokku proxy:ports-add otel-gateway https:443:4318
dokku letsencrypt:enable otel-gateway

# then restart so it uses it, use this to reload the config file after changes
dokku ps:restart otel-gateway

# view logging output
# Nb. if you unintentionally shut down the container when closing this,
# use ps:restart above to get it going
sudo docker container attach otel-gateway.web.1 --no-stdin
```

### Refs

https://opentelemetry.io/docs/concepts/data-collection
https://docs.honeycomb.io/getting-data-in/otel-collector/
https://dokku.com/docs~v0.26.8//deployment/methods/git/#initializing-an-app-repository-from-a-docker-image
https://jessitron.com/2021/08/11/run-an-opentelemetry-collector-locally-in-docker/

### test script

* install [ubuntu pkg dependencies](https://github.com/pyenv/pyenv/wiki#suggested-build-environment)

```bash
sudo apt-get install make build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
``` 

* install pyenv
* install python 3.7.13
* create venv & install requirements for...
* using `python -m pip install -r requirements.txt`
* demo script from https://docs.honeycomb.io/getting-data-in/opentelemetry/python/
* use grpc not http


```bash
# send some test data!
export OTEL_EXPORTER_OTLP_ENDPOINT="https://collector.opensafely.org"
export OTEL_EXPORTER_OTLP_HEADERS="x-honeycomb-dataset=gateway-test"
export OTEL_SERVICE_NAME="gateway-test"
python tracing.py

# for reference in case you want to send direct to honeycomb
export OTEL_EXPORTER_OTLP_ENDPOINT="https://api.honeycomb.io"
export OTEL_EXPORTER_OTLP_HEADERS="x-honeycomb-team=...honeycomb_key...,x-honeycomb-dataset=gateway-test"
export OTEL_SERVICE_NAME="gateway-test"
python tracing.py
```

## authenticating the collector's server

There are more options in [opentelemetry-collector-contrib](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/extension
), we're starting with [basicauthextension](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/extension/basicauthextension
) because it's simple & sufficient for our current needs. (For the maximum, [custom auth](https://opentelemetry.io/docs/collector/custom-auth/) is also available...).

### Configure auth

```bash
# create password
echo -n 'badpassword' | htpasswd -ci /var/lib/dokku/data/storage/otel-gateway/.htpasswd test
# load into the container
dokku storage:mount otel-gateway /var/lib/dokku/data/storage/otel-gateway/.htpasswd:/etc/otel.htpasswd
```

Add auth info to `config.yaml`:

```yaml
extensions:
  basicauth/server:
    htpasswd:
      file: /etc/otel.htpasswd

receivers:
  otlp:
    protocols:
      http:
        auth:
          authenticator: basicauth/server

processors:
  batch:

exporters:
  logging:
    logLevel: debug

  otlphttp:
    endpoint: "https://api.honeycomb.io"
    headers:
      "x-honeycomb-team": "${HONEYCOMB_API_KEY}"

service:
  extensions: [basicauth/server]
  pipelines:
    traces:
      receivers: [otlp]
      processors: []
      exporters: [otlphttp, logging]

```

Configure your client:

```bash
# get the header
$ echo -n 'test:badpassword' | base64 | sed -e "s/.*/Authorization=Basic%20\0/g"
Authorization=Basic%20dGVzdDpiYWRwYXNzd29yZA==
```

and send some test spans:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://collector.opensafely.org"
# add any other headers to taste
# `=` is specifically allowed in the hash & does not need to be encoded/escaped
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic%20dGVzdDpiYWRwYXNzd29yZA==,x-honeycomb-dataset=gateway-test"
python tracing.py
```

## future reference

Might need this in future for building customer otel distributions:

https://github.com/open-telemetry/opentelemetry-collector/tree/main/cmd/builder
