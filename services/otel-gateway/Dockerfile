# we use the contrib image for basicauth and other bits
#
# This image is build FROM scratch, so doesn't include *any* tools:
# 
# https://github.com/open-telemetry/opentelemetry-collector-releases/blob/main/distributions/otelcol/Dockerfile
#
FROM otel/opentelemetry-collector-contrib:0.84.0

LABEL org.opencontainers.image.authors="tech@opensafely.org" \
      org.opencontainers.image.url="opensafely.org" \
      org.opencontainers.image.vendor="OpenSAFELY" \
      org.opencontainers.image.source="https://github.com/opensafely-sysadmin"

# default config, can be overridden at runtime
ENV HONEYCOMB_ENDPOINT="https://api.honeycomb.io"
ENV METRICS_DATASET="jobrunner-metrics"
ENV LOG_LEVEL="info"

# these must be provided at runtime
# ENV HONEYCOMB_KEY
# ENV BASIC_AUTH_USER
# ENV BASIC_AUTH_PASSWORD

COPY config.yaml /etc/otelcol-contrib/config.yaml
