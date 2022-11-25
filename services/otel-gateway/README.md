# OpenSAFELY otel-gateway

This is a deployment of the OpenTelemetry Collector
[Gateway](https://opentelemetry.io/docs/concepts/data-collection/#deployment)
on dokku4.

## Testing

### CI Tests

```
just test-ci
```

This will:
  
1. spin up a test endpoint
2. build the latest otel-gateway image
3. run that, pointing at the test endpoint
4. run some tests against it, using the test endpoint to inspect the output.

The goal is to ensure that the gateway works properly, including forwarding
traffic and basic auth.

### Integration Tests

You will need a valid API key for the developement environment

```
export HONEYCOMB_KEY=...
just test-integration
```

This will print a link where you can go and view the data in the Honeycomb UI.


## Deploy to dokku

From dokku4

```bash
docker pull ghcr.io/opensafely-core/otel-gateway:latest
dokku git:from-image otel-gateway ghcr.io/opensafely-core/otel-gateway:latest
```

## View logs

```
dokku logs otel-gateway
```


## Dokku app set up

```bash
dokku apps:create otel-gateway
dokku domains:add otel-gateway collector.opensafely.org
dokku proxy:ports-add otel-gateway https:443:4318
dokku letsencrypt:enable otel-gateway

# secrets
dokku config:set otel-gateway HONEYCOMB_KEY=... BASIC_AUTH_USER=... BASIC_AUTH_PASSWORD=...

```



## Refs

https://opentelemetry.io/docs/concepts/data-collection
https://docs.honeycomb.io/getting-data-in/otel-collector/
https://dokku.com/docs~v0.26.8//deployment/methods/git/#initializing-an-app-repository-from-a-docker-image
https://jessitron.com/2021/08/11/run-an-opentelemetry-collector-locally-in-docker/

## future reference

Might need this in future for building customer otel distributions:

https://github.com/open-telemetry/opentelemetry-collector/tree/main/cmd/builder
