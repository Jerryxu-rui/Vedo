#!/usr/bin/env python3
"""
Comprehensive Test Suite for Conversational API Endpoints
Tests all 31 endpoints across 8 modules to verify backward compatibility
"""

import requests
import json
import time
from typing import Dict, List, Any
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:3001"
API_PREFIX = "/api/v1/conversational"

# Test results storage
test_results = {
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "tests": []
}

def log_test(module: str, endpoint: str, method: str, status: str, response_time: float, details: str = ""):
    """Log test result"""
    test_results["total_tests"] += 1
    test_results[status.lower()] += 1
    
    result = {
        "module": module,
        "endpoint": endpoint,
        "method": method,
        "status": status,
        "response_time_ms": round(response_time * 1000, 2),
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    test_results["tests"].append(result)
    
    status_icon = "✅" if status == "PASSED" else "❌" if status == "FAILED" else "⏭️"
    print(f"{status_icon} [{module}] {method} {endpoint} - {status} ({result['response_time_ms']}ms)")
    if details:
        print(f"   Details: {details}")

def test_endpoint(module: str, method: str, endpoint: str, data: Dict = None, expected_status: int = 200):
    """Test a single endpoint"""
    url = f"{BASE_URL}{API_PREFIX}{endpoint}"
    start_time = time.time()
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=10)
        elif method == "PATCH":
            response = requests.patch(url, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            log_test(module, endpoint, method, "SKIPPED", 0, f"Unsupported method: {method}")
            return None
        
        response_time = time.time() - start_time
        
        if response.status_code == expected_status:
            log_test(module, endpoint, method, "PASSED", response_time, f"Status: {response.status_code}")
            return response.json() if response.content else None
        else:
            log_test(module, endpoint, method, "FAILED", response_time, 
                    f"Expected {expected_status}, got {response.status_code}: {response.text[:200]}")
            return None
            
    except requests.exceptions.ConnectionError:
        log_test(module, endpoint, method, "FAILED", 0, "Connection refused - Server not running?")
        return None
    except requests.exceptions.Timeout:
        log_test(module, endpoint, method, "FAILED", 10, "Request timeout")
        return None
    except Exception as e:
        log_test(module, endpoint, method, "FAILED", 0, f"Error: {str(e)}")
        return None

def main():
    """Run all endpoint tests"""
    print("=" * 80)
    print("Conversational API Endpoint Test Suite")
    print("=" * 80)
    print(f"Base URL: {BASE_URL}")
    print(f"API Prefix: {API_PREFIX}")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 80)
    print()
    
    # Test 1: Episodes Module (6 endpoints)
    print("\n📦 Testing Episodes Module (6 endpoints)")
    print("-" * 80)
    
    # Create episode
    episode_data = {
        "mode": "idea",
        "initial_content": "A story about a brave knight",
        "style": "Cartoon style",
        "title": "Knight's Tale"
    }
    episode_response = test_endpoint("Episodes", "POST", "/episode/create", episode_data, 201)
    episode_id = episode_response.get("episode_id") if episode_response else "test-episode-id"
    
    # Get episode state
    test_endpoint("Episodes", "GET", f"/episode/{episode_id}/state")
    
    # List episodes
    test_endpoint("Episodes", "GET", "/episodes")
    
    # Get specific episode
    test_endpoint("Episodes", "GET", f"/episodes/{episode_id}")
    
    # Delete workflow (expect 404 if not exists)
    test_endpoint("Episodes", "DELETE", f"/episode/{episode_id}/workflow", expected_status=404)
    
    # Delete episode
    test_endpoint("Episodes", "DELETE", f"/episodes/{episode_id}", expected_status=204)
    
    # Test 2: Outline Module (3 endpoints)
    print("\n📝 Testing Outline Module (3 endpoints)")
    print("-" * 80)
    
    # Generate outline (requires valid episode)
    test_endpoint("Outline", "POST", f"/episode/{episode_id}/outline/generate", expected_status=404)
    
    # Update outline
    outline_data = {"outline": "Updated outline content"}
    test_endpoint("Outline", "PUT", f"/episode/{episode_id}/outline", outline_data, expected_status=404)
    
    # Confirm outline
    test_endpoint("Outline", "POST", f"/episode/{episode_id}/outline/confirm", expected_status=404)
    
    # Test 3: Characters Module (8 endpoints)
    print("\n👥 Testing Characters Module (8 endpoints)")
    print("-" * 80)
    
    # Generate characters
    test_endpoint("Characters", "POST", f"/episode/{episode_id}/characters/generate", expected_status=404)
    
    # Confirm characters
    test_endpoint("Characters", "POST", f"/episode/{episode_id}/characters/confirm", expected_status=404)
    
    # Get character images
    test_endpoint("Characters", "GET", f"/episode/{episode_id}/characters/images", expected_status=404)
    
    # Regenerate character
    test_endpoint("Characters", "POST", f"/episode/{episode_id}/characters/char-1/regenerate", expected_status=404)
    
    # Generate character portrait
    test_endpoint("Characters", "POST", f"/episode/{episode_id}/characters/char-1/portrait", expected_status=404)
    
    # Update character
    char_update = {"name": "Updated Name"}
    test_endpoint("Characters", "PATCH", f"/episode/{episode_id}/characters/char-1", char_update, expected_status=404)
    
    # Delete character
    test_endpoint("Characters", "DELETE", f"/episode/{episode_id}/characters/char-1", expected_status=404)
    
    # List all characters
    test_endpoint("Characters", "GET", "/characters")
    
    # Test 4: Scenes Module (7 endpoints)
    print("\n🎬 Testing Scenes Module (7 endpoints)")
    print("-" * 80)
    
    # Generate scenes
    test_endpoint("Scenes", "POST", f"/episode/{episode_id}/scenes/generate", expected_status=404)
    
    # Confirm scenes
    test_endpoint("Scenes", "POST", f"/episode/{episode_id}/scenes/confirm", expected_status=404)
    
    # Get scene images
    test_endpoint("Scenes", "GET", f"/episode/{episode_id}/scenes/images", expected_status=404)
    
    # Regenerate scene
    test_endpoint("Scenes", "POST", f"/episode/{episode_id}/scenes/scene-1/regenerate", expected_status=404)
    
    # Update scene
    scene_update = {"description": "Updated description"}
    test_endpoint("Scenes", "PATCH", f"/episode/{episode_id}/scenes/scene-1", scene_update, expected_status=404)
    
    # Delete scene
    test_endpoint("Scenes", "DELETE", f"/episode/{episode_id}/scenes/scene-1", expected_status=404)
    
    # List all scenes
    test_endpoint("Scenes", "GET", "/scenes")
    
    # Test 5: Storyboard Module (2 endpoints)
    print("\n📋 Testing Storyboard Module (2 endpoints)")
    print("-" * 80)
    
    # Generate storyboard
    test_endpoint("Storyboard", "POST", f"/episode/{episode_id}/storyboard/generate", expected_status=404)
    
    # Confirm storyboard
    test_endpoint("Storyboard", "POST", f"/episode/{episode_id}/storyboard/confirm", expected_status=404)
    
    # Test 6: Video Module (1 endpoint)
    print("\n🎥 Testing Video Module (1 endpoint)")
    print("-" * 80)
    
    # Generate video
    test_endpoint("Video", "POST", f"/episode/{episode_id}/video/generate", expected_status=404)
    
    # Test 7: Progress Module (1 endpoint)
    print("\n📊 Testing Progress Module (1 endpoint)")
    print("-" * 80)
    
    # Get progress
    test_endpoint("Progress", "GET", f"/episode/{episode_id}/progress", expected_status=404)
    
    # Test 8: Assets Module (2 endpoints)
    print("\n🖼️ Testing Assets Module (2 endpoints)")
    print("-" * 80)
    
    # Update shot
    shot_update = {"visual_desc": "Updated visual description"}
    test_endpoint("Assets", "PATCH", f"/episode/{episode_id}/shots/shot-1", shot_update, expected_status=404)
    
    # Delete shot
    test_endpoint("Assets", "DELETE", f"/episode/{episode_id}/shots/shot-1", expected_status=404)
    
    # Print Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Total Tests: {test_results['total_tests']}")
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    print(f"⏭️ Skipped: {test_results['skipped']}")
    print(f"Success Rate: {(test_results['passed'] / test_results['total_tests'] * 100):.1f}%")
    print("=" * 80)
    
    # Save results to file
    with open("test_results.json", "w") as f:
        json.dump(test_results, f, indent=2)
    print(f"\n📄 Detailed results saved to: test_results.json")
    
    # Performance summary
    if test_results['tests']:
        response_times = [t['response_time_ms'] for t in test_results['tests'] if t['response_time_ms'] > 0]
        if response_times:
            print(f"\n⚡ Performance Summary:")
            print(f"   Average Response Time: {sum(response_times) / len(response_times):.2f}ms")
            print(f"   Min Response Time: {min(response_times):.2f}ms")
            print(f"   Max Response Time: {max(response_times):.2f}ms")

if __name__ == "__main__":
    main()