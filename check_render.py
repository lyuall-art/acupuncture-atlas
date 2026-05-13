import json, urllib.request

api_key = "rnd_zMiLkBGLI75UisjKWQAbjK1fmtDq"

svc_id = "srv-d8254j6gvqtc73dc3lvg"
req = urllib.request.Request(
    f"https://api.render.com/v1/services/{svc_id}",
    headers={"Authorization": f"Bearer {api_key}"}
)
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
print(json.dumps(data, indent=2)[:2000])
