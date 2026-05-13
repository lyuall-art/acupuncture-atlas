import json, urllib.request

api_key = "rnd_zMiLkBGLI75UisjKWQAbjK1fmtDq"
svc_id = "srv-d8254j6gvqtc73dc3lvg"
deploy_id = "dep-d825bqugvqtc73dcaf7g"

req = urllib.request.Request(
    f"https://api.render.com/v1/services/{svc_id}/deploys/{deploy_id}",
    headers={"Authorization": f"Bearer {api_key}"}
)
resp = urllib.request.urlopen(req)
d = json.loads(resp.read())
print(f"Status: {d.get('status')}")
print(f"URL: https://acupuncture-atlas.onrender.com")
