"""Safe demo canary: report access to the generated .env honeytoken to PikaTrap."""
import json
import os
from urllib.request import Request, urlopen

payload = json.dumps({"session_id": os.getenv("PIKATRAP_SESSION", "demo-attacker-01"), "source_ip": os.getenv("PIKATRAP_SOURCE_IP", "172.20.0.10")}).encode()
request = Request(os.getenv("PIKATRAP_API", "http://localhost:8000") + "/api/v1/demo/trigger", data=payload, headers={"Content-Type": "application/json"}, method="POST")
with urlopen(request) as response:
    print(response.read().decode())
