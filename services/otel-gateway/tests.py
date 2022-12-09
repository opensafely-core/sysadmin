import json
import os
import time
from pathlib import Path

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import \
    OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import \
    OTLPSpanExporter
from opentelemetry.metrics import (
    get_meter_provider,
    set_meter_provider,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
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

# set up metric exporting
exporter = OTLPMetricExporter()
# There isn't a direct equivalent of SimpleSpanProcessor, but with the 
# export interval set to 1sec it's close enough
reader = PeriodicExportingMetricReader(exporter, export_interval_millis=1000)
meter_provider = MeterProvider(metric_readers=[reader])
set_meter_provider(meter_provider)
meter = get_meter_provider().get_meter("testmetricscope")


def generate_test_trace():
    """Fixture to generate trace data."""
    with tracer.start_as_current_span("testname") as span:
        span.set_attribute("testattr", "testvalue")


def generate_test_metric():
    """Fixture to generate metric data"""
    counter = meter.create_counter("counter")
    counter.add(1)
    # send two events, just for giggles
    counter.add(2)


@pytest.fixture(autouse=True)
def clear_files():
    # ensure clean data
    # TODO: don't wipe out the trace data if doing metrics test
    if trace_file.exists():
        os.truncate(str(trace_file), 0)
    if metric_file.exists():
        os.truncate(str(metric_file), 0)


def get_output(path):
    # wait for file to be written to, typically a few hundred 100ms
    while path.exists() and path.stat().st_size == 0:
        time.sleep(0.01)

    return json.loads(path.read_text())


def service_name_helper(resource_attributes):
    # annoying json
    return list(
            filter(
                lambda d: d["key"] == "service.name",
                resource_attributes,
            )
        )[0]


def test_trace():
    generate_test_trace()

    output = get_output(trace_file)
    spans = output["resourceSpans"]

    assert len(spans) == 1
    span = spans[0]

    service_name = service_name_helper(span["resource"]["attributes"])
    assert service_name["value"]["stringValue"] == "otel-gateway-tests"

    assert span["scopeSpans"][0]["scope"]["name"] == "testscope"
    span_data = span["scopeSpans"][0]["spans"][0]
    assert span_data["name"] == "testname"
    assert span_data["attributes"][0]["key"] == "testattr"
    assert span_data["attributes"][0]["value"] == {"stringValue": "testvalue"}


def test_metric():
    generate_test_metric()

    output = get_output(metric_file)
    metrics = output["resourceMetrics"]

    assert len(metrics) == 1
    metric = metrics[0]

    service_name = service_name_helper(metric["resource"]["attributes"])
    assert service_name["value"]["stringValue"] == "otel-gateway-tests"

    assert metric["scopeMetrics"][0]["scope"]["name"] == "testmetricscope"
    metric_data = metric["scopeMetrics"][0]["metrics"][0]
    assert metric_data["name"] == "counter"
    assert metric_data["sum"]["dataPoints"][0]["asInt"] == '3'


if __name__ == "__main__":
    print("Generating trace data")
    generate_test_trace()
    print("Generating metric data")
    generate_test_metric()




