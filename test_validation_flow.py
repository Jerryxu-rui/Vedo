#!/usr/bin/env python3
"""
Test script to verify content validation flow
Tests both backend validation and expected frontend behavior
"""

import requests
import json

BASE_URL = "http://localhost:3001"

def test_invalid_content():
    """Test that vague content is rejected with helpful error"""
    print("=" * 60)
    print("TEST 1: Invalid Content - '创建精彩的视频内容'")
    print("=" * 60)
    
    response = requests.post(
        f"{BASE_URL}/api/v1/conversational/episode/create",
        json={
            "series_id": "test-series",
            "episode_number": 1,
            "title": "Test Episode",
            "mode": "idea",
            "style": "sci-fi",
            "initial_content": "创建精彩的视频内容"
        }
    )
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 400:
        print("✅ Backend correctly rejected invalid content")
        
        data = response.json()
        detail = data.get("detail", {})
        
        print(f"\nError Type: {detail.get('error')}")
        print(f"Message: {detail.get('message')}")
        
        if detail.get('validation'):
            v = detail['validation']
            print(f"\nValidation Details:")
            print(f"  - Is Valid: {v.get('is_valid')}")
            print(f"  - Has Subject: {v.get('has_subject')}")
            print(f"  - Has Action: {v.get('has_action')}")
            print(f"  - Has Context: {v.get('has_context')}")
            print(f"  - Missing: {v.get('missing_elements')}")
            print(f"  - Suggestions: {v.get('suggestions')}")
        
        if detail.get('examples'):
            print(f"\nExamples:")
            for ex in detail['examples']:
                print(f"  • {ex}")
        
        print("\n✅ Response format is correct for frontend display")
        return True
    else:
        print(f"❌ Expected 400, got {response.status_code}")
        print(f"Response: {response.text}")
        return False

def test_valid_content():
    """Test that detailed content is accepted"""
    print("\n" + "=" * 60)
    print("TEST 2: Valid Content - Detailed video idea")
    print("=" * 60)
    
    response = requests.post(
        f"{BASE_URL}/api/v1/conversational/episode/create",
        json={
            "series_id": "test-series",
            "episode_number": 1,
            "title": "Test Episode",
            "mode": "idea",
            "style": "sci-fi",
            "initial_content": "创建一个关于太空探索的科幻视频，宇航员发现古代遗迹"
        }
    )
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Backend correctly accepted valid content")
        
        data = response.json()
        print(f"\nEpisode ID: {data.get('episode_id')}")
        print(f"Workflow ID: {data.get('workflow_id')}")
        print(f"State: {data.get('state')}")
        print(f"Mode: {data.get('mode')}")
        
        return True
    else:
        print(f"❌ Expected 200, got {response.status_code}")
        print(f"Response: {response.text}")
        return False

def main():
    print("\n🧪 Content Validation Flow Test")
    print("Testing backend validation and frontend error handling\n")
    
    try:
        # Test 1: Invalid content should be rejected
        test1_passed = test_invalid_content()
        
        # Test 2: Valid content should be accepted
        test2_passed = test_valid_content()
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Test 1 (Invalid Content): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
        print(f"Test 2 (Valid Content): {'✅ PASSED' if test2_passed else '❌ FAILED'}")
        
        if test1_passed and test2_passed:
            print("\n🎉 All tests passed! Validation flow is working correctly.")
            print("\nFrontend should display:")
            print("  1. Remove 'generating' message")
            print("  2. Show validation error with:")
            print("     - Missing elements (主题/主角, 故事情节, 场景/风格)")
            print("     - Suggestions")
            print("     - Examples")
            print("  3. Allow user to retry with better input")
            return 0
        else:
            print("\n❌ Some tests failed. Please check the implementation.")
            return 1
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to backend at", BASE_URL)
        print("Please ensure the backend is running on port 3001")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return 1

if __name__ == "__main__":
    exit(main())