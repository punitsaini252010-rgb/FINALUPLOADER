import os
import sys
import time
import subprocess
import requests
import random
import yt_dlp

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# ==========================================
# 1. CONFIGURATION & ANONYMOUS BRAND SETTINGS
# ==========================================
META_TOKENS = [
    os.getenv("META_TOKEN_1"),
    os.getenv("META_TOKEN_2")
]

GRAPH_API_VERSION = "v20.0"
ARC_DIRECT_URL = os.getenv("ARC_DIRECT_URL") or "https://whop.com/your-arc-link"

ACCOUNTS_PER_WAVE = 23
MAX_ACCOUNTS_PER_VIDEO = 1

LINKS_FILE = "reel_links.txt"
HISTORY_FILE = "posted_history.txt"
CURSOR_FILE = "account_cursor.txt"
REPLIED_COMMENTS_FILE = "replied_comments.txt"
ASSETS_DIR = "assets"
CUSTOM_FONT_PATH = "Montserrat-ExtraBold.ttf"

# Curated High-End Cinematic B-Roll Sources (Dark Luxury, Trading Terminals, Architecture, Workspaces)
CINEMATIC_BROLL_SOURCES = [
    "https://www.youtube.com/watch?v=LXb3EKWsInQ", # Cinematic Cityscapes / Luxury B-roll placeholder links
    "https://www.youtube.com/watch?v=3JZ_D3ELwOQ", 
    "https://www.youtube.com/watch?v=ScMzIvxBSi4"
]

ARC_BASE_CAPTIONS = [
    'Comment "ARC" for free Vault access or tap @ARCBLOODLINE30',
    '@ARCBLOODLINE30 Comment "ARC" and I\'ll DM you the link.',
    'Comment "ARC" to unlock the $100 Starter Kit -> @ARCBLOODLINE30',
    '@ARCBLOODLINE30 Drop "ARC" below for instant terminal entry.',
    'First 1,000 spots FREE. Comment "ARC" or tap @ARCBLOODLINE30',
    '@ARCBLOODLINE30 Comment "ARC" below to escape the 9-5 cage.',
    'Weak minds scroll. Winners comment "ARC" -> @ARCBLOODLINE30',
    '@ARCBLOODLINE30 Reply "ARC" below for free Vault access.',
    'Comment "ARC" for the private blueprint or tap @ARCBLOODLINE30',
    '@ARCBLOODLINE30 Comment "ARC" and check your DMs immediately.'
]

# Hard-Hitting Anonymous Brand Text Frameworks (Flashed on screen)
ARC_VALUE_HOOKS = [
    ("THE 9-5 MATRIX IS DESIGNED", "TO KEEP YOU BROKE FOR 40 YEARS."),
    ("BUILDING DIGITAL ASSETS", "IS THE ONLY WAY OUT IN 2026."),
    ("STOP CONSUMING BRAINROT.", "START PRINTING CASHFLOW INSIDE ARC."),
    ("YOU DON'T NEED LUCK.", "YOU NEED A SYSTEM THAT PRINTS."),
    ("THE FIRST 1,000 TERMINAL SPOTS", "ARE 100% FREE INSIDE ARC.")
]

FIRST_COMMENT_TEMPLATES = [
    'Comment "ARC" below and I\'ll DM you the free ARC Vault + $100 Starter Kit link directly ⚡ (or tap @ARCBLOODLINE30)',
    'Drop "ARC" in the replies for instant free access in your DMs 🔓 Backup link in @ARCBLOODLINE30 bio.',
    'First 1,000 spots are 100% free — reply "ARC" right here and check your DMs ⚡ (@ARCBLOODLINE30)'
]

PUBLIC_REPLY_TEMPLATES = [
    "Just sent the free ARC Vault link straight to your DMs ⚡ Check your message requests!",
    "Check your DMs right now — sent you the direct ARC invite + Starter Kit 🔓",
    "Sent! Check your inbox/requests for the ARC terminal link (or tap @ARCBLOODLINE30) ⚡"
]

def generate_unique_caption_batch(count):
    pool = list(ARC_BASE_CAPTIONS)
    random.shuffle(pool)
    micro_tags = ["", " ↓", " ⚡", " 🗝️", " 🔓"]
    return [f"{pool[i % len(pool)]}{random.choice(micro_tags)}".strip() for i in range(count)]

# ==========================================
# 2. B-ROLL QUEUE INGESTER (FALLBACK TO CINEMATIC SOURCES)
# ==========================================
def ingest_single_fresh_reel(posted_history):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    
    # If links file is empty or missing, inject cinematic B-roll sources automatically
    if not os.path.exists(LINKS_FILE) or os.path.getsize(LINKS_FILE) < 10:
        with open(LINKS_FILE, "w", encoding="utf-8") as f:
            for src in CINEMATIC_BROLL_SOURCES:
                f.write(f"{src}\n")

    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        all_urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    for target_url in [u for u in all_urls if u not in posted_history]:
        log(f"[STEP 1/4] Downloading cinematic B-roll background: {target_url}")
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": os.path.join(ASSETS_DIR, "cinematic_%(id)s.%(ext)s"),
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 25,
            "http_headers": {"Accept-Language": "en-US,en;q=0.9"}
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=True)
                downloaded_file = f"cinematic_{info.get('id', 'unknown')}.mp4"
                full_path = os.path.join(ASSETS_DIR, downloaded_file)

                if os.path.exists(full_path):
                    append_to_set_file(HISTORY_FILE, target_url, posted_history)
                    log(f"[SUCCESS] Cinematic B-roll ready: {downloaded_file}")
                    return full_path
        except Exception as e:
            log(f"[WARNING] B-roll download failed ({target_url}): {e}. Rotating...")
            append_to_set_file(HISTORY_FILE, target_url, posted_history)
    return None

# ==========================================
# 3. ROUND-ROBIN QUEUE & LEDGER MANAGERS
# ==========================================
def select_round_robin_accounts(all_accounts, batch_size):
    sorted_accs = sorted(all_accounts, key=lambda x: str(x["ig_user_id"]))
    total = len(sorted_accs)
    start_idx = 0

    if os.path.exists(CURSOR_FILE):
        try:
            with open(CURSOR_FILE, "r", encoding="utf-8") as f:
                start_idx = int(f.read().strip()) % total
        except Exception:
            start_idx = 0

    selected = [sorted_accs[(start_idx + i) % total] for i in range(min(batch_size, total))]
    next_cursor = (start_idx + len(selected)) % total

    with open(CURSOR_FILE, "w", encoding="utf-8") as f:
        f.write(str(next_cursor))

    log(f"[ROUND-ROBIN] Cursor {start_idx} -> {next_cursor} (Selected {len(selected)}/{total} accounts).")
    return selected

def load_set_file(filepath):
    if not os.path.exists(filepath):
        return set()
    with open(filepath, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def append_to_set_file(filepath, identifier, memory_set):
    if not identifier:
        return
    clean = str(identifier).strip()
    if clean not in memory_set:
        memory_set.add(clean)
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"{clean}\n")

# ==========================================
# 4. CUSTOM FONT & KINETIC TYPOGRAPHY MASTERING
# ==========================================
def ensure_custom_font():
    if os.path.exists(CUSTOM_FONT_PATH) and os.path.getsize(CUSTOM_FONT_PATH) > 10000:
        return CUSTOM_FONT_PATH
    font_url = "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf"
    try:
        res = requests.get(font_url, timeout=(10, 20))
        if res.status_code == 200 and len(res.content) > 10000:
            with open(CUSTOM_FONT_PATH, "wb") as f:
                f.write(res.content)
            return CUSTOM_FONT_PATH
    except Exception:
        pass
    return "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def get_video_duration(input_path):
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_path]
        res = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        return float(res.stdout.decode("utf-8").strip())
    except Exception:
        return 12.0

def mutate_video_for_account(input_path, output_path, font_path):
    log(f"[STEP 2/4] Anonymous Brand Kinetic Typography Mastering ({os.path.basename(input_path)})...")
    trim_start = round(random.uniform(0.12, 1.5), 3)
    crop_keep = round(random.uniform(0.975, 0.992), 4)
    x_jitter = random.randint(2, 6)
    y_jitter = random.randint(2, 6)
    angle_deg = random.choice([-0.35, -0.25, 0.25, 0.35])
    flip_filter = "hflip," if random.random() < 0.5 else ""
    noise_level = random.randint(2, 3)

    b_shift = round(random.uniform(-0.008, 0.008), 4)
    c_shift = round(random.uniform(0.992, 1.012), 4)
    s_shift = round(random.uniform(0.990, 1.015), 4)
    speed = round(random.uniform(0.985, 1.025), 4)
    epoch_jitter = int(time.time()) - random.randint(300, 172800)

    raw_duration = get_video_duration(input_path)
    final_duration = max(5.0, (raw_duration - trim_start) / speed)
    cta_start = round(max(2.0, final_duration - 2.5), 2)

    # Pick a random high-impact ARC value hook for on-screen text
    hook_top, hook_bottom = random.choice(ARC_VALUE_HOOKS)
    cta_line1 = "COMMENT 'ARC' FOR FREE ACCESS"
    cta_line2 = "OR TAP @ARCBLOODLINE30 IN BIO"

    wm_x_offset = random.randint(-6, 6)
    wm_y = 340 + random.randint(-8, 8)

    # FFmpeg filter chain embedding kinetic text directly over cinematic B-roll
    vf_chain = (
        f"setpts=PTS/{speed},{flip_filter}"
        f"rotate={angle_deg}*PI/180:bilinear=1:fillcolor=black,"
        f"crop=iw*{crop_keep}:ih*{crop_keep}:(iw-ow)/2+{x_jitter}:(ih-oh)/2+{y_jitter},"
        f"scale=2160:3840:force_original_aspect_ratio=increase:flags=lanczos+accurate_rnd+full_chroma_int,"
        f"crop=2160:3840,"
        f"eq=brightness={b_shift}:contrast={c_shift}:saturation={s_shift},"
        f"noise=alls={noise_level}:allf=t,unsharp=5:5:0.34:5:5:0.0,"
        # Permanent Brand Watermark
        f"drawtext=fontfile={font_path}:text='ARC':expansion=none:"
        f"fontcolor=white@0.35:fontsize=130:shadowcolor=black@0.3:shadowx=3:shadowy=3:"
        f"x=(w-text_w)/2+{wm_x_offset}:y={wm_y},"
        # Kinetic Top Hook (Yellow Accent)
        f"drawtext=fontfile={font_path}:text='{hook_top}':expansion=none:"
        f"fontcolor=0xFFD700:fontsize=76:shadowcolor=black@0.9:shadowx=4:shadowy=4:"
        f"box=1:boxcolor=black@0.85:boxborderw=24:"
        f"x=(w-text_w)/2:y=(h/2)-180:enable='lt(t,{cta_start})',"
        # Kinetic Bottom Hook (White)
        f"drawtext=fontfile={font_path}:text='{hook_bottom}':expansion=none:"
        f"fontcolor=white:fontsize=70:shadowcolor=black@0.9:shadowx=4:shadowy=4:"
        f"box=1:boxcolor=black@0.85:boxborderw=24:"
        f"x=(w-text_w)/2:y=(h/2)-70:enable='lt(t,{cta_start})',"
        # Final CTA End Card Overlay
        f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.88:t=fill:enable='gte(t,{cta_start})',"
        f"drawtext=fontfile={font_path}:text='{cta_line1}':expansion=none:"
        f"fontcolor=0xFFD700:fontsize=84:shadowcolor=black@0.9:shadowx=4:shadowy=4:"
        f"x=(w-text_w)/2:y=(h/2)-95:enable='gte(t,{cta_start})',"
        f"drawtext=fontfile={font_path}:text='{cta_line2}':expansion=none:"
        f"fontcolor=white:fontsize=70:box=1:boxcolor=black@0.92:boxborderw=34:"
        f"x=(w-text_w)/2:y=(h/2)+35:enable='gte(t,{cta_start})'"
    )

    crf_val = str(random.choice([21, 22, 23]))
    cmd = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", str(trim_start), "-i", input_path, "-vf", vf_chain,
        "-c:v", "libx264", "-profile:v", "high", "-level:v", "5.1",
        "-crf", crf_val, "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-an", "-map_metadata", "-1", "-metadata", f"creation_time={epoch_jitter}", output_path
    ]

    result = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=240)
    if result.returncode != 0:
        raise Exception(f"FFmpeg failed: {result.stderr.decode('utf-8', errors='ignore')}")
    return output_path

# ==========================================
# 5. RELAY UPLOAD, PUBLISH & AUTO-DM SWEEP
# ==========================================
def upload_for_meta_download(file_path):
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", "Accept-Language": "en-US,en;q=0.9"}
    try:
        with open(file_path, "rb") as f:
            res = requests.post("https://uguu.se/upload", files={"files[]": f}, headers=headers, timeout=(15, 75)).json()
        if res.get("success") and res.get("files"):
            return res["files"][0]["url"]
    except Exception:
        pass
    try:
        with open(file_path, "rb") as f:
            res = requests.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload"}, files={"fileToUpload": f}, headers=headers, timeout=(15, 75))
        if res.status_code == 200 and res.text.strip().startswith("https://"):
            return res.text.strip()
    except Exception:
        pass
    with open(file_path, "rb") as f:
        response = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, headers=headers, timeout=(15, 75)).json()
    return response["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")

def seed_first_comment(media_id, token, replied_comments):
    comment_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{media_id}/comments"
    try:
        res = requests.post(comment_url, data={"message": random.choice(FIRST_COMMENT_TEMPLATES), "access_token": token}, timeout=(10, 20)).json()
        if "id" in res:
            append_to_set_file(REPLIED_COMMENTS_FILE, res["id"], replied_comments)
            log(f"[AUTO-SEED] Posted first comment on Media {media_id}")
    except Exception:
        pass

def publish_reel_to_instagram(ig_user_id, video_url, caption, token, replied_comments):
    container_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}/media"
    payload = {"media_type": "REELS", "video_url": video_url, "caption": caption, "share_to_feed": "true", "access_token": token}
    res = requests.post(container_url, data=payload, timeout=(10, 30)).json()
    if "id" not in res:
        raise Exception(f"Container failed: {res}")

    creation_id = res["id"]
    status_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{creation_id}"
    for _ in range(25):
        status_res = requests.get(status_url, params={"fields": "status_code,status", "access_token": token}, timeout=(10, 20)).json()
        status_code = status_res.get("status_code")
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
        raise Exception(f"Publish failed: {publish_res}")

    media_id = publish_res["id"]
    log(f"[SUCCESS] PUBLISHED LIVE! Media ID: {media_id}")
    seed_first_comment(media_id, token, replied_comments)

def sweep_and_dm_commenters(all_accounts, replied_comments):
    log("\n=== RUNNING AUTOMATED COMMENT-TO-DM SWEEP ACROSS FLEET ===")
    dm_text = (
        f"You're in ⚡ Here is your free access link to the ARC Operating System "
        f"+ The First $100 Starter Kit:\n\n👉 {ARC_DIRECT_URL}\n\n"
        f"(First 1,000 spots are free — lock in now before gates close)"
    )
    total_replied = 0
    for acc in all_accounts:
        ig_id, page_id, page_token, user_token = acc["ig_user_id"], acc["page_id"], acc["page_token"], acc["token"]
        own_username = (acc.get("ig_username") or "").lower()
        media_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_id}/media"
        try:
            res = requests.get(media_url, params={"fields": "id,comments.limit(25){id,text,username}", "limit": 6, "access_token": user_token}, timeout=(10, 20)).json()
            for media in res.get("data", []):
                for c in media.get("comments", {}).get("data", []):
                    cid = str(c.get("id", ""))
                    c_user = str(c.get("username", "")).lower()
                    c_text = str(c.get("text", "")).strip()
                    if not cid or cid in replied_comments:
                        continue
                    if (own_username and c_user == own_username) or "@arcbloodline30" in c_text.lower():
                        append_to_set_file(REPLIED_COMMENTS_FILE, cid, replied_comments)
                        continue

                    dm_payload = {"recipient": {"comment_id": cid}, "message": {"text": dm_text}}
                    dm_sent = False
                    for endpoint_id, tok in [(ig_id, page_token), (page_id, page_token), (ig_id, user_token)]:
                        if not endpoint_id:
                            continue
                        dm_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{endpoint_id}/messages"
                        dm_res = requests.post(dm_url, params={"access_token": tok}, json=dm_payload, timeout=(10, 15)).json()
                        if "message_id" in dm_res or "recipient_id" in dm_res:
                            dm_sent = True
                            log(f"[AUTO-DM SENT] Sent ARC link to @{c_user} on {acc['page_name']}")
                            break

                    reply_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{cid}/replies"
                    pub_msg = random.choice(PUBLIC_REPLY_TEMPLATES) if dm_sent else "Tap @ARCBLOODLINE30 right now — free ARC Vault link is live in the bio ⚡"
                    requests.post(reply_url, data={"message": pub_msg, "access_token": user_token}, timeout=(10, 15))
                    append_to_set_file(REPLIED_COMMENTS_FILE, cid, replied_comments)
                    total_replied += 1
        except Exception as e:
            log(f"[SWEEP SKIP] {acc['page_name']}: {e}")
    log(f"=== AUTO-DM SWEEP COMPLETE: CONVERTED {total_replied} NEW COMMENTERS ===\n")

# ==========================================
# 6. MAIN ANONYMOUS BRAND ENGINE EXECUTION
# ==========================================
def main():
    log("=== ARC ANONYMOUS BRAND KINETIC ENGINE STARTED ===")
    active_tokens = [t.strip() for t in META_TOKENS if t and t.strip()]
    if not active_tokens:
        raise ValueError("FATAL: META_TOKEN_1 missing in GitHub Secrets!")

    font_path = ensure_custom_font()
    posted_history = load_set_file(HISTORY_FILE)
    replied_comments = load_set_file(REPLIED_COMMENTS_FILE)

    all_accounts, seen_ig_ids = [], set()
    for token in active_tokens:
        try:
            for a in get_connected_instagram_accounts(token):
                if a["ig_user_id"] not in seen_ig_ids:
                    seen_ig_ids.add(a["ig_user_id"])
                    all_accounts.append(a)
        except Exception as e:
            log(f"[ERROR] Token check failed: {e}")

    if not all_accounts:
        raise RuntimeError("Zero Instagram Business accounts found.")

    sweep_and_dm_commenters(all_accounts, replied_comments)

    wave_accounts = select_round_robin_accounts(all_accounts, ACCOUNTS_PER_WAVE)
    caption_batch = generate_unique_caption_batch(len(wave_accounts))

    current_video = None
    success_count = 0

    for index, acc in enumerate(wave_accounts):
        if index % MAX_ACCOUNTS_PER_VIDEO == 0 or not current_video:
            if current_video and os.path.exists(current_video):
                os.remove(current_video)
            new_vid = ingest_single_fresh_reel(posted_history)
            if new_vid:
                current_video = new_vid
            elif not current_video:
                log("[COMPLETE] B-roll source missing!")
                break

        log(f"\n--- NODE [{index+1}/{len(wave_accounts)}]: {acc['page_name']} ({acc['ig_user_id']}) ---")
        mutated_output = f"arc_4k_master_{index}.mp4"

        try:
            mutate_video_for_account(current_video, mutated_output, font_path)
            public_url = upload_for_meta_download(mutated_output)
            publish_reel_to_instagram(acc["ig_user_id"], public_url, caption_batch[index], acc["token"], replied_comments)
            success_count += 1
        except Exception as e:
            log(f"[ERROR] Failed on {acc['page_name']}: {e}")
        finally:
            if os.path.exists(mutated_output):
                os.remove(mutated_output)

        if index < len(wave_accounts) - 1:
            jitter_seconds = random.randint(35, 75)
            log(f"[COOLDOWN] Waiting {jitter_seconds}s before next node...")
            time.sleep(jitter_seconds)

    if current_video and os.path.exists(current_video):
        os.remove(current_video)

    log(f"\n=== WAVE COMPLETE: {success_count}/{len(wave_accounts)} BRAND KINETIC REELS PUBLISHED ===")

if __name__ == "__main__":
    main()
