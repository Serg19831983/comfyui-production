import asyncio, json, os, shutil, sqlite3, subprocess, time, urllib.parse, urllib.request, uuid
from pathlib import Path
from typing import Dict, List, Optional
import uvicorn, websockets
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
COMFY_DIR  = Path(r"C:\AI_Project\ComfyUI")
OUT_DIR    = COMFY_DIR / "output"
DB_PATH    = Path(r"C:\AI_Project\comfyui-production\data\studio_jobs.db")
FFMPEG_BIN = Path(r"C:\AI_Project\bin\ffmpeg.exe")
COMFY_HTTP = "http://127.0.0.1:8188"
COMFY_WS   = "ws://127.0.0.1:8188/ws"
OLLAMA_URL = "http://127.0.0"
API_KEY    = "EMPIRE-VIP-KEY-2026"
def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            status TEXT,
            idea TEXT,
            enhanced_prompt TEXT,
            output_file TEXT,
            created_at INTEGER
        )""")
def get_gpu_telemetry() -> Dict[str, str]:
    try:
        raw = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
            text=True, timeout=3
        ).strip()
        name, temp, util, used, total = [x.strip() for x in raw.split(",")]
        return {"gpu": name, "temp_c": f"{temp}C", "load": f"{util}%", "vram": f"{used}/{total} MB"}
    except Exception as e:
        return {"error": str(e)}
def purge_vram():
    try:
        req = urllib.request.Request(f"{COMFY_HTTP}/free", data=json.dumps({"unload_models": False, "free_memory": True}).encode(), headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass
def enhance_prompt_ollama(idea: str) -> str:
    sys_prompt = "Translate and expand this video idea into one vivid English prompt for Wan 2.1 AI video generation (camera motion, lighting, lens, 4k photorealism). Output ONLY the prompt."
    for model in ["qwen2.5:14b", "gemma4:12b", "qwen3.5:4b"]:
        try:
            payload = json.dumps({"model": model, "prompt": f"{sys_prompt}\nIdea: {idea}", "stream": False, "options": {"temperature": 0.4}}).encode()
            req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                res = json.loads(r.read().decode()).get("response", "").strip()
                if res: return res
        except Exception:
            continue
    return idea
def build_wan_workflow(prompt: str, prefix: str, frames: int = 81, fps: int = 24):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.1_t2v_1.3B_fp16.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry, low quality, distorted, watermark, text, static, deformed", "clip": ["2", 0]}},
        "6": {"class_type": "EmptyHunyuanLatentVideo", "inputs": {"width": 832, "height": 480, "length": frames, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0], "seed": int.from_bytes(os.urandom(4), "big"), "steps": 25, "cfg": 6.0, "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["8", 0], "frame_rate": fps, "loop_count": 0, "filename_prefix": prefix, "format": "video/h264-mp4", "pix_fmt": "yuv420p", "crf": 16, "save_metadata": True, "save_output": True}}
    }
def postprocess_1080p_60fps(raw_mp4: Path) -> Path:
    if not FFMPEG_BIN.exists(): return raw_mp4
    hd_mp4 = raw_mp4.with_name(f"{raw_mp4.stem}_1080p60.mp4")
    cmd = [
        str(FFMPEG_BIN), "-y", "-i", str(raw_mp4),
        "-vf", "minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,scale=1920:1080:flags=lanczos,unsharp=5:5:0.8:3:3:0.4",
        "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", str(hd_mp4)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return hd_mp4
async def process_job(job_id: str, idea: str, upscale_60fps: bool = True):
    prompt = enhance_prompt_ollama(idea)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE jobs SET status=?, enhanced_prompt=? WHERE job_id=?", ("rendering", prompt, job_id))
    cid = str(uuid.uuid4())
    graph = build_wan_workflow(prompt, f"Studio_{job_id}")
    async with websockets.connect(f"{COMFY_WS}?clientId={urllib.parse.quote(cid)}") as ws:
        req = urllib.request.Request(f"{COMFY_HTTP}/prompt", data=json.dumps({"prompt": graph, "client_id": cid}).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            pid = json.loads(r.read().decode())["prompt_id"]
        while True:
            raw = await ws.recv()
            if isinstance(raw, bytes): continue
            msg = json.loads(raw)
            if msg.get("type") == "executing" and msg.get("data", {}).get("node") is None and msg.get("data", {}).get("prompt_id") == pid:
                break
    files = sorted(OUT_DIR.rglob(f"Studio_{job_id}*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    final_path = postprocess_1080p_60fps(files[0]) if (files and upscale_60fps) else (files[0] if files else Path(""))
    purge_vram()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE jobs SET status=?, output_file=? WHERE job_id=?", ("done", str(final_path), job_id))
app = FastAPI(title="ComfyUI Enterprise Video Studio", version="2.0.0")
class RenderOrder(BaseModel):
    idea: str
    upscale_1080p_60fps: bool = True
@app.get("/health")
def health():
    return {"status": "online", "gpu": get_gpu_telemetry()}
@app.post("/v1/render")
async def create_render(order: RenderOrder, x_api_key: str = Header(default=API_KEY)):
    if x_api_key != API_KEY: raise HTTPException(status_code=401, detail="Invalid API Key")
    job_id = uuid.uuid4().hex[:8].upper()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?)", (job_id, "queued", order.idea, "", "", int(time.time())))
    asyncio.create_task(process_job(job_id, order.idea, order.upscale_1080p_60fps))
    return {"ok": True, "job_id": job_id}
@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT job_id, status, idea, enhanced_prompt, output_file FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if not row: raise HTTPException(status_code=404, detail="Not found")
    return {"job_id": row[0], "status": row[1], "idea": row[2], "prompt": row[3], "file": row[4]}
if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=9000)