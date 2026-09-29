import json
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logs = [json.loads(l) for l in open("data/logs.jsonl", encoding="utf-8") if l.strip()]

print("=== INCIDENT LOGS (latency > 2000ms) ===")
for r in logs:
    if r.get("event") == "response_sent" and r.get("latency_ms", 0) > 2000:
        cid = r["correlation_id"]
        lat = r["latency_ms"]
        feat = r.get("feature")
        sess = r.get("session_id")
        uid = r.get("user_id_hash")
        ts = r.get("ts")
        print(f"  cid={cid} lat={lat}ms feat={feat} sess={sess} uid={uid} ts={ts}")

print()
print("=== NORMAL LOGS (latency <= 2000ms) ===")
count = 0
for r in logs:
    if r.get("event") == "response_sent" and r.get("latency_ms", 0) <= 2000:
        count += 1
        cid = r["correlation_id"]
        lat = r["latency_ms"]
        feat = r.get("feature")
        print(f"  cid={cid} lat={lat}ms feat={feat}")
print(f"  Total normal: {count}")

print()
incident_logs = [r for r in logs if r.get("event") == "response_sent" and r.get("latency_ms", 0) > 2000]
if incident_logs:
    pick = incident_logs[0]
    print("=== SELECTED FOR TRACE INVESTIGATION ===")
    print(f"  correlation_id: {pick['correlation_id']}")
    print(f"  latency_ms: {pick['latency_ms']}")
    print(f"  feature: {pick.get('feature')}")
    print(f"  session_id: {pick.get('session_id')}")
    print(f"  user_id_hash: {pick.get('user_id_hash')}")
    print(f"  timestamp: {pick.get('ts')}")
