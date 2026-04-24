import time
from collections import defaultdict


class MetricsRegistry:
    def __init__(self):
        self._counters = defaultdict(float)
        self._gauges = {}
        self._histograms = defaultdict(list)

    def inc(self, name: str, value: float = 1.0) -> None:
        self._counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value

    def observe(self, name: str, value: float) -> None:
        values = self._histograms[name]
        values.append(value)
        if len(values) > 512:
            del values[: len(values) - 512]

    def time_block(self, name: str):
        return _MetricTimer(self, name)

    def render_prometheus(self) -> str:
        lines = []
        for name, value in sorted(self._counters.items()):
            lines.append(f"{name}_total {value}")
        for name, value in sorted(self._gauges.items()):
            lines.append(f"{name} {value}")
        for name, values in sorted(self._histograms.items()):
            if not values:
                continue
            count = len(values)
            total = sum(values)
            lines.append(f"{name}_count {count}")
            lines.append(f"{name}_sum {total}")
            lines.append(f"{name}_avg {total / count}")
        return "\n".join(lines) + "\n"


class _MetricTimer:
    def __init__(self, registry: MetricsRegistry, name: str):
        self.registry = registry
        self.name = name
        self.started_at = 0.0

    def __enter__(self):
        self.started_at = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.registry.observe(self.name, time.perf_counter() - self.started_at)
        return False


metrics = MetricsRegistry()
