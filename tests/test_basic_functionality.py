#!/usr/bin/env python3
"""
Basic functionality tests for NetStudio application
"""

import pytest
import requests
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8001/api"
FRONTEND_URL = "http://localhost:3000"

class TestNetStudioBasic:
    """Test basic NetStudio functionality"""

    @pytest.mark.slow
    def test_frontend_loads(self):
        """Test that frontend loads correctly"""
        try:
            response = requests.get(FRONTEND_URL, timeout=10)
            assert response.status_code == 200
            assert "NetStudio" in response.text
            print("✅ Frontend loads successfully")
        except Exception as e:
            pytest.fail(f"Frontend failed to load: {e}")

    @pytest.mark.slow
    def test_api_health_check(self):
        """Test API health check endpoint"""
        try:
            response = requests.get(f"{BASE_URL}/health/ping", timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            print("✅ API health check works")
        except Exception as e:
            pytest.fail(f"API health check failed: {e}")

    @pytest.mark.slow
    def test_devices_endpoint(self):
        """Test devices endpoint works without authentication"""
        try:
            response = requests.get(f"{BASE_URL}/devices/", timeout=15)
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            print(f"✅ Devices endpoint works - found {len(data)} devices")

            # Check if we have expected device structure
            if data:
                device = data[0]
                required_fields = ["ip_address", "hostname", "vendor"]
                for field in required_fields:
                    assert field in device, f"Missing field: {field}"

        except Exception as e:
            pytest.fail(f"Devices endpoint failed: {e}")

    @pytest.mark.slow
    def test_scripts_endpoint(self):
        """Test scripts endpoint works without authentication"""
        try:
            response = requests.get(f"{BASE_URL}/scripts/", timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            print(f"✅ Scripts endpoint works - found {len(data)} scripts")
        except Exception as e:
            pytest.fail(f"Scripts endpoint failed: {e}")

    @pytest.mark.slow
    def test_jsnapy_endpoint(self):
        """Test JSNAPy endpoint works without authentication"""
        try:
            response = requests.get(f"{BASE_URL}/jsnapy/templates", timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, dict) or isinstance(data, list)
            print(f"✅ JSNAPy endpoint works")
        except Exception as e:
            pytest.fail(f"JSNAPy endpoint failed: {e}")

@pytest.mark.slow
def test_infrastructure_health():
    """Test overall infrastructure health"""
    results = {}

    # Test Docker containers
    try:
        import subprocess
        result = subprocess.run(
            ["docker-compose", "ps"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            containers = [line for line in result.stdout.split('\n')[2:] if line.strip()]
            results["docker_containers"] = len(containers)
            print(f"✅ Docker containers running: {len(containers)}")
        else:
            pytest.fail("Docker containers not running properly")
    except Exception as e:
        pytest.fail(f"Infrastructure check failed: {e}")

    # Test Redis connectivity
    try:
        response = requests.get(f"{BASE_URL}/health/ping", timeout=5)
        if response.status_code == 200:
            print("✅ Redis connectivity confirmed via API")
        else:
            print("⚠️  Redis connectivity uncertain")
    except:
        print("❌ Redis connectivity failed")

if __name__ == "__main__":
    print("🧪 Running NetStudio Basic Functionality Tests")
    print("=" * 50)

    # Run basic tests
    test_suite = TestNetStudioBasic()

    print("\n📋 Running tests...")

    try:
        test_suite.test_frontend_loads()
        test_suite.test_api_health_check()
        test_suite.test_devices_endpoint()
        test_suite.test_scripts_endpoint()
        test_suite.test_jsnapy_endpoint()
        test_infrastructure_health()

        print("\n🎉 All basic functionality tests passed!")
        print("\n📊 Summary:")
        print("  ✅ Frontend: Operational")
        print("  ✅ API: Operational")
        print("  ✅ Devices: Working")
        print("  ✅ Scripts: Working")
        print("  ✅ JSNAPy: Working")
        print("  ✅ Infrastructure: Stable")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)