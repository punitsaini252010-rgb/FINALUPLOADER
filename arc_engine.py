import os
import sys
import time
import subprocess
import requests
import random
import yt_dlp

# Force real-time unbuffered output on GitHub Actions so logs never freeze
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# ==========================================
# 1. CONFIGURATION & 55 UNIQUE 1-CLICK CAPTIONS
# ==========================================
META_TOKENS = [
    os.getenv("META_TOKEN_1"),
    os.getenv("META_TOKEN_2")
]

GRAPH_API_VERSION = "v20.0"

LINKS_FILE = "reel_links.txt"
HISTORY_FILE = "posted_history.txt"
ASSETS_DIR = "assets"
CUSTOM_FONT_PATH = "Montserrat-ExtraBold.ttf"

# US/UK Tier-1 Peak Schedule Reference Map (UTC Hour -> Target Market Window)
TIER1_SCHEDULE_MAP = {
    1: "US East Prime (8:30 PM EST) | Texas (7:30 PM CST) | US West (5:30 PM PST)",
    3: "US West Prime (7:30 PM PST) | US East Late Night (10:30 PM EST)",
    5: "US West Late Impulse (9:30 PM PST) | Australia Post-Work (4:30 PM AEDT)",
    7: "UK Morning Wake-Up (7:30 AM GMT) | Australia Prime (6:30 PM AEDT)",
    10: "UK Mid-Morning (10:00 AM GMT) | Singapore Post-Work (6:00 PM SGT) | Aus Night",
    12: "UK Lunch Peak (12:00 PM GMT) | US East Wake-Up (7:00 AM EST) | Singapore Prime",
    14: "US East Morning (9:30 AM EST) | UK Afternoon (2:30 PM GMT) | Dubai Evening",
    17: "UK Post-Work Peak (5:00 PM GMT) | US East Lunch (12:00 PM EST) | Dubai Prime",
    19: "UK Evening Prime (7:30 PM GMT) | Europe Prime (8:30 PM CET) | US Afternoon",
    21: "UK Late Impulse (9:30 PM GMT) | US East Work Exit (4:30 PM EST) | Europe Night",
    23: "US East Dinner Prime (6:30 PM EST) | Texas (5:30 PM CST) | UK Midnight"
}

# 55 Short, Single-Line Captions — "@ARCBLOODLINE30" is always Word #1 in CAPS.
ARC_BASE_CAPTIONS = [
    "@ARCBLOODLINE30 Keep scrolling loser or enter ARC.",
    "@ARCBLOODLINE30 Enter ARC and make real money now.",
    "@ARCBLOODLINE30 Stop watching others win. Lock in.",
    "@ARCBLOODLINE30 Scroll back to broke or enter ARC.",
    "@ARCBLOODLINE30 Your only exit out of the matrix.",
    "@ARCBLOODLINE30 Die average or build your empire.",
    "@ARCBLOODLINE30 Weak minds scroll. Winners enter.",
    "@ARCBLOODLINE30 Stop living like a slave. Join us.",
    "@ARCBLOODLINE30 Break the bloodline curse inside.",
    "@ARCBLOODLINE30 Nobody is coming to save you. Act.",
    "@ARCBLOODLINE30 Escape the 9-5 cage right now.",
    "@ARCBLOODLINE30 First 1,000 terminal spots FREE.",
    "@ARCBLOODLINE30 Claim your free ARC Starter Kit.",
    "@ARCBLOODLINE30 The 99% scroll. The 1% lock in.",
    "@ARCBLOODLINE30 Own your life or stay owned.",
    "@ARCBLOODLINE30 Stop wasting years in a cubicle.",
    "@ARCBLOODLINE30 Real wealth starts inside the ARC.",
    "@ARCBLOODLINE30 Swipe to stay broke or enter now.",
    "@ARCBLOODLINE30 Unlock the private ARC terminal.",
    "@ARCBLOODLINE30 Build your fortune inside ARC.",
    "@ARCBLOODLINE30 Spectators scroll. Builders enter.",
    "@ARCBLOODLINE30 Zero excuses left. Enter the ARC.",
    "@ARCBLOODLINE30 Make money or keep making excuses.",
    "@ARCBLOODLINE30 Step out of the herd right now.",
    "@ARCBLOODLINE30 Gates lock at member #1,000.",
    "@ARCBLOODLINE30 Secure your bloodline inside ARC.",
    "@ARCBLOODLINE30 Stop working to make another rich.",
    "@ARCBLOODLINE30 Total sovereignty starts right here.",
    "@ARCBLOODLINE30 Pawns keep scrolling. Kings enter.",
    "@ARCBLOODLINE30 Change your reality inside ARC.",
    "@ARCBLOODLINE30 Free ARC Vault access in bio.",
    "@ARCBLOODLINE30 Don't wake up broke again tomorrow.",
    "@ARCBLOODLINE30 Trade brainrot for real cashflow.",
    "@ARCBLOODLINE30 Every scroll costs you your future.",
    "@ARCBLOODLINE30 Lock into the ARC system today.",
    "@ARCBLOODLINE30 Take command of your income now.",
    "@ARCBLOODLINE30 Leave the broke mindset behind.",
    "@ARCBLOODLINE30 Your bloodline depends on this move.",
    "@ARCBLOODLINE30 Stop spectating luxury. Live it.",
    "@ARCBLOODLINE30 Access the $100 Starter Kit free.",
    "@ARCBLOODLINE30 Losers swipe up. Winners tap here.",
    "@ARCBLOODLINE30 The system wants you broke. Rebel.",
    "@ARCBLOODLINE30 Enter the vault and print money.",
    "@ARCBLOODLINE30 Power and freedom live inside ARC.",
    "@ARCBLOODLINE30 Refuse to die average. Enter now.",
    "@ARCBLOODLINE30 One click separates you from broke.",
    "@ARCBLOODLINE30 Stop begging for a paycheck. Build.",
    "@ARCBLOODLINE30 Outwork everyone inside the ARC.",
    "@ARCBLOODLINE30 Turn your ambition into pure cash.",
    "@ARCBLOODLINE30 Stop scrolling your youth away.",
    "@ARCBLOODLINE30 Claim your seat inside ARC free.",
    "@ARCBLOODLINE30 Only builders survive. Enter ARC.",
    "@ARCBLOODLINE30 Kill complacency. Enter the vault.",
    "@ARCBLOODLINE30 Rewrite your family tree inside.",
    "@ARCBLOODLINE30 Tap now or stay trapped forever."
]

def generate_unique_caption_batch(count):
    pool = list(ARC_BASE_CAPTIONS)
    random.shuffle(pool)
    micro_tags = ["", " ↓", " ⚡", " 🗝️", " 🔓", " ♟️"]
    selected = []
    for i in range(count):
        base = pool[i % len(pool)]
        suffix = random.choice(micro_tags)
        caption = f"{base}{suffix}".strip()
        selected.append(caption)
    return selected

# ==========================================
# 2. CUSTOM FONT AUTO-LOADER
# ==========================================
def ensure_custom_font():
    if os.path.exists(CUSTOM_FONT_PATH) and os.path.getsize(CUSTOM_FONT_PATH) > 10000:
        return CUSTOM_FONT_PATH

    font_url = "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf"
    try:
        log("[INFO] Downloading clean custom font (Montserrat-ExtraBold)...")
        res = requests.get(font_url, timeout=(10, 20))
        if res.status_code == 200 and len(res.content) > 10000:
            with open(CUSTOM_FONT_PATH, "wb") as f:
                f.write(res.content)
            log("[SUCCESS] Custom font Montserrat-ExtraBold loaded.")
            return CUSTOM_FONT_PATH
    except Exception as e:
        log(f"[WARNING] Custom font download skipped ({e}), using system bold font.")

    fallback = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    return fallback

# ==========================================
# 3. PERMANENT DEDUPLICATION & INGESTION
# ==========================================
def load_posted_history():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def mark_as_posted(identifier):
    if not identifier:
        return
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{identifier.strip()}\n")

def remove_link_from_queue(used_url):
    if not used_url or not os.path.exists(LINKS_FILE):
        return
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            if line.strip() != used_url.strip():
                f.write(line)

def ingest_single_fresh_reel(posted_history):
    os.makedirs(ASSETS_DIR, exist_ok=True)

    for existing in os.listdir(ASSETS_DIR):
        if existing.lower().endswith(".mp4") and existing in posted_history:
            try:
                os.remove(os.path.join(ASSETS_DIR, existing))
            except Exception:
                pass

    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, "r", encoding="utf-8") as f:
            all_urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        fresh_urls = [u for u in all_urls if u not in posted_history]

        for target_url in fresh_urls:
            log(f"[STEP 1/4] Downloading fresh unposted Reel: {target_url}")
            ydl_opts = {
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "outtmpl": os.path.join(ASSETS_DIR, "curated_%(id)s.%(ext)s"),
                "merge_output_format": "mp4",
                "quiet": True,
                "no_warnings": True,
                "ignoreerrors": False,
                "socket_timeout": 25,
                "http_headers": {
                    "Accept-Language": "en-US,en;q=0.9"
                }
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(target_url, download=True)
                    vid_id = info.get("id", "unknown")
                    downloaded_file = f"curated_{vid_id}.mp4"
                    full_path = os.path.join(ASSETS_DIR, downloaded_file)

                    if downloaded_file in posted_history:
                        log(f"[SKIP] Video ID {downloaded_file} was already posted. Removing link...")
                        mark_as_posted(target_url)
                        remove_link_from_queue(target_url)
                        if os.path.exists(full_path):
                            os.remove(full_path)
                        continue

                    if os.path.exists(full_path):
                        log(f"[SUCCESS] Fresh Reel downloaded: {downloaded_file}")
                        return full_path, target_url, downloaded_file
            except Exception as e:
                log(f"[WARNING] Link failed ({target_url}): {e}. Removing broken link...")
                mark_as_posted(target_url)
                remove_link_from_queue(target_url)

    unposted_local = [
        f for f in os.listdir(ASSETS_DIR)
        if f.lower().endswith(".mp4") and f not in posted_history
    ]
    if unposted_local:
        chosen = unposted_local[0]
        return os.path.join(ASSETS_DIR, chosen), None, chosen

    return None, None, None

# ==========================================
# 4. DISCOVER ALL CONNECTED IG ACCOUNTS
# ==========================================
def get_connected_instagram_accounts(token):
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/accounts"
    params = {
        "fields": "id,name,instagram_business_account",
        "limit": 100,
        "access_token": token
    }
    response = requests.get(url, params=params, timeout=(10, 20)).json()
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
# 5. HEAVY STEALTH 4K + UPPER-CENTER WATERMARK + END-CARD
# ==========================================
def get_video_duration(input_path):
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            input_path
        ]
        res = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        return float(res.stdout.decode("utf-8").strip())
    except Exception:
        return 10.0

def mutate_video_for_account(input_path, output_path, font_path):
    log(f"[STEP 2/4] Heavy Stealth 4K Mastering + Upper-Center Watermark + End-Card ({os.path.basename(input_path)})...")

    # Shave 0.12s - 0.55s off start so every account has unique keyframe timestamps
    trim_start = round(random.uniform(0.12, 0.55), 3)

    # Subtle spatial, rotation, flip & color shifts to bypass Meta vPDQ duplicate hash
    crop_keep = round(random.uniform(0.975, 0.992), 4)
    x_jitter = random.randint(2, 6)
    y_jitter = random.randint(2, 6)
    angle_deg = random.choice([-0.35, -0.25, 0.25, 0.35])
    flip_filter = "hflip," if random.random() < 0.5 else ""
    noise_level = random.randint(2, 3)

    b_shift = round(random.uniform(-0.006, 0.006), 4)
    c_shift = round(random.uniform(0.994, 1.010), 4)
    s_shift = round(random.uniform(0.992, 1.014), 4)
    g_shift = round(random.uniform(0.992, 1.008), 4)
    speed = round(random.uniform(0.982, 1.028), 4)

    # Audio pitch + EQ + tempo shift to break audio spectrogram matching
    pitch_shift = round(random.uniform(0.980, 1.022), 4)
    tempo_comp = round(speed / pitch_shift, 4)
    tempo_comp = max(0.5, min(2.0, tempo_comp))
    eq_gain = random.choice([-2, -1, 1, 2])
    vol_shift = round(random.uniform(0.985, 1.025), 3)
    epoch_jitter = int(time.time()) - random.randint(300, 172800)

    raw_duration = get_video_duration(input_path)
    effective_raw = max(3.5, raw_duration - trim_start)
    final_duration = effective_raw / speed
    cta_start = round(max(1.5, final_duration - 2.4), 2)

    line1 = "KEEP SCROLLING LOSER"
    line2 = "OR ENTER ARC AND MAKE MONEY"

    # Upper-center large ARC watermark position with micro-pixel jitter per account
    wm_x_offset = random.randint(-6, 6)
    wm_y = 340 + random.randint(-8, 8)

    vf_chain = (
        f"setpts=PTS/{speed},"
        f"{flip_filter}"
        f"rotate={angle_deg}*PI/180:bilinear=1:fillcolor=black,"
        f"crop=iw*{crop_keep}:ih*{crop_keep}:(iw-ow)/2+{x_jitter}:(ih-oh)/2+{y_jitter},"
        f"scale=2160:3840:force_original_aspect_ratio=increase:flags=lanczos+accurate_rnd+full_chroma_int,"
        f"crop=2160:3840,"
        f"eq=brightness={b_shift}:contrast={c_shift}:saturation={s_shift}:gamma={g_shift},"
        f"noise=alls={noise_level}:allf=t,"
        f"unsharp=5:5:0.34:5:5:0.0,"
        f"drawtext=fontfile={font_path}:text='ARC':expansion=none:"
        f"fontcolor=white@0.32:fontsize=130:shadowcolor=black@0.25:shadowx=3:shadowy=3:"
        f"x=(w-text_w)/2+{wm_x_offset}:y={wm_y},"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.82:t=fill:enable='gte(t,{cta_start})',"
        f"drawtext=fontfile={font_path}:text='{line1}':expansion=none:"
        f"fontcolor=0xFFD700:fontsize=92:shadowcolor=black@0.9:shadowx=4:shadowy=4:"
        f"x=(w-text_w)/2:y=(h/2)-95:enable='gte(t,{cta_start})',"
        f"drawtext=fontfile={font_path}:text='{line2}':expansion=none:"
        f"fontcolor=white:fontsize=74:"
        f"box=1:boxcolor=black@0.92:boxborderw=34:"
        f"x=(w-text_w)/2:y=(h/2)+35:enable='gte(t,{cta_start})'"
    )

    af_chain = (
        f"asetrate=48000*{pitch_shift},"
        f"aresample=48000,"
        f"atempo={tempo_comp},"
        f"equalizer=f=1000:width_type=h:width=200:g={eq_gain},"
        f"volume={vol_shift}"
    )

    crf_val = str(random.choice([21, 22, 23]))

    cmd_with_audio = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", str(trim_start),
        "-i", input_path,
        "-vf", vf_chain,
        "-af", af_chain,
        "-c:v", "libx264", "-profile:v", "high", "-level:v", "5.1",
        "-crf", crf_val, "-preset", "veryfast",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-metadata:s:a:0", "language=eng",
        "-map_metadata", "-1",
        "-metadata", f"creation_time={epoch_jitter}",
        output_path
    ]

    result = subprocess.run(cmd_with_audio, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=240)

    if result.returncode != 0:
        cmd_video_only = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", str(trim_start),
            "-i", input_path,
            "-vf", vf_chain,
            "-c:v", "libx264", "-profile:v", "high", "-level:v", "5.1",
            "-crf", crf_val, "-preset", "veryfast",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-an", "-map_metadata", "-1",
            "-metadata", f"creation_time={epoch_jitter}",
            output_path
        ]
        res2 = subprocess.run(cmd_video_only, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=240)
        if res2.returncode != 0:
            raise Exception(f"FFmpeg failed: {res2.stderr.decode('utf-8', errors='ignore')}")

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    log(f"[SUCCESS] Heavy Stealth 4K Master finished ({size_mb:.2f} MB).")
    return output_path

# ==========================================
# 6. 4-RELAY GHOST UPLOAD
# ==========================================
def upload_for_meta_download(file_path):
    log("[STEP 3/4] Uploading 4K Master Reel to temporary ghost relay...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        log(" -> Trying Relay #1 (Uguu CDN)...")
        with open(file_path, "rb") as f:
            res = requests.post("https://uguu.se/upload", files={"files[]": f}, headers=headers, timeout=(15, 75)).json()
        if res.get("success") and res.get("files"):
            url = res["files"][0]["url"]
            log(f"[SUCCESS] Relay #1 URL ready: {url}")
            return url
    except Exception as e:
        log(f" -> Relay #1 skipped ({e})")

    try:
        log(" -> Trying Relay #2 (Catbox CDN)...")
        with open(file_path, "rb") as f:
            res = requests.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload"}, files={"fileToUpload": f}, headers=headers, timeout=(15, 75))
        if res.status_code == 200 and res.text.strip().startswith("https://"):
            url = res.text.strip()
            log(f"[SUCCESS] Relay #2 URL ready: {url}")
            return url
    except Exception as e:
        log(f" -> Relay #2 skipped ({e})")

    try:
        log(" -> Trying Relay #3 (Litterbox CDN)...")
        with open(file_path, "rb") as f:
            res = requests.post("https://litterbox.catbox.moe/resources/internals/api.php", data={"reqtype": "fileupload", "time": "1h"}, files={"fileToUpload": f}, headers=headers, timeout=(15, 75))
        if res.status_code == 200 and res.text.strip().startswith("https://"):
            url = res.text.strip()
            log(f"[SUCCESS] Relay #3 URL ready: {url}")
            return url
    except Exception as e:
        log(f" -> Relay #3 skipped ({e})")

    log(" -> Trying Relay #4 (Tmpfiles CDN)...")
    with open(file_path, "rb") as f:
        response = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, headers=headers, timeout=(15, 75)).json()

    if "data" not in response or "url" not in response["data"]:
        raise Exception(f"All 4 relays failed: {response}")

    direct_url = response["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")
    log(f"[SUCCESS] Relay #4 URL ready: {direct_url}")
    return direct_url

# ==========================================
# 7. META GRAPH API REEL PUBLISHER
# ==========================================
def publish_reel_to_instagram(ig_user_id, video_url, caption, token):
    log(f"[STEP 4/4] Sending 4K Reel to Meta Graph API for IG ID {ig_user_id}...")
    container_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": token
    }
    res = requests.post(container_url, data=payload, timeout=(10, 30)).json()
    if "id" not in res:
        raise Exception(f"Container creation failed: {res}")

    creation_id = res["id"]
    log(f"[INFO] Container ID {creation_id} created. Waiting for Meta 4K processing...")
    status_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{creation_id}"

    for attempt in range(25):
        status_res = requests.get(status_url, params={"fields": "status_code,status", "access_token": token}, timeout=(10, 20)).json()
        status_code = status_res.get("status_code")
        log(f" -> Meta status check [{attempt+1}/25]: {status_code}")

        if status_code == "FINISHED":
            break
        elif status_code in ("ERROR", "EXPIRED"):
            raise Exception(f"Meta rejected video: {status_res}")
        time.sleep(15)
    else:
        raise Exception("Meta video processing timed out.")

    publish_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}/media_publish"
    publish_res = requests.post(publish_url, data={"creation_id": creation_id, "access_token": token}, timeout=(10, 30)).json()

    if "id" not in publish_res:
        raise Exception(f"Publish step failed: {publish_res}")

    log(f"[SUCCESS] PUBLISHED LIVE TO INSTAGRAM! Media ID: {publish_res['id']}")

# ==========================================
# 8. MAIN ENGINE EXECUTION
# ==========================================
def main():
    current_utc_hour = time.gmtime().tm_hour
    target_market = TIER1_SCHEDULE_MAP.get(
        current_utc_hour,
        "Global US/UK/Tier-1 High-Spending Buyer Window"
    )
    log("=== ARC 4K US/UK TIER-1 PUBLISHING ENGINE STARTED ===")
    log(f"[TARGET WAVE] UTC Hour {current_utc_hour:02d}:00 -> {target_market}")

    active_tokens = [t.strip() for t in META_TOKENS if t and t.strip()]
    if not active_tokens:
        raise ValueError("FATAL: META_TOKEN_1 missing in GitHub Secrets!")

    font_path = ensure_custom_font()
    posted_history = load_posted_history()
    log(f"[INFO] Loaded {len(posted_history)} previously posted items from {HISTORY_FILE}.")

    selected_video, used_url, filename_id = ingest_single_fresh_reel(posted_history)
    if not selected_video:
        log("[COMPLETE] All Reels in reel_links.txt and assets/ have already been posted!")
        return

    all_accounts = []
    seen_ig_ids = set()
    for idx, token in enumerate(active_tokens):
        try:
            log(f"[INFO] Checking Meta Token #{idx+1} for Instagram accounts...")
            accs = get_connected_instagram_accounts(token)
            log(f"[INFO] Token #{idx+1}: Found {len(accs)} connected Instagram account(s).")
            for a in accs:
                if a["ig_user_id"] not in seen_ig_ids:
                    seen_ig_ids.add(a["ig_user_id"])
                    all_accounts.append(a)
        except Exception as e:
            log(f"[ERROR] Token #{idx+1} failed: {e}")

    if not all_accounts:
        raise RuntimeError("Zero Instagram Business accounts found on your tokens.")

    # Shuffle account posting order every wave so Meta never sees a fixed sequential pattern
    random.shuffle(all_accounts)

    if used_url:
        mark_as_posted(used_url)
        remove_link_from_queue(used_url)
    if filename_id:
        mark_as_posted(filename_id)

    caption_batch = generate_unique_caption_batch(len(all_accounts))

    success_count = 0
    for index, acc in enumerate(all_accounts):
        log(f"\n========================================")
        log(f"ACCOUNT [{index+1}/{len(all_accounts)}]: {acc['page_name']} ({acc['ig_user_id']})")
        log(f"========================================")

        mutated_output = f"arc_4k_master_{index}.mp4"
        caption = caption_batch[index]
        log(f"[INFO] Assigned Caption: {caption}")

        try:
            mutate_video_for_account(selected_video, mutated_output, font_path)
            public_url = upload_for_meta_download(mutated_output)
            publish_reel_to_instagram(acc["ig_user_id"], public_url, caption, acc["token"])
            success_count += 1
        except Exception as e:
            log(f"[ERROR] Failed on {acc['page_name']}: {e}")
        finally:
            if os.path.exists(mutated_output):
                os.remove(mutated_output)

        if index < len(all_accounts) - 1:
            jitter_seconds = random.randint(20, 60)
            jitter_mins = round(jitter_seconds / 60, 1)
            log(f"[COOLDOWN] Waiting {jitter_mins} minutes ({jitter_seconds}s) before next account...")
            time.sleep(jitter_seconds)

    if os.path.exists(selected_video):
        os.remove(selected_video)

    log(f"\n=== RUN COMPLETE: PUBLISHED ON {success_count}/{len(all_accounts)} ACCOUNTS ===")

if __name__ == "__main__":
    main()
