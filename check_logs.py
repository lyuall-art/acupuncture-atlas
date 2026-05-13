import json, urllib.request

api_key = "rnd_zMiLkBGLI75UisjKWQAbjK1fmtDq"
svc_id = "srv-d8254j6gvqtc73dc3lvg"

req = urllib.request.Request(
    "https://api.render.com/v1/services/" + svc_id + "/deploys",
    headers={"Authorization": "Bearer " + api_key}
)
resp = urllib.request.urlopen(req)
deploys = json.loads(resp.read())
latest = deploys[0]["deploy"]
print("Latest deploy:", latest["id"])
print("Status:", latest["status"])
print("Finished:", latest.get("finishedAt", "N/A"))
