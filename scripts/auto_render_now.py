import json, urllib.request, time, os, glob, subprocess
URL = "http://127.0.0.1:8188"
OUT_DIR = r"C:\AI_Project\ComfyUI\output"
prompt_api = {
    "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.1_t2v_1.3B_fp16.safetensors", "weight_dtype": "default"}},
    "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan"}},
    "3": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
    "4": {"class_type": "CLIPTextEncode", "inputs": {
        "text": "Cinematic tracking shot, observer perspective following stylish cyberpunk women walking down a neon-lit futuristic street at night, wearing futuristic mini-skirts, patterned tights, high boots, and glowing techwear jackets. Dynamic camera angle smoothly panning from low angle to medium shot, wet asphalt reflecting vibrant pink and cyan neon lights, rain mist, photorealistic, 8k, shot on 35mm lens.",
        "clip": ["2", 0]
    }},
    "5": {"class_type": "CLIPTextEncode", "inputs": {
        "text": "blurry, distorted, deformed, low quality, static, watermark, bad anatomy, extra limbs, morphing, flickering, overexposed, ugly",
        "clip": ["2", 0]
    }},
    "6": {"class_type": "EmptyHunyuanLatentVideo", "inputs": {"width": 832, "height": 480, "length": 81, "batch_size": 1}},
    "7": {"class_type": "KSampler", "inputs": {
        "model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0],
        "seed": int.from_bytes(os.urandom(4), "big"), "steps": 25, "cfg": 6.0,
        "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1.0
    }},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
    "9": {"class_type": "CreateVideo", "inputs": {"images": ["8", 0], "fps": 24.0}},
    "10": {"class_type": "SaveVideo", "inputs": {"video": ["9", 0], "filename_prefix": "Cyberpunk_Done", "format": "mp4", "codec": "h264"}}
}
# Проверка, запущен ли сервер, если нет - запускаем в фоне
try:
    urllib.request.urlopen(f"{URL}/system_stats", timeout=2)
except Exception:
    print("[1/3] Запуск движка ComfyUI...")
    env = os.environ.copy()
    env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    subprocess.Popen([r"C:\AI_Project\ComfyUI\venv\Scripts\python.exe", "main.py", "--listen", "127.0.0.1", "--port", "8188", "--reserve-vram", "1.5"], cwd=r"C:\AI_Project\ComfyUI", env=env)
    for _ in range(60):
        try:
            urllib.request.urlopen(f"{URL}/system_stats", timeout=2)
            break
        except Exception:
            time.sleep(1.5)
print("[2/3] Отправка задачи рендера на RTX 3060...")
req = urllib.request.Request(f"{URL}/prompt", data=json.dumps({"prompt": prompt_api}).encode("utf-8"), headers={"Content-Type": "application/json"})
res = json.loads(urllib.request.urlopen(req).read().decode())
pid = res["prompt_id"]
print(f"[3/3] Рендер запущен (ID: {pid}). Ждем завершения на видеокарте...")
while True:
    time.sleep(3)
    hist = json.loads(urllib.request.urlopen(f"{URL}/history/{pid}").read().decode())
    if pid in hist:
        status = hist[pid].get("status", {})
        if status.get("status_str") == "error":
            print("\n[ERROR] Ошибка ядра:", json.dumps(status, ensure_ascii=False))
            break
        print("\n[OK] ВИДЕО ГОТОВО! Открываю папку с результатом...")
        os.startfile(OUT_DIR)
        break