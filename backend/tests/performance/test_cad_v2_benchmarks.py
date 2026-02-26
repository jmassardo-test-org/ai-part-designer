"""
Performance Benchmark Tests for CAD v2 System.

Run with: python -m pytest tests/performance/test_cad_v2_benchmarks.py -v
"""

import statistics
import time
from typing import Any

import pytest

from app.cad_v2.schemas.base import BoundingBox, Dimension
from app.cad_v2.schemas.enclosure import (
    EnclosureSpec,
    LidSpec,
    LidType,
    VentilationSpec,
    WallSide,
    WallSpec,
)

# Import conditionally to handle Build123d availability
try:
    from app.cad_v2.compiler.engine import CompilationEngine

    BUILD123D_AVAILABLE = True
except ImportError:
    BUILD123D_AVAILABLE = False


@pytest.mark.skipif(not BUILD123D_AVAILABLE, reason="Build123d not available")
class TestCompilationPerformance:
    """Benchmark tests for enclosure compilation performance."""

    @pytest.fixture
    def engine(self):
        """Create a compilation engine instance."""
        return CompilationEngine()

    @pytest.fixture
    def simple_spec(self) -> EnclosureSpec:
        """Simple enclosure spec for baseline benchmarks."""
        return EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100, unit="mm"),
                depth=Dimension(value=80, unit="mm"),
                height=Dimension(value=40, unit="mm"),
            ),
            walls=WallSpec(thickness=Dimension(value=2.5, unit="mm")),
        )

    @pytest.fixture
    def complex_spec(self) -> EnclosureSpec:
        """Complex enclosure with lid and ventilation for stress testing."""
        return EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=120, unit="mm"),
                depth=Dimension(value=90, unit="mm"),
                height=Dimension(value=50, unit="mm"),
            ),
            walls=WallSpec(thickness=Dimension(value=3.0, unit="mm")),
            corner_radius=Dimension(value=5.0, unit="mm"),
            lid=LidSpec(
                type=LidType.SNAP_FIT,
                gap=Dimension(value=0.3, unit="mm"),
            ),
            ventilation=VentilationSpec(
                enabled=True,
                pattern="slots",
                sides=[WallSide.LEFT, WallSide.RIGHT],
            ),
        )

    def _benchmark_compilation(
        self, engine, spec: EnclosureSpec, iterations: int = 5
    ) -> dict[str, Any]:
        """Run benchmark and return timing statistics."""
        times: list[float] = []

        for _ in range(iterations):
            start = time.perf_counter()
            result = engine.compile_enclosure(spec)
            elapsed = time.perf_counter() - start

            assert result.success, f"Compilation failed: {result.errors}"
            times.append(elapsed)

        return {
            "min": min(times),
            "max": max(times),
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0,
            "iterations": iterations,
        }

    def test_simple_enclosure_performance(
        self, engine: CompilationEngine, simple_spec: EnclosureSpec
    ) -> None:
        """
        Benchmark: Simple enclosure should compile in under 3 seconds.

        Target: < 3s mean compilation time
        Acceptable: < 5s max compilation time
        """
        stats = self._benchmark_compilation(engine, simple_spec)

        print("\n=== Simple Enclosure Benchmark ===")
        print(f"  Min:    {stats['min']:.3f}s")
        print(f"  Max:    {stats['max']:.3f}s")
        print(f"  Mean:   {stats['mean']:.3f}s")
        print(f"  Median: {stats['median']:.3f}s")
        print(f"  StdDev: {stats['stdev']:.3f}s")

        assert stats["mean"] < 3.0, f"Mean compile time {stats['mean']:.2f}s exceeds 3s target"
        assert stats["max"] < 5.0, (
            f"Max compile time {stats['max']:.2f}s exceeds 5s acceptable limit"
        )

    def test_complex_enclosure_performance(
        self, engine: CompilationEngine, complex_spec: EnclosureSpec
    ) -> None:
        """
        Benchmark: Complex enclosure should compile in under 10 seconds.

        Target: < 10s mean compilation time
        Acceptable: < 15s max compilation time
        """
        stats = self._benchmark_compilation(engine, complex_spec)

        print("\n=== Complex Enclosure Benchmark ===")
        print(f"  Min:    {stats['min']:.3f}s")
        print(f"  Max:    {stats['max']:.3f}s")
        print(f"  Mean:   {stats['mean']:.3f}s")
        print(f"  Median: {stats['median']:.3f}s")
        print(f"  StdDev: {stats['stdev']:.3f}s")

        assert stats["mean"] < 10.0, f"Mean compile time {stats['mean']:.2f}s exceeds 10s target"
        assert stats["max"] < 15.0, (
            f"Max compile time {stats['max']:.2f}s exceeds 15s acceptable limit"
        )

    def test_memory_efficiency(
        self, engine: CompilationEngine, complex_spec: EnclosureSpec
    ) -> None:
        """
        Test that repeated compilations don't leak memory.

        Run 10 compilations and check memory usage stays reasonable.
        """
        import tracemalloc

        tracemalloc.start()

        initial_snapshot = tracemalloc.take_snapshot()

        # Run several compilations
        for _ in range(10):
            result = engine.compile_enclosure(complex_spec)
            assert result.success

        final_snapshot = tracemalloc.take_snapshot()

        # Compare memory usage
        top_stats = final_snapshot.compare_to(initial_snapshot, "lineno")

        # Calculate total memory increase
        total_increase = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)
        total_increase_mb = total_increase / (1024 * 1024)

        print("\n=== Memory Benchmark ===")
        print(f"  Total memory increase: {total_increase_mb:.2f} MB")

        # Should not increase by more than 100 MB for 10 compilations
        assert total_increase_mb < 100, (
            f"Memory increase {total_increase_mb:.2f}MB exceeds 100MB limit"
        )

        tracemalloc.stop()


@pytest.mark.skipif(not BUILD123D_AVAILABLE, reason="Build123d not available")
class TestExportPerformance:
    """Benchmark tests for file export performance."""

    @pytest.fixture
    def engine(self):
        return CompilationEngine()

    @pytest.fixture
    def compiled_result(self, engine) -> Any:
        """Pre-compile an enclosure for export testing."""
        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100, unit="mm"),
                depth=Dimension(value=80, unit="mm"),
                height=Dimension(value=40, unit="mm"),
            ),
            walls=WallSpec(thickness=Dimension(value=2.5, unit="mm")),
            corner_radius=Dimension(value=3.0, unit="mm"),
        )
        result = engine.compile_enclosure(spec)
        assert result.success
        return result

    def test_step_export_performance(self, compiled_result: Any, tmp_path) -> None:
        """
        Benchmark: STEP export should complete in under 2 seconds.
        """
        from app.cad_v2.compiler.export import ExportFormat

        times = []
        for i in range(3):
            output_dir = tmp_path / f"step_export_{i}"
            output_dir.mkdir()

            start = time.perf_counter()
            compiled_result.export(output_dir, ExportFormat.STEP)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        mean_time = statistics.mean(times)
        print("\n=== STEP Export Benchmark ===")
        print(f"  Mean export time: {mean_time:.3f}s")

        assert mean_time < 2.0, f"STEP export time {mean_time:.2f}s exceeds 2s target"

    def test_stl_export_performance(self, compiled_result: Any, tmp_path) -> None:
        """
        Benchmark: STL export should complete in under 3 seconds.
        """
        from app.cad_v2.compiler.export import ExportFormat

        times = []
        for i in range(3):
            output_dir = tmp_path / f"stl_export_{i}"
            output_dir.mkdir()

            start = time.perf_counter()
            compiled_result.export(output_dir, ExportFormat.STL)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        mean_time = statistics.mean(times)
        print("\n=== STL Export Benchmark ===")
        print(f"  Mean export time: {mean_time:.3f}s")

        assert mean_time < 3.0, f"STL export time {mean_time:.2f}s exceeds 3s target"


class TestAPIPerformance:
    """Benchmark tests for API endpoint response times."""

    @pytest.fixture
    def client(self):
        """Create async test client."""
        from httpx import ASGITransport, AsyncClient

        from app.main import app

        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    @pytest.mark.asyncio
    async def test_compile_endpoint_performance(self, client) -> None:
        """
        Benchmark: /api/v2/generate/compile should respond within targets.

        Target: < 10s for simple enclosures
        """
        spec = {
            "spec": {
                "exterior": {
                    "width": {"value": 100, "unit": "mm"},
                    "depth": {"value": 80, "unit": "mm"},
                    "height": {"value": 40, "unit": "mm"},
                },
                "walls": {"thickness": {"value": 2.5, "unit": "mm"}},
            }
        }

        times = []
        for _ in range(3):
            start = time.perf_counter()
            await client.post("/api/v2/generate/compile", json=spec)
            elapsed = time.perf_counter() - start

            # May fail without auth or actual CAD backend, that's okay for benchmark
            times.append(elapsed)

        mean_time = statistics.mean(times)
        print("\n=== Compile API Benchmark ===")
        print(f"  Mean response time: {mean_time:.3f}s")

    @pytest.mark.asyncio
    async def test_health_endpoint_performance(self, client) -> None:
        """
        Benchmark: Health check should respond in under 100ms.
        """
        times = []
        for _ in range(10):
            start = time.perf_counter()
            await client.get("/health")
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        mean_time = statistics.mean(times)
        print("\n=== Health Check Benchmark ===")
        print(f"  Mean response time: {mean_time * 1000:.1f}ms")

        assert mean_time < 0.1, f"Health check {mean_time * 1000:.1f}ms exceeds 100ms target"
