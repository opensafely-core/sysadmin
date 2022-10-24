from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import \
    OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

# set up trace exporting
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("testscope")


def generate_trace():
    with tracer.start_as_current_span("testname") as span:
        span.set_attribute("testattr", "testvalue")


# Currently, python sdk can only export metrics over grpc, not http. And our
# collector is http only atm. Once the following pull request lands then we can
# add a test for metrics too.
# https://github.com/open-telemetry/opentelemetry-python/pull/2891
def generate_metric():
    pass


if __name__ == "__main__":
    print("Generating trace data")
    generate_trace()
    # print("Generating metric data")
    # generate_metric()
