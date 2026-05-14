import json, os, time
from pathlib import Path

MEMORY_FILE = Path(__file__).parent / "chat_memory.json"
CHAT_HISTORY = Path(__file__).parent / "patients.json"

def save_memory():
    if CHAT_HISTORY.exists():
        data = json.loads(CHAT_HISTORY.read_text(encoding="utf-8"))
        patients = data.get("patients", [])
    else:
        patients = []

    memory = {
        "last_save": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_patients": len(patients),
        "patient_names": [p.get("name", "?") for p in patients[-10:]],
    }
    MEMORY_FILE.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Memory] Saved: {memory['total_patients']} patients, {memory['last_save']}")

if __name__ == "__main__":
    while True:
        try:
            save_memory()
        except Exception as e:
            print(f"[Memory] Error: {e}")
        time.sleep(600)  # 10 minutes
