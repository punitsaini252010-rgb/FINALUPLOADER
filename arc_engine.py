import os
import sys
import time
import subprocess
import requests
import random
import yt_dlp

def log(msg):
    print(msg, flush=True)

# ==========================================
# 1. CONFIGURATION: DUAL TOKENS & ARC CTAs
# ==========================================
META_TOKENS = [
    os.getenv("META_TOKEN_1"),
    os.getenv("META_TOKEN_2")
]

GRAPH_API_VERSION = "v20.0"

ARC_CTAS = [
    "⏳ 80 years on this Earth. Don’t waste 50 in a cubicle making another man rich.\n\n🔓 First 1,000 spots inside the ARC Private Terminal + Starter Kit are FREE (Locks at #1,000).\n🗝️ Enter the ARC via @arcbloodline30 (Link in bio) ↓",
    "🌍 Real wealth is total freedom, sovereignty, and owning every second of your bloodline.\n\n🔓 Claim your free ARC Terminal + First $100 Starter Kit before the first 1,000 spots lock.\n♟️ Step out of the matrix via @arcbloodline30 (Link in bio) ↓",
    "⚡ They want you sedated on brainrot while your life slips away. Build your own empire instead.\n\n🔓 Private ARC Vault is open FREE for the first 1,000 builders.\n🗝️ Secure your terminal access via @arcbloodline30 (Link in bio) ↓"
]

# ==========================================
# 2. INGEST HAND-PICKED REELS FROM reel_links.txt
# ==========================================
def ingest_curated_reels():
    assets_dir = "assets"
    os.makedirs(assets_dir, exist_ok=True)

    links_file = "reel_links.txt"
    if not os.path.exists(links_file):
        log("[INFO] No 'reel_links.txt' found. Using existing .mp4 files in assets/.")
        return

    with open(links_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not urls:
        log("[INFO] 'reel_links.txt' is empty. Using existing .mp4 files in assets/.")
        return

    log(f"[INFO] Downloading {len(urls)} hand-picked Reels from reel_links.txt...")

    ydl_opts = {
        "format": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
        "outtmpl": os.path.join(assets_dir, "curated_%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "quiet": False,
        "no_warnings": True,
        "ignoreerrors": True,
        "socket_timeout": 30,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(urls)
        log("[SUCCESS] Hand-picked Reels downloaded into assets/.")
    except Exception as e:
        log(f"[WARNING] Download warning: {e}")

# ==========================================
# 3. DISCOVER ALL CONNECTED IG ACCOUNTS
# ==========================================
def get_connected_instagram_accounts(token):
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/accounts"
    params = {
        "fields": "id,name,instagram_business_account",
        "limit": 100,
        "access_token": token
    }
    response = requests.get(url, params=params, timeout=30).json()
    if "error" in response:
        raise Exception(f"Token error: {response['error'].get('message')}")

    accounts = []
    for page in response.get("data", []):
        ig_biz = page.get("instagram_business_account")
        if ig_biz and "id" in ig_biz:
            accounts.append({
                "page_name": page.get("name", "ARC_Node"),
                "ig_user_id": ig_biz["id"],
                "token": token
            })
    return accounts

# ==========================================
# 4. NON-BLOCKING FFmpeg STEALTH MASTERING
# ==========================================
def mutate_video_for_account(input_path, output_path):
    log(f"[INFO] Running FFmpeg stealth mastering on {os.path.basename(input_path)}...")

    b_shift = round(random.uniform(0.001, 0.006), 4)
    s_shift = round(random.uniform(1.002, 1.012), 4)
    speed = round(random.uniform(1.01, 1.03), 3)

    vf_chain = (
        f"setpts=PTS/{speed},"
        f"eq=brightness={b_shift}:saturation={s_shift},"
        f"scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop=1080:1920,"
        f"unsharp=3:3:0.45:3:3:0.0"
    )

    cmd_with_audio = [
        "ffmpeg", "-nostdin", "-y", "-i", input_path,
        "-vf", vf_chain,
        "-af", f"atempo={speed}",
        "-c:v", "libx264", "-crf", "17", "-preset", "veryfast",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "192k",
        "-map_metadata", "-1",
        output_path
    ]

    result = subprocess.run(
        cmd_with_audio,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=180
    )

    if result.returncode != 0:
        log("[INFO] Retrying FFmpeg in video-only stream mode...")
        cmd_video_only = [
            "ffmpeg", "-nostdin", "-y", "-i", input_path,
            "-vf", vf_chain,
            "-c:v", "libx264", "-crf", "17", "-preset", "veryfast",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-an", "-map_metadata", "-1",
            output_path
        ]
        res2 = subprocess.run(
            cmd_video_only,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180
        )
        if res2.returncode != 0:
            raise Exception(f"FFmpeg failed: {res2.stderr.decode('utf-8', errors='ignore')[-400:]}")

    log(f"[SUCCESS] FFmpeg mastering complete: {output_path}")
    return output_path

# ==========================================
# 5. DUAL-HOST GHOST BUCKET RELAY
# ==========================================
def upload_for_meta_download(file_path):
    log("[INFO] Uploading mastered Reel to temporary ghost relay...")

    try:
        with open(file_path, "rb") as f:
            res = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "1h"},
                files={"fileToUpload": f},
                timeout=60
            )
        if res.status_code == 200 and res.text.strip().startswith("https://"):
            direct_url = res.text.strip()
            log(f"[SUCCESS] Ghost Relay #1 URL ready: {direct_url}")
            return direct_url
    except Exception as e:
        log(f"[WARNING] Primary relay hiccup ({e}), switching to backup relay...")

    with open(file_path, "rb") as f:
        response = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=60).json()

    if "data" not in response or "url" not in response["data"]:
        raise Exception(f"Both ghost relays failed: {response}")

    viewer_url = response["data"]["url"]
    direct_url = viewer_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
    log(f"[SUCCESS] Ghost Relay #2 URL ready: {direct_url}")
    return direct_url

# ==========================================
# 6. META GRAPH API REEL PUBLISHER
# ==========================================
def publish_reel_to_instagram(ig_user_id, video_url, caption, token):
    log(f"[INFO] Creating Meta Reel container for IG ID {ig_user_id}...")
    container_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": token
    }
    res = requests.post(container_url, data=payload, timeout=30).json()
    if "id" not in res:
        raise Exception(f"Container creation failed: {res}")

    creation_id = res["id"]
    status_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{creation_id}"

    for attempt in range(20):
        status_res = requests.get(
            status_url,
            params={"fields": "status_code,status", "access_token": token},
            timeout=30
        ).json()
        status_code = status_res.get("status_code")
        log(f"[INFO] Meta processing [{attempt+1}/20]: {status_code}")

        if status_code == "FINISHED":
            break
        elif status_code in ("ERROR", "EXPIRED"):
            raise Exception(f"Meta rejected video: {status_res}")
        time.sleep(15)
    else:
        raise Exception("Meta video processing timed out.")

    publish_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}/media_publish"
    publish_res = requests.post(
        publish_url,
        data={"creation_id": creation_id, "access_token": token},
        timeout=30
    ).json()

    if "id" not in publish_res:
        raise Exception(f"Publish step failed: {publish_res}")

    log(f"[SUCCESS] LIVE ON INSTAGRAM! Media ID: {publish_res['id']}")

# ==========================================
# 7. MAIN ENGINE EXECUTION
# ==========================================
def main():
    log("[START] Initializing ARC Publishing Engine...")
    active_tokens = [t.strip() for t in META_TOKENS if t and t.strip()]
    if not active_tokens:
        raise ValueError("FATAL: Add META_TOKEN_1 (and META_TOKEN_2) in GitHub Actions Secrets.")

    ingest_curated_reels()

    assets_dir = "assets"
    raw_videos = [f for f in os.listdir(assets_dir) if f.lower().endswith(".mp4")]
    log(f"[INFO] Found {len(raw_videos)} ready .mp4 files in assets/: {raw_videos}")
    if not raw_videos:
        raise FileNotFoundError("No .mp4 videos found after ingestion!")

    all_accounts = []
    seen_ig_ids = set()
    for idx, token in enumerate(active_tokens):
        try:
            log(f"[INFO] Scanning Token #{idx+1} for connected Instagram accounts...")
            accs = get_connected_instagram_accounts(token)
            log(f"[INFO] Token #{idx+1}: Found {len(accs)} connected Instagram accounts.")
            for a in accs:
                if a["ig_user_id"] not in seen_ig_ids:
                    seen_ig_ids.add(a["ig_user_id"])
                    all_accounts.append(a)
        except Exception as e:
            log(f"[ERROR] Token #{idx+1} lookup failed: {e}")

    if not all_accounts:
        raise RuntimeError("Zero Instagram Business accounts found across your tokens.")

    log(f"[INFO] Deploying across {len(all_accounts)} accounts...")
    shuffled_pool = random.sample(raw_videos, len(raw_videos))

    for index, acc in enumerate(all_accounts):
        log(f"\n----------------------------------------")
        log(f"[NODE {index+1}/{len(all_accounts)}] {acc['page_name']} (IG ID: {acc['ig_user_id']})")
        log(f"----------------------------------------")

        video_choice = shuffled_pool[index % len(shuffled_pool)]
        selected_video = os.path.join(assets_dir, video_choice)
        mutated_output = f"arc_master_{index}.mp4"
        caption = random.choice(ARC_CTAS)

        try:
            mutate_video_for_account(selected_video, mutated_output)
            public_url = upload_for_meta_download(mutated_output)
            publish_reel_to_instagram(acc["ig_user_id"], public_url, caption, acc["token"])
        except Exception as e:
            log(f"[ERROR] Failed on {acc['page_name']}: {e}")
        finally:
            if os.path.exists(mutated_output):
                os.remove(mutated_output)

        if index < len(all_accounts) - 1:
            jitter = random.randint(20, 35)
            log(f"[SAFE JITTER] Pausing {jitter}s before next account...")
            time.sleep(jitter)

    log("\n[COMPLETE] All accounts processed successfully!")

if __name__ == "__main__":
    main()
                
