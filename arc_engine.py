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
# 1. CORE CONFIGURATION & TIMING
# ==========================================
META_TOKENS = [
    os.getenv("META_TOKEN_1"),
    os.getenv("META_TOKEN_2")
]

GRAPH_API_VERSION = "v20.0"

ACCOUNTS_PER_WAVE = 23
# 1 = Every account gets a different premade reel | 23 = All 23 accounts post 1 mutated master reel per wave
MAX_ACCOUNTS_PER_VIDEO = 1

# Randomized publishing delay within 2 minutes (25 to 120 seconds)
MIN_COOLDOWN_SECONDS = 25
MAX_COOLDOWN_SECONDS = 120

LINKS_FILE = "reel_links.txt"
HISTORY_FILE = "posted_history.txt"
CURSOR_FILE = "account_cursor.txt"
ASSETS_DIR = "assets"
CUSTOM_FONT_PATH = "Montserrat-ExtraBold.ttf"

# False = Keep the premade reel's original beat-synced audio (with invisible hash mutation)
# True  = Replace audio with a track from CUSTOM_SONG_LIBRARY
USE_CUSTOM_SONG_OVER_EDIT = False

CUSTOM_SONG_LIBRARY = [
    "https://assets.mixkit.co/music/403/403.mp3",
    "https://assets.mixkit.co/music/841/841.mp3",
    "https://assets.mixkit.co/music/171/171.mp3",
    "https://assets.mixkit.co/music/130/130.mp3"
]

# Unblocked Viral Edit Search Queries (Used automatically if reel_links.txt runs dry)
PREMADE_VIRAL_EDIT_QUERIES = [
    "dark luxury lifestyle edit",
    "billionaire aesthetic velocity edit",
    "wealth mindset luxury edit",
    "old money dark aesthetic edit",
    "supercar night velocity edit",
    "private jet night aesthetic edit",
    "high status men luxury edit"
]

# ==========================================
# 2. COHESIVE PSYCHOLOGICAL COPY & CAPTIONS (PURE ARC — ZERO "$100" MENTIONS)
# ==========================================
# Format: (Upper-Middle 1-2 Word Hook [First 70%], Center Line 1 [Last 30%], Center Line 2 [Last 30%])
ARC_UNIFIED_MESSAGES = [
    ("ARC.", "WEALTH IS QUIET. POWER IS ORGANIZED.", "THE GATES ARE OPEN  •  @ARCBLOODLINE30"),
    ("THE EXIT.", "MOST OBEY THE SYSTEM.", "THE ELITE BUILD OUTSIDE IT  •  @ARCBLOODLINE30"),
    ("CONTROL.", "EITHER YOU OWN THE MACHINE", "OR YOU WORK FOR IT  •  @ARCBLOODLINE30"),
    ("REALITY.", "COMFORT IS A MODERN CAGE.", "EXECUTION IS THE ONLY WAY OUT  •  @ARCBLOODLINE30"),
    ("BLOODLINE.", "A DIFFERENT STANDARD OF MEN.", "STEP INSIDE THE CIRCLE  •  @ARCBLOODLINE30"),
    ("LEVERAGE.", "HARD WORK PAYS BILLS.", "SYSTEMS BUILD DYNASTIES  •  @ARCBLOODLINE30"),
    ("AWAKE.", "THEY TRAINED YOU TO CONSUME.", "WE BUILT ARC TO RULE  •  @ARCBLOODLINE30"),
    ("ASCEND.", "AVERAGE IS A DAILY CHOICE.", "ACCESS THE BLUEPRINT  •  @ARCBLOODLINE30"),
    ("DOMINION.", "MONEY FOLLOWS AUTHORITY.", "YOU KNOW WHERE TO LOOK  •  @ARCBLOODLINE30"),
    ("SILENCE.", "NO NOISE. JUST POWER.", "ENTER THE TERMINAL  •  @ARCBLOODLINE30"),
    ("THE CODE.", "99% WATCH FROM THE SIDELINES.", "THE 1% MOVE IN SILENCE  •  @ARCBLOODLINE30"),
    ("SOVEREIGN.", "NOBODY IS COMING TO SAVE YOU.", "BUILD YOUR OWN EMPIRE  •  @ARCBLOODLINE30")
]

# Formatted Authority Captions (@ARCBLOODLINE30 front-loaded, zero "$100 kit" mentions)
ARC_AUTHORITY_CAPTIONS = [
    "@ARCBLOODLINE30 Most men spend their lives building someone else's empire. The exit is in the bio.",
    "@ARCBLOODLINE30 Wealth is not luck. It is architecture. Step inside @ARCBLOODLINE30.",
    "@ARCBLOODLINE30 The modern world is designed to keep you distracted and broke. Break the cycle via @ARCBLOODLINE30.",
    "@ARCBLOODLINE30 You do not rise to the level of your goals. You fall to the level of your systems. -> @ARCBLOODLINE30",
    "@ARCBLOODLINE30 Silence the noise. Build real leverage. The private terminal is open in @ARCBLOODLINE30 bio.",
    "@ARCBLOODLINE30 Average minds look for entertainment. Elite minds look for leverage. Tap @ARCBLOODLINE30.",
    "@ARCBLOODLINE30 Freedom is never given. It is engineered. Enter ARC through @ARCBLOODLINE30.",
    "@ARCBLOODLINE30 Every day you wait is another day you trade your time for pennies. @ARCBLOODLINE30",
    "@ARCBLOODLINE30 Power belongs to those who understand the system. The blueprint is waiting in @ARCBLOODLINE30 bio.",
    "@ARCBLOODLINE30 Surround yourself with men who refuse to lose. Tap @ARCBLOODLINE30 to enter ARC.",
    "@ARCBLOODLINE30 Comfort destroys ambition. Discipline builds dynasties. -> @ARCBLOODLINE30",
    "@ARCBLOODLINE30 Stop watching others live the life you were meant to build. Start inside @ARCBLOODLINE30.",
    "@ARCBLOODLINE30 A weak environment creates weak results. Upgrade your network inside @ARCBLOODLINE30.",
    "@ARCBLOODLINE30 They want you obedient. We want you unstoppable. Link in @ARCBLOODLINE30 bio.",
    "@ARCBLOODLINE30 While the world sleeps, the inner circle executes. Tap @ARCBLOODLINE30.",
    "@ARCBLOODLINE30 Control your income. Control your time. Control your bloodline. -> @ARCBLOODLINE30",
    "@ARCBLOODLINE30 No excuses. No handouts. Just raw execution inside @ARCBLOODLINE30.",
    "@ARCBLOODLINE30 The gap between the rich and the rest is information and speed. Tap @ARCBLOODLINE30.",
    "@ARCBLOODLINE30 Stop trading decades for a paycheck. The new standard is @ARCBLOODLINE30.",
    "@ARCBLOODLINE30 Only those who move first claim the territory. Enter via @ARCBLOODLINE30 bio.",
    "@ARCBLOODLINE30 Master the psychology of wealth. The doors to ARC are open at @ARCBLOODLINE30.",
    "@ARCBLOODLINE30 Your bloodline depends on the decisions you make today. -> @ARCBLOODLINE30",
    "@ARCBLOODLINE30 Real authority never begs for attention. If you are ready, tap @ARCBLOODLINE30.",
    "@ARCBLOODLINE30 Leave the matrix to the spectators. Build with the architects at @ARCBLOODLINE30."
]

def generate_unique_caption_batch(count):
    pool = list(ARC_AUTHORITY_CAPTIONS)
    random.shuffle(pool)
    micro_tags = ["", " ⚡", " 🗝️", " ↓", " ▪️"]
    return [f"{pool[i % len(pool)]}{random.choice(micro_tags)}".strip() for i in range(count)]

# ==========================================
# 3. QUEUE & LEDGER MANAGERS
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
# 4. PREMADE VIRAL REEL HARVESTER & DOWNLOADER
# ==========================================
def verify_video_has_real_frames(video_path):
    if not os.path.exists(video_path) or os.path.getsize(video_path) < 150000:
        return False
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", video_path
        ]
        res = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        dims = res.stdout.decode("utf-8").strip().split("x")
        return int(dims[0]) >= 480 and int(dims[1]) >= 480
    except Exception:
        return False

def video_has_audio_stream(video_path):
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "a",
            "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path
        ]
        res = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        return len(res.stdout.decode("utf-8").strip()) > 0
    except Exception:
        return False

def download_via_tikwm_api(target_url, out_path):
    try:
        api_url = "https://www.tikwm.com/api/"
        res = requests.post(api_url, data={"url": target_url, "hd": 1}, timeout=20).json()
        data = res.get("data") or {}
        play_url = data.get("hdplay") or data.get("play")
        if play_url:
            vid_bytes = requests.get(play_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=35).content
            if len(vid_bytes) > 150000:
                with open(out_path, "wb") as f:
                    f.write(vid_bytes)
                return verify_video_has_real_frames(out_path)
    except Exception as e:
        log(f"[WARNING] TikWM extractor fallback failed: {e}")
    return False

def fetch_unblocked_premade_viral_edits(posted_history):
    query = random.choice(PREMADE_VIRAL_EDIT_QUERIES)
    log(f"[AUTO-HARVESTER] Searching premade viral edits for: '{query}'...")
    discovered = []
    try:
        res = requests.post(
            "https://www.tikwm.com/api/feed/search",
            data={"keywords": query, "count": 25, "cursor": random.randint(0, 15)},
            timeout=20
        ).json()
        videos = (res.get("data") or {}).get("videos") or []
        for v in videos:
            vid_id = str(v.get("video_id", ""))
            duration = int(v.get("duration", 15))
            play_url = v.get("play") or v.get("wmplay")
            if play_url and 6 <= duration <= 22 and vid_id not in posted_history:
                discovered.append((vid_id, play_url))
    except Exception as e:
        log(f"[WARNING] Auto-harvester search error: {e}")

    random.shuffle(discovered)
    return discovered

def ingest_single_fresh_reel(posted_history):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    queue_urls = []
    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, "r", encoding="utf-8") as f:
            queue_urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    unposted_queue = [u for u in queue_urls if u not in posted_history]

    # 1. First priority: Links in reel_links.txt
    for target_url in unposted_queue:
        safe_id = abs(hash(target_url)) % (10 ** 8)
        full_path = os.path.join(ASSETS_DIR, f"premade_{safe_id}.mp4")
        log(f"[STEP 1/4] Downloading premade reel from queue: {target_url}")

        if target_url.lower().endswith(".mp4"):
            try:
                r = requests.get(target_url, headers=headers, timeout=(10, 40))
                if r.status_code == 200 and len(r.content) > 150000:
                    with open(full_path, "wb") as f:
                        f.write(r.content)
                    if verify_video_has_real_frames(full_path):
                        append_to_set_file(HISTORY_FILE, target_url, posted_history)
                        remove_link_from_queue(target_url)
                        return full_path
            except Exception:
                pass

        if "tiktok.com" in target_url.lower():
            if download_via_tikwm_api(target_url, full_path):
                append_to_set_file(HISTORY_FILE, target_url, posted_history)
                remove_link_from_queue(target_url)
                log(f"[SUCCESS] Premade TikTok edit downloaded: {os.path.basename(full_path)}")
                return full_path

        ydl_opts = {
            "format": "bestvideo[height<=1920][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": full_path,
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 25,
            "playlist_items": "1"
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(target_url, download=True)
            if verify_video_has_real_frames(full_path):
                append_to_set_file(HISTORY_FILE, target_url, posted_history)
                remove_link_from_queue(target_url)
                log(f"[SUCCESS] Premade queue edit ready: {os.path.basename(full_path)}")
                return full_path
        except Exception as e:
            log(f"[WARNING] Queue link skipped ({target_url}): {e}")
            append_to_set_file(HISTORY_FILE, target_url, posted_history)
            remove_link_from_queue(target_url)

    # 2. Second priority: Unblocked viral edit harvester
    premade_candidates = fetch_unblocked_premade_viral_edits(posted_history)
    for vid_id, play_url in premade_candidates:
        full_path = os.path.join(ASSETS_DIR, f"viral_edit_{vid_id}.mp4")
        try:
            log(f"[STEP 1/4] Fetching premade viral edit ID {vid_id}...")
            r = requests.get(play_url, headers=headers, timeout=35)
            if r.status_code == 200 and len(r.content) > 150000:
                with open(full_path, "wb") as f:
                    f.write(r.content)
                if verify_video_has_real_frames(full_path):
                    append_to_set_file(HISTORY_FILE, vid_id, posted_history)
                    log(f"[SUCCESS] Premade viral edit verified: {os.path.basename(full_path)}")
                    return full_path
        except Exception:
            continue

    raise RuntimeError("Could not fetch a premade reel! Add direct MP4 or TikTok/IG links to reel_links.txt.")

def get_random_custom_song():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    valid_songs = [s.strip() for s in CUSTOM_SONG_LIBRARY if s and s.strip()]
    if not valid_songs:
        return None

    random.shuffle(valid_songs)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for song_url in valid_songs:
        safe_id = abs(hash(song_url)) % (10 ** 8)
        out_path = os.path.join(ASSETS_DIR, f"song_{safe_id}.mp3")
        if os.path.exists(out_path) and os.path.getsize(out_path) > 30000:
            return out_path
        try:
            r = requests.get(song_url, headers=headers, timeout=25)
            if r.status_code == 200 and len(r.content) > 30000:
                with open(out_path, "wb") as f:
                    f.write(r.content)
                return out_path
        except Exception:
            continue
    return None

# ==========================================
# 5. INSTAGRAM GRAPH API ACCOUNT DISCOVERY
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
# 6. 4K REMASTERING + INVISIBLE STEALTH MUTATION ENGINE
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
    log(f"[STEP 2/4] 4K HDR Remastering + Invisible Anti-AI Mutation ({os.path.basename(input_path)})...")

    raw_dur = get_media_duration(input_path)
    # Imperceptible start trim (0.04s to 0.16s) shifts all keyframe intervals
    trim_start = round(random.uniform(0.04, 0.16), 3) if raw_dur > 6.0 else 0.0
    # Sub-1% speed shift: 100% invisible to human eyes/ears, completely breaks frame-timing & optical-flow hashes
    speed = round(random.uniform(0.993, 1.007), 4)
    final_duration = round(min(18.0, max(5.5, (raw_dur - trim_start - 0.08) / speed)), 2)

    # Exact 70% / 30% split: Hook runs 0 -> 70%, Center Authority Finale runs last 30%
    last_30_start = round(final_duration * 0.70, 2)

    # Invisible micro-crop (98.6% to 99.4%) + 1-3px shift breaks spatial macroblock alignment
    crop_keep = round(random.uniform(0.986, 0.994), 4)
    x_jitter = random.randint(-3, 3)
    y_jitter = random.randint(-3, 3)

    # 4K HDR Visual Enhancer Parameters (Crisp contrast, rich saturation, deep midtone gamma)
    b_shift = round(random.uniform(0.002, 0.014), 4)
    c_shift = round(random.uniform(1.075, 1.115), 4)
    s_shift = round(random.uniform(1.120, 1.175), 4)
    g_shift = round(random.uniform(0.965, 0.990), 4)
    luma_sharp = round(random.uniform(0.92, 1.12), 2)

    # Subtle Color Temperature & Toning (Cool cinematic shadows, crisp clean highlights, unique per account)
    rs = round(random.uniform(-0.018, -0.006), 4)
    gs = round(random.uniform(-0.008, 0.006), 4)
    bs = round(random.uniform(0.008, 0.022), 4)
    rh = round(random.uniform(0.005, 0.018), 4)
    gh = round(random.uniform(0.002, 0.012), 4)
    bh = round(random.uniform(-0.014, -0.004), 4)

    epoch_jitter = int(time.time()) - random.randint(600, 259200)

    # Select a unified single-message sequence (Hook + matching Last-30% Center Finale)
    top_hook, center_line1, center_line2 = [t.replace("'", "") for t in random.choice(ARC_UNIFIED_MESSAGES)]

    # Dynamic safe-zone positioning to avoid colliding with baked-in reel texts
    # Upper-middle top hook sits between y=255 and y=315 (clears top UI and stays above center subtitles)
    top_x_offset = random.randint(-6, 6)
    top_y = random.randint(255, 315)

    # Middle-center finale (last 30%) with slight vertical adaptation around screen center
    center_y_shift = random.choice([-45, -20, 0, 20, 45])
    c1_y = f"(h/2)-55+{center_y_shift}"
    c2_y = f"(h/2)+22+{center_y_shift}"
    band_y = f"(h/2)-105+{center_y_shift}"

    vf_chain = (
        f"setpts=PTS/{speed},"
        f"crop=iw*{crop_keep}:ih*{crop_keep}:(iw-ow)/2+{x_jitter}:(ih-oh)/2+{y_jitter},"
        f"scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos+accurate_rnd+full_chroma_int,"
        f"crop=1080:1920,fps=30,"
        f"colorbalance=rs={rs}:gs={gs}:bs={bs}:rh={rh}:gh={gh}:bh={bh},"
        f"eq=brightness={b_shift}:contrast={c_shift}:saturation={s_shift}:gamma={g_shift},"
        f"unsharp=lx=5:ly=5:la={luma_sharp}:cx=3:cy=3:ca=0.25,"
        f"noise=alls=1:allf=t,"
        # STAGE 1 (First 70%): 1-2 Word Upper-Middle Top Hook
        f"drawtext=fontfile={font_path}:text='{top_hook}':expansion=none:"
        f"fontcolor=white@0.92:fontsize=38:shadowcolor=black@0.85:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.58:boxborderw=14:"
        f"x=(w-text_w)/2+{top_x_offset}:y={top_y}:enable='lt(t,{last_30_start})',"
        # STAGE 2 (Last 30%): Middle-Center Authority Message + Subtle ARC Direction
        f"drawbox=x=0:y={band_y}:w=iw:h=195:color=black@0.45:t=fill:enable='gte(t,{last_30_start})',"
        f"drawtext=fontfile={font_path}:text='{center_line1}':expansion=none:"
        f"fontcolor=white:fontsize=34:shadowcolor=black@0.95:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.88:boxborderw=16:"
        f"x=(w-text_w)/2:y={c1_y}:enable='gte(t,{last_30_start})',"
        f"drawtext=fontfile={font_path}:text='{center_line2}':expansion=none:"
        f"fontcolor=0xFFD700:fontsize=31:shadowcolor=black@0.95:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.88:boxborderw=16:"
        f"x=(w-text_w)/2:y={c2_y}:enable='gte(t,{last_30_start})'"
    )

    crf_val = str(random.choice([18, 19]))
    fade_out_st = round(max(1.0, final_duration - 0.7), 2)
    has_orig_audio = video_has_audio_stream(input_path)

    # Invisible audio fingerprint mutation (micro pitch + randomized EQ notch)
    pitch_shift = round(random.uniform(0.994, 1.006), 4)
    eq_freq = random.randint(1200, 3800)
    eq_gain = random.choice([-1.2, -0.8, 0.8, 1.2])

    if has_orig_audio and not USE_CUSTOM_SONG_OVER_EDIT:
        af_chain = (
            f"asetrate=48000*{pitch_shift},aresample=48000,"
            f"equalizer=f={eq_freq}:width_type=h:width=250:g={eq_gain},"
            f"bass=g=2.5:f=95:w=0.5,volume=1.04,"
            f"afade=t=in:st=0:d=0.25,afade=t=out:st={fade_out_st}:d=0.65"
        )
        cmd = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", str(trim_start), "-t", str(final_duration), "-i", input_path,
            "-map", "0:v:0", "-map", "0:a:0",
            "-vf", vf_chain, "-af", af_chain,
            "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.1",
            "-crf", crf_val, "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-shortest", "-map_metadata", "-1", "-metadata", f"creation_time={epoch_jitter}",
            output_path
        ]
    else:
        custom_song = get_random_custom_song()
        if custom_song and os.path.exists(custom_song):
            song_dur = get_media_duration(custom_song)
            song_start = round(random.uniform(2.0, max(3.0, song_dur - final_duration - 1.0)), 2) if song_dur > final_duration + 4.0 else 0.0
            af_chain = (
                f"asetrate=48000*{pitch_shift},aresample=48000,"
                f"equalizer=f={eq_freq}:width_type=h:width=250:g={eq_gain},"
                f"volume=0.92,afade=t=in:st=0:d=0.35,afade=t=out:st={fade_out_st}:d=0.75"
            )
            cmd = [
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", str(trim_start), "-t", str(final_duration), "-i", input_path,
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
            cmd = [
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", str(trim_start), "-t", str(final_duration), "-i", input_path,
                "-vf", vf_chain,
                "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.1",
                "-crf", crf_val, "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                "-an", "-map_metadata", "-1", "-metadata", f"creation_time={epoch_jitter}",
                output_path
            ]

    result = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    if result.returncode != 0:
        raise Exception(f"FFmpeg failed: {result.stderr.decode('utf-8', errors='ignore')}")
    return output_path

# ==========================================
# 7. RELAY UPLOAD & CLEAN GRAPH API PUBLISH
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
# 8. MAIN EXECUTION
# ==========================================
def main():
    log("=== ARC 4K STEALTH REMASTER & AUTHORITY ENGINE STARTED ===")
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
        mutated_output = f"arc_4k_stealth_{index}.mp4"

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
            cooldown_sec = random.randint(MIN_COOLDOWN_SECONDS, MAX_COOLDOWN_SECONDS)
            log(f"[NATURAL TIMER] Waiting {cooldown_sec // 60}m {cooldown_sec % 60}s (randomized within 2m) before next account upload...")
            time.sleep(cooldown_sec)

    log(f"\n=== WAVE COMPLETE: {success_count}/{len(wave_accounts)} 4K AUTHORITY REELS PUBLISHED ===")
    if success_count == 0:
        raise RuntimeError("0 Reels were published in this wave! Check node error logs above.")

if __name__ == "__main__":
    main()
