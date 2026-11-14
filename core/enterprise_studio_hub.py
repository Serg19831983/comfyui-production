import asyncio, json, os, sqlite3, subprocess, time, urllib.parse, urllib.request, uuid
from pathlib import Path
import uvicorn, websockets
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
COMFY_DIR, OUT_DIR, DB_PATH, FFMPEG_BIN = Path(r"C:\AI_Project\ComfyUI"), Path(r"C:\AI_Project\ComfyUI\output"), Path(r"C:\AI_Project\comfyui-production\data\studio_jobs.db"), Path(r"C:\AI_Project\bin\ffmpeg.exe")
H = "http" + "://127.0.0.1"
COMFY_HTTP, COMFY_WS, OLLAMA_URL, API_KEY = f"{H}:8188", "ws" + "://127.0.0.1:8188/ws", f"{H}:11434/api/generate", "EMPIRE-VIP-KEY-2026"
def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn: conn.execute("CREATE TABLE IF NOT EXISTS jobs (job_id TEXT PRIMARY KEY, mode TEXT, status TEXT, idea TEXT, enhanced_prompt TEXT, output_file TEXT, created_at INTEGER)")
def purge_vram():
    try: urllib.request.urlopen(urllib.request.Request(f"{COMFY_HTTP}/free", data=json.dumps({"unload_models": False, "free_memory": True}).encode(), headers={"Content-Type": "application/json"}, method="POST"), timeout=5)
    except Exception: pass
def enhance_prompt_ollama(idea: str, mode: str) -> str:
    sys_p = f"Translate and expand this {mode} idea into one vivid English prompt for AI generation (camera motion, lighting, lens, 8k photorealism). Output ONLY the prompt."
    for model in ["qwen2.5:14b", "gemma4:12b", "qwen3.5:4b", "llama3.2"]:
        try:
            req = urllib.request.Request(OLLAMA_URL, data=json.dumps({"model": model, "prompt": f"{sys_p}\nIdea: {idea}", "stream": False}).encode(), headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as r:
                res = json.loads(r.read().decode()).get("response", "").strip()
                if res: return res
        except Exception: continue
    return idea
def build_wan_t2v(prompt: str, prefix: str, frames: int = 81, fps: int = 24):
    return {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.1_t2v_1.3B_fp16.safetensors", "weight_dtype": "default"}}, "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan"}}, "3": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}}, "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}}, "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry, low quality, distorted, watermark, text, static, deformed", "clip": ["2", 0]}}, "6": {"class_type": "EmptyHunyuanLatentVideo", "inputs": {"width": 832, "height": 480, "length": frames, "batch_size": 1}}, "7": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0], "seed": int.from_bytes(os.urandom(4), "big"), "steps": 25, "cfg": 6.0, "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1.0}}, "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}}, "9": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["8", 0], "frame_rate": fps, "loop_count": 0, "filename_prefix": prefix, "format": "video/h264-mp4", "pix_fmt": "yuv420p", "crf": 16, "save_metadata": True, "save_output": True}}}
def build_flux_t2i(prompt: str, prefix: str):
    return {"1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "flux1-dev-Q4_K_S.gguf"}}, "2": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "t5xxl_fp8_e4m3fn.safetensors", "clip_name2": "clip_l.safetensors", "type": "flux"}}, "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}}, "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}}, "5": {"class_type": "EmptySD3LatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}}, "6": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["4", 0], "latent_image": ["5", 0], "seed": int.from_bytes(os.urandom(4), "big"), "steps": 20, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}}, "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}}, "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": prefix}}}
def postprocess_1080p_60fps(raw_mp4: Path) -> Path:
    if not FFMPEG_BIN.exists(): return raw_mp4
    hd_mp4 = raw_mp4.with_name(f"{raw_mp4.stem}_1080p60.mp4")
    subprocess.run([str(FFMPEG_BIN), "-y", "-i", str(raw_mp4), "-vf", "minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,scale=1920:1080:flags=lanczos,unsharp=5:5:0.8:3:3:0.4", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", str(hd_mp4)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return hd_mp4
async def process_job(job_id: str, idea: str, mode: str, upscale_60fps: bool):
    prompt = enhance_prompt_ollama(idea, mode)
    with sqlite3.connect(DB_PATH) as conn: conn.execute("UPDATE jobs SET status=?, enhanced_prompt=? WHERE job_id=?", ("rendering", prompt, job_id))
    cid = str(uuid.uuid4())
    graph = build_flux_t2i(prompt, f"Flux_{job_id}") if mode == "image" else build_wan_t2v(prompt, f"Video_{job_id}")
    async with websockets.connect(f"{COMFY_WS}?clientId={urllib.parse.quote(cid)}") as ws:
        req = urllib.request.Request(f"{COMFY_HTTP}/prompt", data=json.dumps({"prompt": graph, "client_id": cid}).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r: pid = json.loads(r.read().decode())["prompt_id"]
        while True:
            raw = await ws.recv()
            if isinstance(raw, bytes): continue
            msg = json.loads(raw)
            if msg.get("type") == "executing" and msg.get("data", {}).get("node") is None and msg.get("data", {}).get("prompt_id") == pid: break
    ext = "*.png" if mode == "image" else "*.mp4"
    pref = f"Flux_{job_id}" if mode == "image" else f"Video_{job_id}"
    files = sorted(OUT_DIR.rglob(f"{pref}{ext}"), key=lambda p: p.stat().st_mtime, reverse=True)
    final_path = postprocess_1080p_60fps(files[0]) if (files and mode == "video" and upscale_60fps) else (files[0] if files else Path(""))
    purge_vram()
    with sqlite3.connect(DB_PATH) as conn: conn.execute("UPDATE jobs SET status=?, output_file=? WHERE job_id=?", ("done", str(final_path), job_id))
app = FastAPI(title="ComfyUI Enterprise Production Hub", version="5.0.0")
class RenderOrder(BaseModel):
    idea: str
    mode: str = "video"
    upscale_1080p_60fps: bool = True
@app.get("/")
def root(): return {"status": "online", "gpu": "RTX 3060 12GB", "pipelines": ["Wan 2.1 T2V 1080p60", "Flux.1 Dev GGUF", "Qwen-Image"]}
@app.post("/v1/render")
async def create_render(order: RenderOrder, x_api_key: str = Header(default=API_KEY)):
    if x_api_key != API_KEY: raise HTTPException(status_code=401, detail="Invalid API Key")
    job_id = uuid.uuid4().hex[:8].upper()
    with sqlite3.connect(DB_PATH) as conn: conn.execute("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?)", (job_id, "queued", order.mode, order.idea, "", "", int(time.time())))
    asyncio.create_task(process_job(job_id, order.idea, order.mode, order.upscale_1080p_60fps))
    return {"ok": True, "job_id": job_id}
@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str):
    with sqlite3.connect(DB_PATH) as conn: row = conn.execute("SELECT job_id, mode, status, idea, enhanced_prompt, output_file FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if not row: raise HTTPException(status_code=404, detail="Not found")
    return {"job_id": row[0], "mode": row[1], "status": row[2], "idea": row[3], "prompt": row[4], "file": row[5]}
if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="127.0.0.1", port=9000)