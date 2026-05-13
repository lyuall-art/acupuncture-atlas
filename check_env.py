import json, urllib.request

api_key = "rnd_zMiLkBGLI75UisjKWQAbjK1fmtDq"
svc_id = "srv-d8254j6gvqtc73dc3lvg"

req = urllib.request.Request(
    "https://api.render.com/v1/services/" + svc_id + "/env-vars",
    headers={"Authorization": "Bearer " + api_key}
)
resp = urllib.request.urlopen(req)
vars = json.loads(resp.read())
for v in vars:
    print(v["envVar"]["key"], "=", v["envVar"]["value"][:40])
