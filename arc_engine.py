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
# 1. CONFIGURATION & DIRECT BIO-FUNNEL SETTINGS
# ==========================================
META_TOKENS = [
    os.getenv("META_TOKEN_1"),
    os.getenv("META_TOKEN_2")
]

GRAPH_API_VERSION = "v20.0"

ACCOUNTS_PER_WAVE = 23
MAX_ACCOUNTS_PER_VIDEO = 1

LINKS_FILE = "reel_links.txt"
HISTORY_FILE = "posted_history.txt"
CURSOR_FILE = "account_cursor.txt"
ASSETS_DIR = "assets"
CUSTOM_FONT_PATH = "Montserrat-ExtraBold.ttf"

# =====================================================================
# PASTE SOUNDCLOUD OR DIRECT .MP3/.MP4 SONG LINKS HERE
# (Avoid youtube.com links here because YouTube blocks GitHub Actions IPs)
# =====================================================================
CUSTOM_SONG_LIBRARY = [
    "https://files.catbox.moe/9r7y0z.mp3",  # <-- Replace with your SoundCloud or direct .mp3/catbox link
]

# Unblockable Direct HD MP4 B-Roll Fallbacks (Works 100% of the time on GitHub Actions IPs)
UNBLOCKABLE_BROLL_MP4S = [
    "https://assets.mixkit.co/videos/preview/mixkit-aerial-view-of-city-traffic-at-night-11-large.mp4",
    "https://assets.mixkit.co/videos/preview/mixkit-flying-through-a-modern-city-at-night-41587-large.mp4",
    "https://assets.mixkit.co/videos/preview/mixkit-hands-of-a-man-typing-on-a-laptop-in-the-dark-41614-large.mp4",
    "https://assets.mixkit.co/videos/preview/mixkit-driving-through-a-tunnel-with-lights-41575-large.mp4",
    "https://assets.mixkit.co/videos/preview/mixkit-futuristic-corridor-with-neon-lights-41595-large.mp4",
    "https://assets.mixkit.co/videos/preview/mixkit-aerial-view-of-skyscrapers-in-a-modern-city-41585-large.mp4",
    "https://assets.mixkit.co/videos/preview/mixkit-man-working-on-his-laptop-in-a-dark-room-41611-large.mp4",
    "https://assets.mixkit.co/videos/preview/mixkit-clouds-moving-over-the-mountains-at-sunset-41566-large.mp4"
]

ARC_BIO_CAPTIONS = [
    "@ARCBLOODLINE30 Free access to the ARC Vault + First $100 Starter Kit is live in the bio.",
    "@ARCBLOODLINE30 First 1,000 terminal spots are 100% free. Tap @ARCBLOODLINE30 to lock yours in.",
    "@ARCBLOODLINE30 Stop watching others cash out. Enter the ARC Operating System via @ARCBLOODLINE30 bio.",
    "@ARCBLOODLINE30 The blueprint is live. Tap @ARCBLOODLINE30 and claim your free Starter Kit before gates lock.",
    "@ARCBLOODLINE30 Built for execution, not spectators. Tap @ARCBLOODLINE30 for instant Vault entry.",
    "@ARCBLOODLINE30 Escape the 9-5 cage. Free ARC terminal invite is waiting inside @ARCBLOODLINE30 bio.",
    "@ARCBLOODLINE30 Gates close permanently at member #1,000. Tap @ARCBLOODLINE30 right now.",
    "@ARCBLOODLINE30 Your first $100 digital system is unlocked inside @ARCBLOODLINE30. Tap the bio link."
]

# Apostrophe-safe 3-Stage Conversion Copywriting (Zero FFmpeg syntax crashes)
ARC_CONVERSION_SEQUENCES = [
    ("STILL TRADING HOURS FOR PENNIES", "WHILE AUTOMATED SYSTEMS PRINT?", "UNLOCK THE ARC OPERATING SYSTEM", "FREE $100 STARTER KIT IN BIO"),
    ("99% SCROLL PAST WEALTH SYSTEMS", "THE 1% BUILD DIGITAL CASHFLOW.", "INSIDE THE PRIVATE ARC VAULT:", "STEP-BY-STEP EXECUTION BLUEPRINTS"),
    ("THE 9-5 MATRIX WAS DESIGNED", "TO KEEP YOU BROKE FOR 40 YEARS.", "WE BUILT THE EXIT PROTOCOL.", "FIRST 1,000 SPOTS ARE 100% FREE"),
    ("YOU DO NOT HAVE A MONEY PROBLEM", "YOU HAVE A SYSTEM PROBLEM.", "PLUG INTO ARC TERMINAL TODAY", "ZERO COST UNTIL MEMBER #1,000"),
    ("STOP CONSUMING CHEAP DOPAMINE", "START BUILDING REAL LEVERAGE.", "CLAIM YOUR FREE ARC VAULT PASS", "BEFORE THE GATES LOCK FOREVER")
]

def generate_unique_caption_batch(count):
    pool = list(ARC_BIO_CAPTIONS)
    random.shuffle(pool)
    micro_tags = ["", " ⚡", " 🔓", " ↓", " 🗝️"]
    return [f"{pool[i % len(pool)]}{random.choice(micro_tags)}".strip() for i in range(count)]

# ==========================================
# 2. QUEUE & LEDGER MANAGERS
# ==========================================
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

def remove_link_from_queue(used_url):
    if not used_url or not os.path.exists(LINKS_FILE):
        return
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            if line.strip() != used_url.strip():
                f.write(line)

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

# ==========================================
# 3. SELF-HEALING B-ROLL & SONG ENGINE
# ==========================================
def get_random_custom_song():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    valid_songs = [s.strip() for s in CUSTOM_SONG_LIBRARY if s and s.strip()]
    if not valid_songs:
        return None

    song_url = random.choice(valid_songs)
    safe_id = abs(hash(song_url)) % (10 ** 8)
    out_path = os.path.join(ASSETS_DIR, f"song_{safe_id}.m4a")

    if os.path.exists(out_path) and os.path.getsize(out_path) > 15000:
        return out_path

    log(f"[SONG ENGINE] Downloading custom track: {song_url}")
    # Direct MP3/M4A download if it's a direct file URL
    if song_url.lower().endswith((".mp3", ".m4a", ".wav", ".mp4")):
        try:
            r = requests.get(song_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=(10, 30))
            if r.status_code == 200 and len(r.content) > 15000:
                with open(out_path, "wb") as f:
                    f.write(r.content)
                return out_path
        except Exception as e:
            log(f"[WARNING] Direct song download failed: {e}")

    # Fallback to yt-dlp for SoundCloud / other links
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": out_path,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 20
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(song_url, download=True)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 15000:
            return out_path
    except Exception as e:
        log(f"[WARNING] Song URL blocked or unavailable ({song_url}): {e}")
    return None

def download_direct_mp4_fallback():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    urls = list(UNBLOCKABLE_BROLL_MP4S)
    random.shuffle(urls)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for url in urls:
        safe_id = abs(hash(url)) % (10 ** 8)
        out_path = os.path.join(ASSETS_DIR, f"direct_broll_{safe_id}.mp4")
        if os.path.exists(out_path) and os.path.getsize(out_path) > 50000:
            log(f"[SUCCESS] Using cached HD B-roll: {os.path.basename(out_path)}")
            return out_path
        try:
            log(f"[FALLBACK] Fetching unblockable HD B-roll: {url}")
            res = requests.get(url, headers=headers, timeout=(10, 35))
            if res.status_code == 200 and len(res.content) > 50000:
                with open(out_path, "wb") as f:
                    f.write(res.content)
                log(f"[SUCCESS] Downloaded HD B-roll: {os.path.basename(out_path)}")
                return out_path
        except Exception as e:
            log(f"[WARNING] Fallback fetch failed: {e}")

    # Ultimate emergency synthetic dark-luxury background video via FFmpeg lavfi
    synth_path = os.path.join(ASSETS_DIR, "synth_luxury_bg.mp4")
    cmd = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "color=c=0x08080c:s=1080x1920:d=10:r=30",
        "-vf", "noise=alls=18:allf=t+u",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", synth_path
    ]
    subprocess.run(cmd, timeout=30)
    return synth_path

def ingest_single_fresh_reel(posted_history):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    all_urls = []
    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, "r", encoding="utf-8") as f:
            all_urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    candidates = [u for u in all_urls if u not in posted_history]

    for target_url in candidates:
        log(f"[STEP 1/4] Ingesting queue link: {target_url}")
        safe_id = abs(hash(target_url)) % (10 ** 8)
        full_path = os.path.join(ASSETS_DIR, f"broll_{safe_id}.mp4")

        # If direct MP4 link
        if target_url.lower().endswith(".mp4"):
            try:
                r = requests.get(target_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=(10, 35))
                if r.status_code == 200 and len(r.content) > 50000:
                    with open(full_path, "wb") as f:
                        f.write(r.content)
                    append_to_set_file(HISTORY_FILE, target_url, posted_history)
                    remove_link_from_queue(target_url)
                    return full_path
            except Exception:
                pass

        ydl_opts = {
            "format": "bestvideo[height<=1920][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": full_path,
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 20,
            "playlist_items": "1"
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(target_url, download=True)
                if os.path.exists(full_path) and os.path.getsize(full_path) > 50000:
                    append_to_set_file(HISTORY_FILE, target_url, posted_history)
                    remove_link_from_queue(target_url)
                    log(f"[SUCCESS] Queue video ready: {os.path.basename(full_path)}")
                    return full_path
        except Exception as e:
            log(f"[WARNING] Queue link failed ({target_url}): {e}. Removing from queue...")
            append_to_set_file(HISTORY_FILE, target_url, posted_history)
            remove_link_from_queue(target_url)

    # Always succeed by pulling from the unblockable HD B-Roll pool
    return download_direct_mp4_fallback()

# ==========================================
# 4. INSTAGRAM GRAPH API ACCOUNT DISCOVERY
# ==========================================
def get_connected_instagram_accounts(token):
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/accounts"
    params = {
        "fields": "id,name,access_token,instagram_business_account{id,username}",
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
                "page_id": page.get("id"),
                "page_name": page.get("name", "ARC_Node"),
                "page_token": page.get("access_token", token),
                "ig_user_id": ig_biz["id"],
                "ig_username": ig_biz.get("username", ""),
                "token": token
            })
    return accounts

# ==========================================
# 5. META-COMPLIANT 1080x1920 MASTERING
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

def get_media_duration(input_path):
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_path]
        res = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        return float(res.stdout.decode("utf-8").strip())
    except Exception:
        return 10.0

def mutate_video_for_account(input_path, output_path, font_path):
    log(f"[STEP 2/4] Dark-Luxury 1080p HD + Audio Mastering ({os.path.basename(input_path)})...")

    raw_dur = get_media_duration(input_path)
    final_duration = round(random.uniform(8.2, 9.8), 2)
    trim_start = round(random.uniform(0.1, max(0.2, raw_dur - final_duration - 0.5)), 2) if raw_dur > final_duration + 1.0 else 0.0

    phase2_start = round(final_duration * 0.36, 2)
    cta_start = round(final_duration - 2.4, 2)

    crop_keep = round(random.uniform(0.975, 0.992), 4)
    x_jitter = random.randint(2, 6)
    y_jitter = random.randint(2, 6)
    angle_deg = random.choice([-0.3, -0.2, 0.2, 0.3])
    flip_filter = "hflip," if random.random() < 0.5 else ""
    noise_level = random.randint(2, 3)

    b_shift = round(random.uniform(-0.045, -0.025), 4)
    c_shift = round(random.uniform(1.06, 1.10), 4)
    s_shift = round(random.uniform(0.86, 0.94), 4)
    speed = round(random.uniform(0.985, 1.022), 4)
    epoch_jitter = int(time.time()) - random.randint(300, 172800)

    # Sanitize any accidental single quotes so FFmpeg never crashes
    h1, h2, p1, p2 = [txt.replace("'", "") for txt in random.choice(ARC_CONVERSION_SEQUENCES)]
    cta1 = "TAP @ARCBLOODLINE30 IN BIO"
    cta2 = "FREE VAULT + $100 STARTER KIT"

    wm_x_offset = random.randint(-4, 4)
    wm_y = 165 + random.randint(-5, 5)

    # 1080x1920 Native Full HD (100% Meta Reels API compliant, zero container rejections)
    vf_chain = (
        f"setpts=PTS/{speed},{flip_filter}"
        f"rotate={angle_deg}*PI/180:bilinear=1:fillcolor=black,"
        f"crop=iw*{crop_keep}:ih*{crop_keep}:(iw-ow)/2+{x_jitter}:(ih-oh)/2+{y_jitter},"
        f"scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop=1080:1920,fps=30,"
        f"eq=brightness={b_shift}:contrast={c_shift}:saturation={s_shift},"
        f"noise=alls={noise_level}:allf=t,unsharp=5:5:0.45:5:5:0.0,"
        f"drawtext=fontfile={font_path}:text='ARC':expansion=none:"
        f"fontcolor=white@0.38:fontsize=64:shadowcolor=black@0.4:shadowx=2:shadowy=2:"
        f"x=(w-text_w)/2+{wm_x_offset}:y={wm_y},"
        f"drawtext=fontfile={font_path}:text='{h1}':expansion=none:"
        f"fontcolor=0xFFD700:fontsize=38:shadowcolor=black@0.95:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.86:boxborderw=14:"
        f"x=(w-text_w)/2:y=(h/2)-80:enable='lt(t,{phase2_start})',"
        f"drawtext=fontfile={font_path}:text='{h2}':expansion=none:"
        f"fontcolor=white:fontsize=34:shadowcolor=black@0.95:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.86:boxborderw=14:"
        f"x=(w-text_w)/2:y=(h/2)-15:enable='lt(t,{phase2_start})',"
        f"drawtext=fontfile={font_path}:text='{p1}':expansion=none:"
        f"fontcolor=0xFFD700:fontsize=38:shadowcolor=black@0.95:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.86:boxborderw=14:"
        f"x=(w-text_w)/2:y=(h/2)-80:enable='between(t,{phase2_start},{cta_start})',"
        f"drawtext=fontfile={font_path}:text='{p2}':expansion=none:"
        f"fontcolor=white:fontsize=34:shadowcolor=black@0.95:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.86:boxborderw=14:"
        f"x=(w-text_w)/2:y=(h/2)-15:enable='between(t,{phase2_start},{cta_start})',"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.90:t=fill:enable='gte(t,{cta_start})',"
        f"drawtext=fontfile={font_path}:text='{cta1}':expansion=none:"
        f"fontcolor=0xFFD700:fontsize=42:shadowcolor=black@0.95:shadowx=2:shadowy=2:"
        f"x=(w-text_w)/2:y=(h/2)-50:enable='gte(t,{cta_start})',"
        f"drawtext=fontfile={font_path}:text='{cta2}':expansion=none:"
        f"fontcolor=white:fontsize=35:box=1:boxcolor=black@0.92:boxborderw=16:"
        f"x=(w-text_w)/2:y=(h/2)+20:enable='gte(t,{cta_start})'"
    )

    custom_song = get_random_custom_song()
    crf_val = str(random.choice([20, 21]))
    fade_out_st = round(max(1.0, final_duration - 1.2), 2)

    if custom_song and os.path.exists(custom_song):
        song_dur = get_media_duration(custom_song)
        song_start = round(random.uniform(2.0, max(3.0, song_dur - final_duration - 1.0)), 2) if song_dur > final_duration + 4.0 else 0.0
        pitch_shift = round(random.uniform(0.988, 1.015), 4)
        af_chain = f"asetrate=48000*{pitch_shift},aresample=48000,volume=0.85,afade=t=in:st=0:d=0.5,afade=t=out:st={fade_out_st}:d=1.0"

        cmd = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-stream_loop", "-1", "-ss", str(trim_start), "-t", str(final_duration), "-i", input_path,
            "-stream_loop", "-1", "-ss", str(song_start), "-t", str(final_duration), "-i", custom_song,
            "-map", "0:v:0", "-map", "1:a:0",
            "-vf", vf_chain, "-af", af_chain,
            "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.1",
            "-crf", crf_val, "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-shortest", "-map_metadata", "-1", "-metadata", f"creation_time={epoch_jitter}",
            output_path
        ]
    else:
        # Built-in dark cinematic sub-bass drone if custom song link was blocked
        bass_freq = random.choice([55, 58, 62, 65])
        cmd = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-stream_loop", "-1", "-ss", str(trim_start), "-t", str(final_duration), "-i", input_path,
            "-f", "lavfi", "-t", str(final_duration), "-i", f"sine=frequency={bass_freq}:sample_rate=48000",
            "-map", "0:v:0", "-map", "1:a:0",
            "-vf", vf_chain,
            "-af", f"volume=0.35,tremolo=f=4.0:d=0.6,afade=t=in:st=0:d=0.5,afade=t=out:st={fade_out_st}:d=1.0",
            "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.1",
            "-crf", crf_val, "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-shortest", "-map_metadata", "-1", "-metadata", f"creation_time={epoch_jitter}",
            output_path
        ]

    result = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    if result.returncode != 0:
        raise Exception(f"FFmpeg failed: {result.stderr.decode('utf-8', errors='ignore')}")
    return output_path

# ==========================================
# 6. RELAY UPLOAD & CLEAN GRAPH API PUBLISH
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
    try:
        with open(file_path, "rb") as f:
            res = requests.post("https://litterbox.catbox.moe/resources/internals/api.php", data={"reqtype": "fileupload", "time": "1h"}, files={"fileToUpload": f}, headers=headers, timeout=(15, 75))
        if res.status_code == 200 and res.text.strip().startswith("https://"):
            return res.text.strip()
    except Exception:
        pass
    with open(file_path, "rb") as f:
        response = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, headers=headers, timeout=(15, 75)).json()
    return response["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")

def publish_reel_to_instagram(ig_user_id, video_url, caption, token):
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

    log(f"[SUCCESS] PUBLISHED LIVE! Media ID: {publish_res['id']}")

# ==========================================
# 7. MAIN EXECUTION
# ==========================================
def main():
    log("=== ARC PURE BIO-FUNNEL & CUSTOM SONG ENGINE STARTED ===")
    active_tokens = [t.strip() for t in META_TOKENS if t and t.strip()]
    if not active_tokens:
        raise ValueError("FATAL: META_TOKEN_1 missing in GitHub Secrets!")

    font_path = ensure_custom_font()
    posted_history = load_set_file(HISTORY_FILE)

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

    wave_accounts = select_round_robin_accounts(all_accounts, ACCOUNTS_PER_WAVE)
    caption_batch = generate_unique_caption_batch(len(wave_accounts))

    current_video = None
    success_count = 0

    for index, acc in enumerate(wave_accounts):
        if index % MAX_ACCOUNTS_PER_VIDEO == 0 or not current_video:
            new_vid = ingest_single_fresh_reel(posted_history)
            if new_vid:
                current_video = new_vid

        log(f"\n--- NODE [{index+1}/{len(wave_accounts)}]: {acc['page_name']} ({acc['ig_user_id']}) ---")
        mutated_output = f"arc_hd_master_{index}.mp4"

        try:
            mutate_video_for_account(current_video, mutated_output, font_path)
            public_url = upload_for_meta_download(mutated_output)
            publish_reel_to_instagram(acc["ig_user_id"], public_url, caption_batch[index], acc["token"])
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

    log(f"\n=== WAVE COMPLETE: {success_count}/{len(wave_accounts)} HIGH-CONVERTING REELS PUBLISHED ===")
    if success_count == 0:
        raise RuntimeError("0 Reels were published in this wave! Check node error logs above.")

if __name__ == "__main__":
    main()
