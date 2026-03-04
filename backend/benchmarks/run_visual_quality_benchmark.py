import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List

from backend.llm_service import generate_manim_code
from backend.manim_service import run_visual_quality_check


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    k = (len(sorted_values) - 1) * pct
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k - f)
    return d0 + d1


async def run_case(case: Dict[str, Any], qa_mode: str) -> Dict[str, Any]:
    prompt = str(case["prompt"])
    length = str(case["length"])

    start = time.perf_counter()
    code = await generate_manim_code(prompt=prompt, length=length)
    gen_latency = time.perf_counter() - start

    qa_start = time.perf_counter()
    qa_report = run_visual_quality_check(code=code, mode=qa_mode)
    qa_latency = time.perf_counter() - qa_start

    total_latency = gen_latency + qa_latency
    issues = qa_report.get("issues", []) if isinstance(qa_report, dict) else []
    issue_types = [str(issue.get("issue_type", "")) for issue in issues if isinstance(issue, dict)]

    return {
        "prompt": prompt,
        "length": length,
        "gen_latency_seconds": gen_latency,
        "qa_latency_seconds": qa_latency,
        "total_latency_seconds": total_latency,
        "qa_passed": bool(qa_report.get("passed", False)),
        "qa_score": int(qa_report.get("score", 0)),
        "qa_error_count": int(qa_report.get("error_count", 0)),
        "qa_warning_count": int(qa_report.get("warning_count", 0)),
        "issue_types": issue_types,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run visual-quality benchmark suite")
    parser.add_argument(
        "--suite",
        default="backend/benchmarks/prompt_suite.json",
        help="Path to benchmark prompt suite JSON",
    )
    parser.add_argument(
        "--qa-mode",
        default="balanced",
        choices=["balanced", "max"],
        help="Visual QA mode",
    )
    parser.add_argument(
        "--output",
        default="backend/benchmarks/last_benchmark_report.json",
        help="Where to write benchmark results",
    )
    args = parser.parse_args()

    suite_path = Path(args.suite)
    cases = json.loads(suite_path.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise SystemExit("Benchmark suite is empty or invalid.")

    results: List[Dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            continue
        print(f"[{index}/{len(cases)}] Running: {case.get('length')} | {case.get('prompt')}")
        try:
            result = await run_case(case, qa_mode=args.qa_mode)
        except Exception as exc:
            result = {
                "prompt": str(case.get("prompt", "")),
                "length": str(case.get("length", "")),
                "failed": True,
                "error": str(exc),
            }
        results.append(result)

    successful = [row for row in results if not row.get("failed")]
    latencies = [float(row["total_latency_seconds"]) for row in successful]

    out_of_frame_failures = sum(
        1
        for row in successful
        if "out_of_frame" in row.get("issue_types", [])
    )
    overlap_failures = sum(
        1
        for row in successful
        if "text_overlap" in row.get("issue_types", [])
    )

    summary = {
        "total_cases": len(results),
        "successful_cases": len(successful),
        "failed_cases": len(results) - len(successful),
        "median_total_latency_seconds": statistics.median(latencies) if latencies else 0.0,
        "p50_total_latency_seconds": percentile(latencies, 0.50),
        "p95_total_latency_seconds": percentile(latencies, 0.95),
        "avg_total_latency_seconds": statistics.mean(latencies) if latencies else 0.0,
        "out_of_frame_rate": (out_of_frame_failures / len(successful)) if successful else 0.0,
        "overlap_rate": (overlap_failures / len(successful)) if successful else 0.0,
        "qa_mode": args.qa_mode,
        "targets": {
            "out_of_frame_rate_max": 0.05,
            "overlap_rate_max": 0.10,
            "median_latency_increase_max": 0.35,
        },
    }

    output = {
        "summary": summary,
        "results": results,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"Wrote benchmark report to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
