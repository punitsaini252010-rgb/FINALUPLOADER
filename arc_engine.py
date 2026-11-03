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
# 1. CONFIGURATION & CUSTOM SONG SETTINGS
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

# Cinematic B-roll background loops
CINEMATIC_BROLL_SOURCES = [
    "https://www.youtube.com/watch?v=LXb3EKWsInQ",
    "https://www.youtube.com/watch?v=3JZ_D3ELwOQ",
    "https://www.youtube.com/watch?v=ScMzIvxBSi4"
]

# =====================================================================
# PASTE YOUR SPECIFIC SONG / BEAT YOUTUBE LINKS HERE:
# =====================================================================
CUSTOM_SONG_LIBRARY = [
    "https://www.youtube.com/watch?v=2S24-y0Ij3Y", # Replace with your 1st specific track URL
    "https://www.youtube.com/watch?v=5qap5aO4i9A"  # Replace with your 2nd specific track URL
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
# 2. AUTO-DOWNLOAD ASSETS & SPECIFIC SONGS
# ==========================================
def download_asset(url, out_template):
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": out_template,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 20
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info.get("id", "unknown")
    except Exception:
        return None

def get_random_custom_song():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    if not CUSTOM_SONG_LIBRARY:
        return None
    song_url = random.choice(CUSTOM_SONG_LIBRARY)
    safe_id = abs(hash(song_url)) % (10 ** 8)
    out_path = os.path.join(ASSETS_DIR, f"song_{safe_id}.mp4")
    
    if not os.path.exists(out_path):
        log(f"[AUDIO] Downloading custom track: {song_url}")
        download_asset(song_url, os.path.join(ASSETS_DIR, f"song_{safe_id}.%(ext)s"))
        
    return out_path if os.path.exists(out_path) else None

def ingest_single_fresh_reel(posted_history):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    if not os.path.exists(LINKS_FILE) or os.path.getsize(LINKS_FILE) < 10:
        with open(LINKS_FILE, "w", encoding="utf-8") as f:
            for src in CINEMATIC_BROLL_SOURCES:
                f.write(f"{src}\n")

    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        all_urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    for target_url in [u for u in all_urls if u not in posted_history]:
        log(f"[STEP 1/4] Downloading cinematic B-roll background: {target_url}")
        vid_id = download_asset(target_url, os.path.join(ASSETS_DIR, "cinematic_%(id)s.%(ext)s"))
        if vid_id:
            full_path = os.path.join(ASSETS_DIR, f"cinematic_{vid_id}.mp4")
            if os.path.exists(full_path):
                append_to_set_file(HISTORY_FILE, target_url, posted_history)
                return full_path
    return None

# ==========================================
# 3. DISCOVER IG ACCOUNTS & QUEUE MANAGERS
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
# 4. CUSTOM FONT & SONG-MIXED KINETIC MASTERING
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
    log(f"[STEP 2/4] Custom Song-Injected Kinetic Mastering ({os.path.basename(input_path)})...")
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

    hook_top, hook_bottom = random.choice(ARC_VALUE_HOOKS)
    cta_line1 = "COMMENT 'ARC' FOR FREE ACCESS"
    cta_line2 = "OR TAP @ARCBLOODLINE30 IN BIO"
    wm_x_offset = random.randint(-6, 6)
    wm_y = 340 + random.randint(-8, 8)

    vf_chain = (
        f"setpts=PTS/{speed},{flip_filter}"
        f"rotate={angle_deg}*PI/180:bilinear=1:fillcolor=black,"
        f"crop=iw*{crop_keep}:ih*{crop_keep}:(iw-ow)/2+{x_jitter}:(ih-oh)/2+{y_jitter},"
        f"scale=2160:3840:force_original_aspect_ratio=increase:flags=lanczos+accurate_rnd+full_chroma_int,"
        f"crop=2160:3840,"
        f"eq=brightness={b_shift}:contrast={c_shift}:saturation={s_shift},"
        f"noise=alls={noise_level}:allf=t,unsharp=5:5:0.34:5:5:0.0,"
        f"drawtext=fontfile={font_path}:text='ARC':expansion=none:"
        f"fontcolor=white@0.35:fontsize=130:shadowcolor=black@0.3:shadowx=3:shadowy=3:"
        f"x=(w-text_w)/2+{wm_x_offset}:y={wm_y},"
        f"drawtext=fontfile={font_path}:text='{hook_top}':expansion=none:"
        f"fontcolor=0xFFD700:fontsize=76:shadowcolor=black@0.9:
