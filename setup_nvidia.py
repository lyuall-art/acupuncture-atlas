import json, urllib.request

api_key = "rnd_zMiLkBGLI75UisjKWQAbjK1fmtDq"
svc_id = "srv-d8254j6gvqtc73dc3lvg"

# Update env vars via service update
body = json.dumps({
    "serviceDetails": {
        "env": "python",
        "envSpecificDetails": {
            "buildCommand": "pip install -r backend/requirements.txt",
            "startCommand": "uvicorn backend.main:app --host 0.0.0.0 --port $PORT"
        }
    }
}).encode()

req = urllib.request.Request(
    f"https://api.render.com/v1/services/{svc_id}",
    data=body,
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    },
    method="PATCH"
)
try:
    resp = urllib.request.urlopen(req)
    print(f"Service update: {resp.status}")
except urllib.error.HTTPError as e:
    print(f"Error: {e.code} - {e.read().decode()[:300]}")
