import json
import os
import time
from pathlib import Path

import generate
import pytest

trace_file = Path("exported/traces.json")
metric_file = Path("exported/metrics.json")


@pytest.fixture(autouse=True)
def clear_files():
    # ensure test server has stasted up
    #while not trace_file.exists():
    #    time.sleep(0.01)
    #while not metric_file.exists():
    #    time.sleep(0.01)

    # server has fileno already, so we can't delete
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
    generate.generate_trace()

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
