import os
import json
import httpx
import re
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', '.env'))

app = FastAPI(title="Acupuncture AI Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")
app.mount("/atlas", StaticFiles(directory=os.path.join(BASE_DIR, "atlas")), name="atlas")
app.mount("/atlas_images", StaticFiles(directory=os.path.join(BASE_DIR, "atlas_images")), name="atlas_images")
app.mount("/atlas_images_small", StaticFiles(directory=os.path.join(BASE_DIR, "atlas_images_small")), name="atlas_images_small")

RECIPES_FILE = os.path.join(BASE_DIR, "recipes.json")
POINTS_FILE = os.path.join(BASE_DIR, "custom_points.json")
BUTTONS_FILE = os.path.join(BASE_DIR, "custom_buttons.json")
PATIENTS_FILE = os.path.join(BASE_DIR, "patients.json")

# ─── Provider Configuration ───
ACTIVE_PROVIDER = os.getenv("ACTIVE_PROVIDER", "ollama")

PROVIDERS = {
    "ollama": {
        "label": "Ollama (Local + Cloud)",
        "base_url": os.getenv("OLLAMA_URL", "http://localhost:11434"),
        "default_model": os.getenv("MODEL_NAME", "qwen2.5:7b"),
        "api_format": "ollama",
        "api_key": None,
        "chat_endpoint": "/api/chat",
        "generate_endpoint": "/api/generate",
        "models_endpoint": "/api/tags",
        "docs_url": "https://ollama.com"
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": os.getenv("OPENROUTER_MODEL", "google/gemma-4-27b-it:free"),
        "api_format": "openai",
        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "chat_endpoint": "/chat/completions",
        "models_endpoint": "/models",
        "docs_url": "https://openrouter.ai/keys"
    },
    "nvidia": {
        "label": "NVIDIA (build.nvidia.com)",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "default_model": os.getenv("NVIDIA_MODEL", "nvidia/llama-3.1-nemotron-70b-instruct"),
        "api_format": "openai",
        "api_key": os.getenv("NVIDIA_API_KEY", ""),
        "chat_endpoint": "/chat/completions",
        "models_endpoint": "/models",
        "docs_url": "https://build.nvidia.com"
    }
}

def get_provider(name=None):
    name = name or ACTIVE_PROVIDER
    return PROVIDERS.get(name, PROVIDERS["ollama"])

def get_headers(provider):
    h = {"Content-Type": "application/json"}
    if provider.get("api_key"):
        h["Authorization"] = f"Bearer {provider['api_key']}"
    if provider.get("api_format") == "openai":
        h["HTTP-Referer"] = "http://localhost:8000"
        h["X-Title"] = "Acupuncture Atlas"
    return h

def load_json(filepath, default):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

SYSTEM_PROMPT = """Ты - эксперт по акупунктуре и ТКМ. Помощник врача.

ПРАВИЛО 1: Если пользователь даёт информацию о точке — прими её, подтверди. Если пользователь ошибается — мягко поправь.
ПРАВИЛО 2: Никогда НЕ выдумывай. Если не знаешь — скажи "нет информации".
ПРАВИЛО 3: Используй дополнительные знания из раздела "Дополнительные знания" ниже, если они есть. Они из TCM книг и достоверны.
ПРАВИЛО 4: Отвечай на русском языке.
"""

# ─── RAG (Retrieval-Augmented Generation) ───
import math

RAG_INDEX_PATH = os.path.join(BASE_DIR, "..", "tcm-index-full.json")
_rag_index = None
_rag_chunks = []

def load_rag_index():
    global _rag_index, _rag_chunks
    if _rag_index is not None:
        return _rag_index, _rag_chunks
    path = RAG_INDEX_PATH
    if not os.path.exists(path):
        print(f"[RAG] Index not found: {path}")
        _rag_index = {}
        _rag_chunks = []
        return _rag_index, _rag_chunks
    with open(path, 'r', encoding='utf-8') as f:
        _rag_index = json.load(f)
    for src, src_data in _rag_index.items():
        for c in src_data.get("chunks", []):
            if c.get("embedding") and c.get("text_full", "").strip():
                _rag_chunks.append({
                    "source": src,
                    "text": c["text_full"],
                    "embedding": c["embedding"]
                })
    print(f"[RAG] Loaded {len(_rag_chunks)} chunks from {len([k for k,v in _rag_index.items() if v.get('chunks')])} sources")
    return _rag_index, _rag_chunks

load_rag_index()

def cosine_similarity(a, b):
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) + 1e-10
    nb = math.sqrt(sum(x * x for x in b)) + 1e-10
    return dot / (na * nb)

async def embed_query(text: str, provider_url: str) -> list:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(
                f"{provider_url}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text[:512]}
            )
            if res.status_code == 200:
                return res.json().get("embedding", [])
    except:
        pass
    return []

async def search_rag(query: str, top_k: int = 5, provider_url: str = "http://localhost:11434") -> list:
    _, chunks = load_rag_index()
    if not chunks:
        return []
    q_embed = await embed_query(query, provider_url)
    if not q_embed:
        return []
    scored = []
    for c in chunks:
        sim = cosine_similarity(q_embed, c["embedding"])
        scored.append((sim, c))
    scored.sort(key=lambda x: -x[0])
    return [{"text": c["text"], "score": round(s, 3), "source": c["source"]} for s, c in scored[:top_k] if s > 0.3]

# ─── Static Routes ───

@app.get("/")
async def root():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

# ─── Provider API ───

@app.get("/api/providers")
async def list_providers():
    return JSONResponse({
        name: {
            "label": p["label"],
            "default_model": p["default_model"],
            "has_key": bool(p.get("api_key")),
            "docs_url": p.get("docs_url", ""),
        }
        for name, p in PROVIDERS.items()
    })

@app.get("/api/provider")
async def get_active_provider():
    p = get_provider()
    return JSONResponse({
        "active": ACTIVE_PROVIDER,
        "label": p["label"],
        "model": p["default_model"],
    })

@app.post("/api/provider")
async def set_active_provider(request: Request):
    body = await request.json()
    provider = body.get("provider", ACTIVE_PROVIDER)
    model = body.get("model", "")
    if provider in PROVIDERS:
        os.environ["ACTIVE_PROVIDER"] = provider
        if model:
            os.environ["MODEL_NAME"] = model
            PROVIDERS["ollama"]["default_model"] = model
        return JSONResponse({"success": True, "provider": provider, "model": PROVIDERS[provider]["default_model"]})
    raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

@app.post("/api/config")
async def update_config(request: Request):
    body = await request.json()
    key = body.get("key", "")
    value = body.get("value", "")
    if not key or not value:
        raise HTTPException(status_code=400, detail="key and value required")
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []
    updated = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"{key}={value}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    os.environ[key] = value
    PROVIDERS["openrouter"]["api_key"] = os.getenv("OPENROUTER_API_KEY", "")
    PROVIDERS["nvidia"]["api_key"] = os.getenv("NVIDIA_API_KEY", "")
    return JSONResponse({"success": True, "key": key})

# ─── Health & Models ───

@app.get("/api/health")
async def health():
    provider = get_provider()
    base_url = provider["base_url"]
    ep = provider.get("models_endpoint", "/api/tags")
    label = provider["label"]
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.get(f"{base_url}{ep}",
                headers=get_headers(provider))
            if res.status_code == 200:
                data = res.json()
                models = []
                if provider["api_format"] == "ollama":
                    models = [m["name"] for m in data.get("models", [])]
                elif provider["api_format"] == "openai":
                    models = [m["id"] for m in data.get("data", [])]
                return {
                    "status": "ok",
                    "provider": ACTIVE_PROVIDER,
                    "label": label,
                    "url": base_url,
                    "models": models[:20],
                    "total_models": len(models),
                }
    except Exception as e:
        return {"status": "error", "provider": ACTIVE_PROVIDER, "label": label, "detail": str(e)}
    return {"status": "error", "provider": ACTIVE_PROVIDER, "label": label, "detail": "Cannot reach API"}

@app.get("/api/models")
async def list_models():
    provider = get_provider()
    try:
        ep = provider.get("models_endpoint", "/api/tags")
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(f"{provider['base_url']}{ep}",
                headers=get_headers(provider))
            data = res.json()
            if provider["api_format"] == "ollama":
                return JSONResponse(data.get("models", []))
            elif provider["api_format"] == "openai":
                return JSONResponse(data.get("data", []))
            return JSONResponse(data)
    except Exception as e:
        return JSONResponse({"error": str(e)})

# ─── Recipes & Points ───

@app.get("/api/recipes")
async def get_recipes():
    return JSONResponse(load_json(RECIPES_FILE, {"recipes": [], "custom_buttons": []}))

@app.post("/api/recipes")
async def add_recipe(request: Request):
    data = await request.json()
    recipes_data = load_json(RECIPES_FILE, {"recipes": [], "custom_buttons": []})
    recipe = {
        "id": data.get("id", f"custom_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
        "name": data.get("name", "Custom Recipe"),
        "description": data.get("description", ""),
        "image": data.get("image", "/atlas_images_small/p104_img0.jpeg"),
        "points": data.get("points", []),
        "indications": data.get("indications", []),
        "created_by": "agent",
        "created_at": datetime.now().isoformat()
    }
    recipes_data["recipes"].append(recipe)
    save_json(RECIPES_FILE, recipes_data)
    return JSONResponse({"success": True, "recipe": recipe})

@app.get("/api/points")
async def get_points():
    return JSONResponse(load_json(POINTS_FILE, {"points": []}))

@app.put("/api/points/{code}")
async def update_point(code: str, request: Request):
    data = await request.json()
    points_data = load_json(POINTS_FILE, {"points": []})
    for point in points_data["points"]:
        if point["code"].upper() == code.upper():
            point["name"] = data.get("name", point.get("name", ""))
            point["meridian"] = data.get("meridian", point.get("meridian", ""))
            point["location"] = data.get("location", point.get("location", ""))
            point["location_detail"] = data.get("location_detail", point.get("location_detail", ""))
            point["technique"] = data.get("technique", point.get("technique", ""))
            point["notes"] = data.get("notes", point.get("notes", ""))
            point["indications"] = data.get("indications", point.get("indications", []))
            save_json(POINTS_FILE, points_data)
            return JSONResponse({"success": True, "point": point})
    raise HTTPException(status_code=404, detail=f"Point {code} not found")

@app.post("/api/points")
async def add_point(request: Request):
    data = await request.json()
    points_data = load_json(POINTS_FILE, {"points": []})
    point = {
        "code": data.get("code", "").upper(),
        "name": data.get("name", ""),
        "meridian": data.get("meridian", ""),
        "location": data.get("location", ""),
        "location_detail": data.get("location_detail", ""),
        "technique": data.get("technique", ""),
        "notes": data.get("notes", ""),
        "indications": data.get("indications", []),
        "created_at": datetime.now().isoformat()
    }
    if not point["code"]:
        raise HTTPException(status_code=400, detail="Point code is required")
    existing = [p for p in points_data["points"] if p["code"] == point["code"]]
    if existing:
        raise HTTPException(status_code=400, detail=f"Point {point['code']} already exists")
    points_data["points"].append(point)
    save_json(POINTS_FILE, points_data)
    return JSONResponse({"success": True, "point": point})

# ─── Buttons ───

@app.get("/api/buttons")
async def get_buttons():
    data = load_json(RECIPES_FILE, {"recipes": [], "custom_buttons": []})
    return JSONResponse(data.get("custom_buttons", []))

@app.post("/api/buttons")
async def add_button(request: Request):
    data = await request.json()
    recipes_data = load_json(RECIPES_FILE, {"recipes": [], "custom_buttons": []})
    button = {
        "id": data.get("id", f"btn_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
        "label": data.get("label", "New Button"),
        "color": data.get("color", "#22c55e"),
        "prompt": data.get("prompt", ""),
        "created_at": datetime.now().isoformat()
    }
    recipes_data.setdefault("custom_buttons", []).append(button)
    save_json(RECIPES_FILE, recipes_data)
    return JSONResponse({"success": True, "button": button})

@app.delete("/api/buttons/{button_id}")
async def delete_button(button_id: str):
    recipes_data = load_json(RECIPES_FILE, {"recipes": [], "custom_buttons": []})
    recipes_data["custom_buttons"] = [b for b in recipes_data.get("custom_buttons", []) if b["id"] != button_id]
    save_json(RECIPES_FILE, recipes_data)
    return JSONResponse({"success": True})

# ─── Patients ───

@app.get("/api/patients")
async def get_patients():
    return JSONResponse(load_json(PATIENTS_FILE, {"patients": []}))

@app.post("/api/patients")
async def create_patient(request: Request):
    data = await request.json()
    patients_data = load_json(PATIENTS_FILE, {"patients": []})
    patient_id = data.get("id", f"patient_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    patient = {
        "id": patient_id,
        "name": data.get("name", "Unknown"),
        "age_sex": data.get("age_sex", ""),
        "symptoms": data.get("symptoms", ""),
        "tongue": data.get("tongue", ""),
        "pulse": data.get("pulse", ""),
        "thermal": data.get("thermal", ""),
        "emotion": data.get("emotion", ""),
        "history": data.get("history", ""),
        "notes": data.get("notes", ""),
        "recipes": data.get("recipes", []),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    patients_data["patients"].append(patient)
    save_json(PATIENTS_FILE, patients_data)
    return JSONResponse({"success": True, "patient": patient})

@app.put("/api/patients/{patient_id}")
async def update_patient(patient_id: str, request: Request):
    data = await request.json()
    patients_data = load_json(PATIENTS_FILE, {"patients": []})
    for patient in patients_data["patients"]:
        if patient["id"] == patient_id:
            patient["name"] = data.get("name", patient["name"])
            patient["age_sex"] = data.get("age_sex", patient["age_sex"])
            patient["symptoms"] = data.get("symptoms", patient["symptoms"])
            patient["tongue"] = data.get("tongue", patient["tongue"])
            patient["pulse"] = data.get("pulse", patient["pulse"])
            patient["thermal"] = data.get("thermal", patient["thermal"])
            patient["emotion"] = data.get("emotion", patient["emotion"])
            patient["history"] = data.get("history", patient["history"])
            patient["notes"] = data.get("notes", patient.get("notes", ""))
            patient["recipes"] = data.get("recipes", patient["recipes"])
            patient["updated_at"] = datetime.now().isoformat()
            save_json(PATIENTS_FILE, patients_data)
            return JSONResponse({"success": True, "patient": patient})
    raise HTTPException(status_code=404, detail="Patient not found")

@app.post("/api/patients/{patient_id}/recipes")
async def add_recipe_to_patient(patient_id: str, request: Request):
    data = await request.json()
    patients_data = load_json(PATIENTS_FILE, {"patients": []})
    for patient in patients_data["patients"]:
        if patient["id"] == patient_id:
            recipe_id = data.get("recipe_id")
            if recipe_id and recipe_id not in patient.get("recipes", []):
                patient.setdefault("recipes", []).append(recipe_id)
                patient["updated_at"] = datetime.now().isoformat()
                save_json(PATIENTS_FILE, patients_data)
            return JSONResponse({"success": True, "patient": patient})
    raise HTTPException(status_code=404, detail="Patient not found")

@app.delete("/api/patients/{patient_id}")
async def delete_patient(patient_id: str):
    patients_data = load_json(PATIENTS_FILE, {"patients": []})
    patients_data["patients"] = [p for p in patients_data["patients"] if p["id"] != patient_id]
    save_json(PATIENTS_FILE, patients_data)
    return JSONResponse({"success": True})

# ─── Chat / Generate ───

async def auto_save_point(messages: list):
    for msg in messages:
        if msg.get("role") != "user":
            continue
        content = msg.get("content", "")
        has_point_cmd = re.search(r'(запомни|добавь|запиши|сохрани)\s*.{0,60}(точк|KI|LU|ST|HT|SI|PC|SJ|GB|LV|BL|GV|CV|SP|LI)', content, re.IGNORECASE)
        if not has_point_cmd:
            continue
        match = re.search(r'\b(ST|LU|LI|HT|SI|PC|SJ|GB|LV|KI|BL|GV|CV|EX)[ ]*([0-9]+[A-Za-z]*)\b', content, re.IGNORECASE)
        if not match:
            continue
        code = (match.group(1).upper() + match.group(2).upper()).replace(" ", "")
        # Try to extract name: "KI11 (Название)" or "KI11 — Название" or "KI11 Название"
        name = code
        name_match = re.search(r'[-(—–\s]([A-Za-zА-Яа-я].+?)(?:\)|\n|$|,)', content)
        if name_match:
            name = name_match.group(1).strip().rstrip(')')
        # Also try: "точка KI11 (Название)" 
        name_match2 = re.search(r'точ[кку]\s+\w+\s*\(([^)]+)\)', content)
        if name_match2:
            name = name_match2.group(1).strip()
        meridian_map = {"ST": "Stomach", "LU": "Lung", "LI": "Large Intestine", "HT": "Heart",
                       "SI": "Small Intestine", "PC": "Pericardium", "SJ": "Triple Burner",
                       "GB": "Gallbladder", "LV": "Liver", "KI": "Kidney", "BL": "Bladder",
                       "GV": "Governing Vessel", "CV": "Conception Vessel", "EX": "Extra"}
        points_data = load_json(POINTS_FILE, {"points": []})
        if not any(p.get("code") == code for p in points_data.get("points", [])):
            points_data.setdefault("points", []).append({
                "code": code, "name": name,
                "meridian": meridian_map.get(code[:2], "Unknown"),
                "location": "", "location_detail": "",
                "technique": "", "notes": "", "indications": [],
                "created_at": datetime.now().isoformat(), "source": "agent"
            })
            save_json(POINTS_FILE, points_data)

async def save_points_from_response(messages: list, response_text: str):
    """Parse AI response for point codes and save them to atlas"""
    if not response_text:
        return
    for m in reversed(messages):
        if m.get("role") == "user":
            user_text = m.get("content", "")
            break
    else:
        user_text = ""

    meridian_map = {"ST": "Stomach", "LU": "Lung", "LI": "Large Intestine", "HT": "Heart",
                   "SI": "Small Intestine", "PC": "Pericardium", "SJ": "Triple Burner",
                   "GB": "Gallbladder", "LV": "Liver", "KI": "Kidney", "BL": "Bladder",
                   "GV": "Governing Vessel", "CV": "Conception Vessel", "EX": "Extra"}

    for match in re.finditer(r'\b(ST|LU|LI|HT|SI|PC|SJ|GB|LV|KI|BL|GV|CV|EX)[ ]*([0-9]+[A-Za-z]*)\b', response_text, re.IGNORECASE):
        code = (match.group(1).upper() + match.group(2).upper()).replace(" ", "")
        points_data = load_json(POINTS_FILE, {"points": []})
        if any(p.get("code") == code for p in points_data.get("points", [])):
            continue
        name = code
        lines = response_text.split('\n')
        for i, line in enumerate(lines):
            if code.upper() in line.upper() and i + 1 < len(lines):
                nl = line.replace(code, "").strip().lstrip("(—– ").rstrip(")")
                if nl and len(nl) > 2:
                    name = nl.split(',')[0].strip()[:80]
                    break
        points_data.setdefault("points", []).append({
            "code": code, "name": name,
            "meridian": meridian_map.get(code[:2], "Unknown"),
            "location": user_text[:300], "location_detail": "",
            "technique": "", "notes": "", "indications": [],
            "created_at": datetime.now().isoformat(), "source": "agent"
        })
        save_json(POINTS_FILE, points_data)

def convert_openai_stream(line: str, provider: str) -> str:
    """Convert OpenAI streaming line to Ollama-compatible format for frontend."""
    try:
        data = json.loads(line)
        if "choices" in data and len(data["choices"]) > 0:
            delta = data["choices"][0].get("delta", {})
            content = delta.get("content", "")
            if content:
                return json.dumps({"message": {"content": content}}) + "\n"
    except json.JSONDecodeError:
        pass
    return ""

@app.post("/api/chat")
async def chat(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    messages = body.get("messages", [])
    model = body.get("model", "")
    stream = body.get("stream", True)
    provider_name = body.get("provider", ACTIVE_PROVIDER)
    provider = get_provider(provider_name)

    if not model:
        model = provider["default_model"]

    await auto_save_point(messages)

    # RAG: find relevant context from TCM PDFs
    rag_ctx = ""
    user_msgs = [m.get("content", "") for m in messages if m.get("role") == "user"]
    if user_msgs:
        try:
            rag_provider_url = PROVIDERS["ollama"]["base_url"]
            rag_results = await search_rag(user_msgs[-1], top_k=4, provider_url=rag_provider_url)
            if rag_results and len(rag_results) > 0:
                rag_ctx = "\n\n---\nДополнительные знания из TCM источников:\n" + "\n\n".join(
                    f"[{r['source']}]: {r['text'][:600]}" for r in rag_results
                )
        except Exception:
            rag_ctx = ""

    has_system = any(m.get("role") == "system" for m in messages)
    if not has_system:
        system_content = SYSTEM_PROMPT + (rag_ctx if rag_ctx else "")
        messages = [{"role": "system", "content": system_content}] + messages
    elif rag_ctx:
        messages[0]["content"] += rag_ctx

    ollama_body = {"model": model, "messages": messages, "stream": stream}
    openai_body = {"model": model, "messages": messages, "stream": stream, "max_tokens": 4096, "temperature": 1.0, "top_p": 0.95}

    chat_ep = provider["chat_endpoint"]
    req_body = ollama_body if provider["api_format"] == "ollama" else openai_body

    async def stream_response():
        full_text = ""
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", f"{provider['base_url']}{chat_ep}",
                json=req_body, headers=get_headers(provider)) as resp:
                if provider["api_format"] == "ollama":
                    async for chunk in resp.aiter_bytes():
                        decoded = chunk.decode()
                        try:
                            # Extract content from Ollama JSON chunk
                            chunk_data = json.loads(decoded)
                            content = chunk_data.get("message", {}).get("content", "")
                            full_text += content
                        except json.JSONDecodeError:
                            pass
                        yield chunk
                else:
                    buffer = ""
                    async for chunk in resp.aiter_bytes():
                        decoded = chunk.decode()
                        buffer += decoded
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if not line:
                                continue
                            if line.startswith("data: "):
                                payload = line[6:]
                                if payload.strip() == "[DONE]":
                                    continue
                                try:
                                    data = json.loads(payload)
                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            full_text += content
                                            yield json.dumps({"message": {"content": content}}).encode()
                                except json.JSONDecodeError:
                                    pass
        # After streaming completes, save points from the full response
        if full_text:
            await save_points_from_response(messages, full_text)

    if stream:
        return StreamingResponse(stream_response(), media_type="application/x-ndjson")
    else:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(f"{provider['base_url']}{chat_ep}",
                json=req_body, headers=get_headers(provider))
            if provider["api_format"] == "ollama":
                resp_data = res.json()
                reply = resp_data.get("message", {}).get("content", "")
                await save_points_from_response(messages, reply)
                return resp_data
            else:
                data = res.json()
                msg = data.get("choices", [{}])[0].get("message", {})
                reply = msg.get("content", "")
                await save_points_from_response(messages, reply)
                return {"message": msg}

@app.post("/api/generate")
async def generate(request: Request):
    body = await request.json()
    prompt = body.get("prompt", "")
    model = body.get("model", "")
    stream = body.get("stream", True)
    provider_name = body.get("provider", ACTIVE_PROVIDER)
    provider = get_provider(provider_name)

    if not model:
        model = provider["default_model"]

    if provider["api_format"] == "ollama":
        async def ollama_stream():
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream("POST", f"{provider['base_url']}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": True}) as resp:
                    async for chunk in resp.aiter_bytes():
                        yield chunk

        if stream:
            return StreamingResponse(ollama_stream(), media_type="application/x-ndjson")
        else:
            async with httpx.AsyncClient(timeout=120) as client:
                res = await client.post(f"{provider['base_url']}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False})
                return res.json()
    else:
        messages = [{"role": "user", "content": prompt}]
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(f"{provider['base_url']}{provider['chat_endpoint']}",
                json={"model": model, "messages": messages, "stream": False, "max_tokens": 4096},
                headers=get_headers(provider))
            data = res.json()
            return {"response": data.get("choices", [{}])[0].get("message", {}).get("content", "")}

# ─── Button trigger ───

@app.post("/api/buttons/{button_id}/trigger")
async def trigger_button(button_id: str):
    recipes_data = load_json(RECIPES_FILE, {"recipes": [], "custom_buttons": []})
    for btn in recipes_data.get("custom_buttons", []):
        if btn["id"] == button_id:
            return JSONResponse({"prompt": btn.get("prompt", "")})
    raise HTTPException(status_code=404, detail="Button not found")
