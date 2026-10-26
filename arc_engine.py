import os
import time
import subprocess
import requests
import random
import yt_dlp

# ==========================================
# 1. CONFIGURATION: DUAL TOKENS & ARC CTAs
# ==========================================
META_TOKENS = [
    os.getenv("META_TOKEN_1"),
    os.getenv("META_TOKEN_2")
]

GRAPH_API_VERSION = "v20.0"

# High-authority, zero-friction CTAs leading strictly to ARC via @arcbloodline30
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
        print("[INFO] No 'reel_links.txt' found. Using existing .mp4 files in assets/.")
        return

    with open(links_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not urls:
        print("[INFO] 'reel_links.txt' is empty. Using existing .mp4 files in assets/.")
        return

    print(f"[INFO] Downloading {len(urls)} hand-picked Reels from reel_links.txt...")

        ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": os.path.join(assets_dir, "curated_%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        }

    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(urls)
        print("[SUCCESS] Hand-picked Reels ingested into assets/.")
    except Exception as e:
        print(f"[WARNING] Some links could not be downloaded: {e}")

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
# 4. PRISTINE FFmpeg STEALTH MUTATION (NATURAL COLORS, ULTRA-CRISP)
# ==========================================
def mutate_video_for_account(input_path, output_path):
    print(f"[INFO] Mastering pristine quality & unique hash for {os.path.basename(input_path)}...")

    # Micro-adjustments: invisible to human eye, zero flashy/neon color shifts, 100% new file hash
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
        "ffmpeg", "-y", "-i", input_path,
        "-vf", vf_chain,
        "-af", f"atempo={speed}",
        "-c:v", "libx264", "-crf", "17", "-preset", "slow",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "192k",
        "-map_metadata", "-1",
        output_path
    ]

    result = subprocess.run(cmd_with_audio, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        # Fallback if source clip has no audio track
        cmd_video_only = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", vf_chain,
            "-c:v", "libx264", "-crf", "17", "-preset", "slow",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-an", "-map_metadata", "-1",
            output_path
        ]
        res2 = subprocess.run(cmd_video_only, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res2.returncode != 0:
            raise Exception(f"FFmpeg failed: {res2.stderr.decode('utf-8', errors='ignore')}")

    return output_path

# ==========================================
# 5. DUAL-HOST GHOST BUCKET RELAY (ZERO CARD REQUIRED)
# ==========================================
def upload_for_meta_download(file_path):
    print("[INFO] Uploading mastered Reel to temporary ghost relay...")

    # Primary Relay: Litterbox (1-hour direct MP4 link)
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
            print(f"[INFO] Relay #1 URL ready: {direct_url}")
            return direct_url
    except Exception as e:
        print(f"[WARNING] Primary relay hiccup ({e}), switching to backup relay...")

    # Backup Relay: tmpfiles.org
    with open(file_path, "rb") as f:
        response = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=60).json()

    if "data" not in response or "url" not in response["data"]:
        raise Exception(f"Both ghost relays failed: {response}")

    viewer_url = response["data"]["url"]
    direct_url = viewer_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
    print(f"[INFO] Relay #2 URL ready: {direct_url}")
    return direct_url

# ==========================================
# 6. META GRAPH API REEL PUBLISHER
# ==========================================
def publish_reel_to_instagram(ig_user_id, video_url, caption, token):
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

    for attempt in range(25):
        status_res = requests.get(
            status_url,
            params={"fields": "status_code,status", "access_token": token},
            timeout=30
        ).json()
        status_code = status_res.get("status_code")
        print(f"[INFO] Meta processing [{attempt+1}/25]: {status_code}")

        if status_code == "FINISHED":
            break
        elif status_code in ("ERROR", "EXPIRED"):
            raise Exception(f"Meta rejected video: {status_res}")
        time.sleep(20)
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

    print(f"[SUCCESS] Live on Instagram! Media ID: {publish_res['id']}")

# ==========================================
# 7. MAIN ENGINE EXECUTION
# ==========================================
def main():
    active_tokens = [t.strip() for t in META_TOKENS if t and t.strip()]
    if not active_tokens:
        raise ValueError("FATAL: Add META_TOKEN_1 (and META_TOKEN_2) in GitHub Actions Secrets.")

    # Step A: Pull any curated IG links from reel_links.txt
    ingest_curated_reels()

    assets_dir = "assets"
    raw_videos = [f for f in os.listdir(assets_dir) if f.lower().endswith(".mp4")]
    if not raw_videos:
        raise FileNotFoundError(
            "No .mp4 videos available! Paste Instagram Reel URLs into 'reel_links.txt' or upload .mp4 files into 'assets/'."
        )

    # Step B: Discover all linked IG accounts across both tokens
    all_accounts = []
    seen_ig_ids = set()
    for idx, token in enumerate(active_tokens):
        try:
            accs = get_connected_instagram_accounts(token)
            print(f"[INFO] Token #{idx+1}: Found {len(accs)} connected Instagram accounts.")
            for a in accs:
                if a["ig_user_id"] not in seen_ig_ids:
                    seen_ig_ids.add(a["ig_user_id"])
                    all_accounts.append(a)
        except Exception as e:
            print(f"[ERROR] Token #{idx+1} lookup failed: {e}")

    if not all_accounts:
        raise RuntimeError("Zero Instagram Business accounts found across your tokens.")

    print(f"[INFO] Starting deployment across {len(all_accounts)} accounts using {len(raw_videos)} curated clips.")

    # Shuffle videos so accounts don't pick the same clip in the same order
    shuffled_pool = random.sample(raw_videos, len(raw_videos))

    # Step C: Mutate and publish 1 unique Reel per account for this run
    for index, acc in enumerate(all_accounts):
        print(f"\n----------------------------------------")
        print(f"[NODE {index+1}/{len(all_accounts)}] {acc['page_name']} (IG ID: {acc['ig_user_id']})")
        print(f"----------------------------------------")

        video_choice = shuffled_pool[index % len(shuffled_pool)]
        selected_video = os.path.join(assets_dir, video_choice)
        mutated_output = f"arc_master_{index}.mp4"
        caption = random.choice(ARC_CTAS)

        try:
            mutate_video_for_account(selected_video, mutated_output)
            public_url = upload_for_meta_download(mutated_output)
            publish_reel_to_instagram(acc["ig_user_id"], public_url, caption, acc["token"])
        except Exception as e:
            print(f"[ERROR] Failed on {acc['page_name']}: {e}")
        finally:
            if os.path.exists(mutated_output):
                os.remove(mutated_output)

        if index < len(all_accounts) - 1:
            jitter = random.randint(25, 45)
            print(f"[SAFE JITTER] Pausing {jitter}s before next account...")
            time.sleep(jitter)

if __name__ == "__main__":
    main()
  
