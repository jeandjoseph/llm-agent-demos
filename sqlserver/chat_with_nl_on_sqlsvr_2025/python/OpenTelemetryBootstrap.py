# OpenTelemetryBootstrap.py
# Clean, minimal, production-ready bootstrap for tracing

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter


class TelemetryConfig:
    def __init__(self, service_name, service_version, environment, otlp_endpoint):
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
        self.otlp_endpoint = otlp_endpoint


class OpenTelemetryBootstrap:
    def __init__(self, config: TelemetryConfig):
        self.config = config
        self.provider = None

    def setup(self):
        """Initialize OpenTelemetry tracing."""
        resource = Resource.create({
            "service.name": self.config.service_name,
            "service.version": self.config.service_version,
            "deployment.environment": self.config.environment,
        })

        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=self.config.otlp_endpoint)
        processor = BatchSpanProcessor(exporter)

        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        self.provider = provider

    def shutdown(self):
        """Flush and shutdown tracing."""
        if self.provider:
            self.provider.shutdown()
