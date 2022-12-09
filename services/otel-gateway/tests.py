import json
import os
import time
from pathlib import Path

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import \
    OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

import pytest

trace_file = Path("exported/traces.json")
metric_file = Path("exported/metrics.json")

# set up trace exporting
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer("testscope")


def generate_test_trace():
    """Fixture to generate trace data."""
    with tracer.start_as_current_span("testname") as span:
        span.set_attribute("testattr", "testvalue")


# Currently, python sdk can only export metrics over grpc, not http. And our
# collector is http only atm. Once the following pull request lands then we can
# add a test for metrics too.
# https://github.com/open-telemetry/opentelemetry-python/pull/2891
def generate_test_metric():
    """Fixture to generate metric data"""
    pass



@pytest.fixture(autouse=True)
def clear_files():
    # ensure clean data
    if trace_file.exists():
        os.truncate(str(trace_file), 0)
    if metric_file.exists():
        os.truncate(str(metric_file), 0)


def get_output(path):
    # wait for file to be written to, typically a few hundered 100ms
    while path.exists() and path.stat().st_size == 0:
        time.sleep(0.01)

    return json.loads(path.read_text())


def test_trace():
    generate_test_trace()

    output = get_output(trace_file)
    spans = output["resourceSpans"]

    assert len(spans) == 1
    span = spans[0]

    # annoying json
    service_name = list(
        filter(
            lambda d: d["key"] == "service.name",
            span["resource"]["attributes"],
        )
    )[0]
    assert service_name["value"]["stringValue"] == "otel-gateway-tests"

    assert span["scopeSpans"][0]["scope"]["name"] == "testscope"
    span_data = span["scopeSpans"][0]["spans"][0]
    assert span_data["name"] == "testname"
    assert span_data["attributes"][0]["key"] == "testattr"
    assert span_data["attributes"][0]["value"] == {"stringValue": "testvalue"}


if __name__ == "__main__":
    print("Generating trace data")
    generate_test_trace()
    # print("Generating metric data")
    # generate_test_metric()




