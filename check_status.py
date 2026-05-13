import json, urllib.request

api_key = "rnd_zMiLkBGLI75UisjKWQAbjK1fmtDq"
svc_id = "srv-d8254j6gvqtc73dc3lvg"

req = urllib.request.Request(
    f"https://api.render.com/v1/services/{svc_id}/deploys",
    headers={"Authorization": f"Bearer {api_key}"}
)
resp = urllib.request.urlopen(req)
deploys = json.loads(resp.read())
for d in deploys[:3]:
    dep = d["deploy"]
    print(f"{dep['id']}: {dep['status']} - {dep['createdAt'][:19]}")
