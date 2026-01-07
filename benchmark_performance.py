#!/usr/bin/env python3
"""
Performance Benchmark Suite for Conversational API
Measures response times, throughput, and resource usage
"""

import requests
import json
import time
import statistics
from typing import Dict, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
BASE_URL = "http://localhost:3001"
API_PREFIX = "/api/v1/conversational"
WARMUP_REQUESTS = 5
BENCHMARK_REQUESTS = 50
CONCURRENT_USERS = [1, 5, 10]

# Benchmark results
benchmark_results = {
    "timestamp": datetime.now().isoformat(),
    "configuration": {
        "base_url": BASE_URL,
        "warmup_requests": WARMUP_REQUESTS,
        "benchmark_requests": BENCHMARK_REQUESTS,
        "concurrent_users": CONCURRENT_USERS
    },
    "endpoints": {}
}

def make_request(url: str, method: str = "GET", data: Dict = None) -> float:
    """Make a single request and return response time in ms"""
    start_time = time.time()
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            return -1
        
        response_time = (time.time() - start_time) * 1000
        return response_time if response.status_code < 500 else -1
    except Exception:
        return -1

def benchmark_endpoint(name: str, url: str, method: str = "GET", data: Dict = None):
    """Benchmark a single endpoint"""
    print(f"\n🔍 Benchmarking: {name}")
    print(f"   URL: {url}")
    print(f"   Method: {method}")
    
    # Warmup
    print(f"   Warming up ({WARMUP_REQUESTS} requests)...", end=" ")
    for _ in range(WARMUP_REQUESTS):
        make_request(url, method, data)
    print("✓")
    
    results = {
        "url": url,
        "method": method,
        "sequential": {},
        "concurrent": {}
    }
    
    # Sequential benchmark
    print(f"   Sequential test ({BENCHMARK_REQUESTS} requests)...", end=" ")
    response_times = []
    for _ in range(BENCHMARK_REQUESTS):
        rt = make_request(url, method, data)
        if rt > 0:
            response_times.append(rt)
    
    if response_times:
        results["sequential"] = {
            "requests": len(response_times),
            "mean_ms": round(statistics.mean(response_times), 2),
            "median_ms": round(statistics.median(response_times), 2),
            "min_ms": round(min(response_times), 2),
            "max_ms": round(max(response_times), 2),
            "stdev_ms": round(statistics.stdev(response_times), 2) if len(response_times) > 1 else 0,
            "p95_ms": round(sorted(response_times)[int(len(response_times) * 0.95)], 2),
            "p99_ms": round(sorted(response_times)[int(len(response_times) * 0.99)], 2),
            "throughput_rps": round(len(response_times) / (sum(response_times) / 1000), 2)
        }
        print(f"✓ (Mean: {results['sequential']['mean_ms']}ms)")
    else:
        print("✗ (All requests failed)")
        results["sequential"] = {"error": "All requests failed"}
    
    # Concurrent benchmarks
    for num_users in CONCURRENT_USERS:
        print(f"   Concurrent test ({num_users} users, {BENCHMARK_REQUESTS} requests)...", end=" ")
        response_times = []
        
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(make_request, url, method, data) for _ in range(BENCHMARK_REQUESTS)]
            for future in as_completed(futures):
                rt = future.result()
                if rt > 0:
                    response_times.append(rt)
        
        if response_times:
            results["concurrent"][f"{num_users}_users"] = {
                "requests": len(response_times),
                "mean_ms": round(statistics.mean(response_times), 2),
                "median_ms": round(statistics.median(response_times), 2),
                "min_ms": round(min(response_times), 2),
                "max_ms": round(max(response_times), 2),
                "stdev_ms": round(statistics.stdev(response_times), 2) if len(response_times) > 1 else 0,
                "p95_ms": round(sorted(response_times)[int(len(response_times) * 0.95)], 2),
                "p99_ms": round(sorted(response_times)[int(len(response_times) * 0.99)], 2),
                "throughput_rps": round(len(response_times) / (sum(response_times) / 1000), 2)
            }
            print(f"✓ (Mean: {results['concurrent'][f'{num_users}_users']['mean_ms']}ms)")
        else:
            print("✗ (All requests failed)")
            results["concurrent"][f"{num_users}_users"] = {"error": "All requests failed"}
    
    benchmark_results["endpoints"][name] = results

def main():
    """Run performance benchmarks"""
    print("=" * 80)
    print("Conversational API Performance Benchmark Suite")
    print("=" * 80)
    print(f"Base URL: {BASE_URL}")
    print(f"Warmup Requests: {WARMUP_REQUESTS}")
    print(f"Benchmark Requests: {BENCHMARK_REQUESTS}")
    print(f"Concurrent Users: {CONCURRENT_USERS}")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 80)
    
    # Benchmark key endpoints
    endpoints_to_test = [
        ("Health Check", f"{BASE_URL}/health", "GET", None),
        ("List Episodes", f"{BASE_URL}{API_PREFIX}/episodes", "GET", None),
        ("List Characters", f"{BASE_URL}{API_PREFIX}/characters", "GET", None),
        ("List Scenes", f"{BASE_URL}{API_PREFIX}/scenes", "GET", None),
        ("Get Episode State (404)", f"{BASE_URL}{API_PREFIX}/episode/test-id/state", "GET", None),
    ]
    
    for name, url, method, data in endpoints_to_test:
        benchmark_endpoint(name, url, method, data)
    
    # Print Summary
    print("\n" + "=" * 80)
    print("Performance Benchmark Summary")
    print("=" * 80)
    
    for endpoint_name, results in benchmark_results["endpoints"].items():
        print(f"\n📊 {endpoint_name}")
        print(f"   URL: {results['url']}")
        
        if "error" not in results["sequential"]:
            seq = results["sequential"]
            print(f"   Sequential Performance:")
            print(f"      Mean: {seq['mean_ms']}ms | Median: {seq['median_ms']}ms")
            print(f"      Min: {seq['min_ms']}ms | Max: {seq['max_ms']}ms")
            print(f"      P95: {seq['p95_ms']}ms | P99: {seq['p99_ms']}ms")
            print(f"      Throughput: {seq['throughput_rps']} req/s")
            
            print(f"   Concurrent Performance:")
            for users, metrics in results["concurrent"].items():
                if "error" not in metrics:
                    print(f"      {users}: Mean {metrics['mean_ms']}ms | P95 {metrics['p95_ms']}ms | {metrics['throughput_rps']} req/s")
        else:
            print(f"   ❌ Benchmark failed: {results['sequential']['error']}")
    
    # Calculate overall statistics
    print("\n" + "=" * 80)
    print("Overall Statistics")
    print("=" * 80)
    
    all_sequential_means = []
    all_concurrent_means = {users: [] for users in [f"{u}_users" for u in CONCURRENT_USERS]}
    
    for results in benchmark_results["endpoints"].values():
        if "error" not in results["sequential"]:
            all_sequential_means.append(results["sequential"]["mean_ms"])
            for users in all_concurrent_means.keys():
                if users in results["concurrent"] and "error" not in results["concurrent"][users]:
                    all_concurrent_means[users].append(results["concurrent"][users]["mean_ms"])
    
    if all_sequential_means:
        print(f"\n📈 Sequential Performance (across all endpoints):")
        print(f"   Average Mean Response Time: {statistics.mean(all_sequential_means):.2f}ms")
        print(f"   Best Endpoint: {min(all_sequential_means):.2f}ms")
        print(f"   Worst Endpoint: {max(all_sequential_means):.2f}ms")
    
    for users, means in all_concurrent_means.items():
        if means:
            print(f"\n📈 Concurrent Performance ({users}):")
            print(f"   Average Mean Response Time: {statistics.mean(means):.2f}ms")
            print(f"   Best Endpoint: {min(means):.2f}ms")
            print(f"   Worst Endpoint: {max(means):.2f}ms")
    
    # Performance grades
    print("\n" + "=" * 80)
    print("Performance Grades")
    print("=" * 80)
    
    if all_sequential_means:
        avg_response = statistics.mean(all_sequential_means)
        if avg_response < 10:
            grade = "A+ (Excellent)"
        elif avg_response < 50:
            grade = "A (Very Good)"
        elif avg_response < 100:
            grade = "B (Good)"
        elif avg_response < 200:
            grade = "C (Acceptable)"
        else:
            grade = "D (Needs Improvement)"
        
        print(f"\n🏆 Overall Grade: {grade}")
        print(f"   Average Response Time: {avg_response:.2f}ms")
        print(f"\n   Performance Targets:")
        print(f"      ✓ < 10ms: Excellent (A+)")
        print(f"      ✓ < 50ms: Very Good (A)")
        print(f"      ✓ < 100ms: Good (B)")
        print(f"      ✓ < 200ms: Acceptable (C)")
        print(f"      ✗ > 200ms: Needs Improvement (D)")
    
    # Save results
    with open("benchmark_results.json", "w") as f:
        json.dump(benchmark_results, f, indent=2)
    
    print("\n" + "=" * 80)
    print(f"📄 Detailed results saved to: benchmark_results.json")
    print(f"⏱️  Completed: {datetime.now().isoformat()}")
    print("=" * 80)

if __name__ == "__main__":
    main()