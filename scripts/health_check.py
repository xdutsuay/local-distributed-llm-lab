#!/usr/bin/env python3
"""
LLM Lab - Cluster Health Check Utility

Run diagnostics on the Ray cluster and coordinator services.
"""
import ray
import requests
import sys

def check_ray_cluster():
    """Check Ray cluster status"""
    print("🔍 Checking Ray Cluster...")
    
    try:
        if not ray.is_initialized():
            ray.init(address="auto", namespace="llm-lab", ignore_reinit_error=True)
        
        nodes = ray.nodes()
        alive_nodes = [n for n in nodes if n['Alive']]
        
        print(f"✅ Ray Cluster Active")
        print(f"   Total Nodes: {len(nodes)}")
        print(f"   Alive Nodes: {len(alive_nodes)}")
        
        for node in alive_nodes:
            print(f"   - {node['NodeManagerAddress']} (Resources: {node['Resources']})")
        
        return True
    except Exception as e:
        print(f"❌ Ray Cluster Error: {e}")
        return False

def check_coordinator_api():
    """Check coordinator API endpoints"""
    print("\n🌐 Checking Coordinator API...")
    
    base_url = "http://localhost:8000"
    endpoints = [
        "/health",
        "/api/nodes",
        "/api/tasks",
    ]
    
    all_ok = True
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint} - OK")
            else:
                print(f"⚠️  {endpoint} - Status: {response.status_code}")
                all_ok = False
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint} - Error: {e}")
            all_ok = False
    
    return all_ok

def check_lmstudio():
    """Check LM Studio OpenAI-compatible API when INFERENCE_BACKEND=lmstudio."""
    import os
    if os.getenv("INFERENCE_BACKEND", "ollama").lower() != "lmstudio":
        print("\n🧠 LM Studio check skipped (INFERENCE_BACKEND != lmstudio)")
        return True

    print("\n🧠 Checking LM Studio API...")
    api_base = os.getenv("LMSTUDIO_API_BASE", "http://127.0.0.1:1234/v1")
    try:
        response = requests.get(f"{api_base}/models", timeout=5)
        if response.status_code == 200:
            models = response.json().get("data", [])
            print(f"✅ LM Studio reachable ({len(models)} model(s))")
            return True
        print(f"⚠️  LM Studio /models status: {response.status_code}")
        return False
    except requests.RequestException as e:
        print(f"❌ LM Studio Error: {e}")
        return False


def check_android_nodes():
    """Report mobile/android compute nodes registered via heartbeat."""
    print("\n📱 Checking Android / mobile nodes...")
    try:
        response = requests.get("http://localhost:8000/api/nodes", timeout=5)
        if response.status_code != 200:
            print(f"❌ /api/nodes status: {response.status_code}")
            return False
        active = response.json().get("active_nodes", {})
        mobile = [
            nid
            for nid, info in active.items()
            if "mobile_compute" in info.get("capabilities", [])
            or "Android" in nid
            or info.get("metadata", {}).get("model") == "Mobile-Compute-Node"
        ]
        if mobile:
            print(f"✅ {len(mobile)} mobile/android node(s): {', '.join(mobile[:3])}")
            return True
        print("⚠️  No Android/mobile nodes connected (optional for stable v1)")
        return True
    except Exception as e:
        print(f"❌ Android node check error: {e}")
        return False


def check_workers():
    """Check registered workers"""
    print("\n👷 Checking Worker Registration...")
    
    try:
        response = requests.get("http://localhost:8000/api/nodes", timeout=5)
        if response.status_code == 200:
            data = response.json()
            active_nodes = data.get("active_nodes", {})
            
            if len(active_nodes) == 0:
                print("⚠️  No workers registered")
                return False
            
            print(f"✅ {len(active_nodes)} worker(s) registered:")
            for node_id, info in active_nodes.items():
                model = info.get("metadata", {}).get("model", "unknown")
                print(f"   - {node_id[:20]}... ({model})")
            
            return True
        else:
            print(f"❌ API Error: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Worker Check Error: {e}")
        return False

def main():
    """Run all health checks"""
    print("=" * 50)
    print("LLM Lab - Cluster Health Check")
    print("=" * 50)
    
    checks = [
        check_ray_cluster(),
        check_coordinator_api(),
        check_lmstudio(),
        check_workers(),
        check_android_nodes(),
    ]
    
    print("\n" + "=" * 50)
    if all(checks):
        print("✅ All Systems Operational")
        sys.exit(0)
    else:
        print("⚠️  Some Systems Have Issues")
        sys.exit(1)

if __name__ == "__main__":
    main()
