import json, urllib.request

api_key = "rnd_zMiLkBGLI75UisjKWQAbjK1fmtDq"
svc_id = "srv-d8254j6gvqtc73dc3lvg"

# Update build command
body = json.dumps({
    "serviceDetails": {
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
resp = urllib.request.urlopen(req)
print(f"Update: {resp.status}")

# Trigger a deploy
body2 = json.dumps({"clearCache": "do_not_clear"}).encode()
req2 = urllib.request.Request(
    f"https://api.render.com/v1/services/{svc_id}/deploys",
    data=body2,
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    },
    method="POST"
)
resp2 = urllib.request.urlopen(req2)
deploy = json.loads(resp2.read())
print(f"Deploy triggered: {resp2.status}")
print(f"Deploy ID: {deploy.get('id')}")
print(f"Status: {deploy.get('status')}")
