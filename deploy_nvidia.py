import json, urllib.request

api_key = "rnd_zMiLkBGLI75UisjKWQAbjK1fmtDq"
svc_id = "srv-d8254j6gvqtc73dc3lvg"

body = json.dumps({"clearCache": "do_not_clear"}).encode()
req = urllib.request.Request(
    f"https://api.render.com/v1/services/{svc_id}/deploys",
    data=body,
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    method="POST"
)
resp = urllib.request.urlopen(req)
d = json.loads(resp.read())
print(f"Deploy: {d.get('id')} - {d.get('status')}")
print("URL: https://acupuncture-atlas.onrender.com")
