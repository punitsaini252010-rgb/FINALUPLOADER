import os
import re
import sys
import time
import urllib.parse
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

# 1 Master Reel per wave -> 23 unique 4K variations across all 23 accounts -> Never reposted again
ACCOUNTS_PER_WAVE = 23

# Randomized publishing delay strictly within 2 minutes (15 to 120 seconds)
MIN_COOLDOWN_SECONDS = 15
MAX_COOLDOWN_SECONDS = 120

LINKS_FILE = "reel_links.txt"
HISTORY_FILE = "posted_history.txt"
CURSOR_FILE = "account_cursor.txt"
ASSETS_DIR = "assets"
CUSTOM_FONT_PATH = "Montserrat-ExtraBold.ttf"

# False = Keep the premade reel's original beat-synced audio (with invisible per-account hash mutation)
# True  = Replace audio with a track from CUSTOM_SONG_LIBRARY
USE_CUSTOM_SONG_OVER_EDIT = False

CUSTOM_SONG_LIBRARY = [
    "https://assets.mixkit.co/music/403/403.mp3",
    "https://assets.mixkit.co/music/841/841.mp3",
    "https://assets.mixkit.co/music/171/171.mp3",
    "https://assets.mixkit.co/music/130/130.mp3",
    "https://assets.mixkit.co/music/132/132.mp3",
    "https://assets.mixkit.co/music/371/371.mp3"
]

PREMADE_VIRAL_EDIT_QUERIES = [
    "dark luxury lifestyle edit",
    "billionaire aesthetic velocity edit",
    "wealth mindset luxury edit",
    "old money dark aesthetic edit",
    "supercar night velocity edit",
    "private jet night aesthetic edit",
    "high status men luxury edit"
]

VERIFIED_LUXURY_VIDEO_IDS = [
    "44559", "36289", "32991", "17256", "86", "40248",
    "151", "41576", "35540", "39912", "4978", "4308",
    "52427", "40766", "41587", "41585", "41575", "41614"
]

MIXKIT_DISCOVERY_PAGES = [
    "https://mixkit.co/free-stock-video/discover/luxury/?orientation=vertical",
    "https://mixkit.co/free-stock-video/discover/suit/?orientation=vertical",
    "https://mixkit.co/free-stock-video/car/",
    "https://mixkit.co/free-stock-video/city/",
    "https://mixkit.co/free-stock-video/business/"
]

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.tikwm.com",
    "Referer": "https://www.tikwm.com/"
}

# ==========================================
# 2. COHESIVE PSYCHOLOGICAL COPY & CAPTIONS
# ==========================================
# Permanent Signature Ending (Last 30% of every Reel across all 23 accounts) in stylized all-caps font
ARC_FINAL_LINE_1 = "ＥＳＣＡＰＥ ＴＨＥ ＲＡＣＥ ＡＮＤ ＢＥＣＯＭＥ ＳＵＣＣＥＳＳＦＵＬ, ＣＯＭＥ ＪＯＩℕ ＡＲＣ"
ARC_FINAL_LINE_2 = "ＷＥＡＬＴＨ • ＰＯＷＥＲ • ＦＲＥＥＤＯＭ • ＠ＡＲＣＢＬＯＯＤＬＩＮＥ３０"

ARC_TOP_HOOKS = [
    "SALARIES ARE BRIBES  •  ＡＲＣ",
    "BROKE MEN SCROLL  •  ＡＲＣ",
    "OBEDIENCE IS EXPENSIVE  •  ＡＲＣ",
    "HARD WORK LIES  •  ＡＲＣ",
    "STOP RENTING LIFE  •  ＡＲＣ",
    "COMFORT KILLS EMPIRES  •  ＡＲＣ",
    "WEAK MEN WAIT  •  ＡＲＣ",
    "MONEY OBEYS LEVERAGE  •  ＡＲＣ",
    "OWN THE MACHINE  •  ＡＲＣ",
    "THE 9-5 CAGE  •  ＡＲＣ",
    "BUILT FOR THE 1%  •  ＡＲＣ",
    "ESCAPE THE MATRIX  •  ＡＲＣ",
    "YOUR SALARY IS A TAX  •  ＡＲＣ",
    "STAY POOR OR BUILD  •  ＡＲＣ",
    "COMFORT IS A TRAP  •  ＡＲＣ",
    "MASTERS OR PAWNS  •  ＡＲＣ"
]

ARC_UNIFIED_MESSAGES = [
    (hook, ARC_FINAL_LINE_1, ARC_FINAL_LINE_2) for hook in ARC_TOP_HOOKS
]

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
    "@ARCBLOODLINE30 Leave the matrix to the spectators. Build with the architects at @ARCBLOODLINE30.",
    "@ARCBLOODLINE30 Fortune favours the organized. Claim your position inside @ARCBLOODLINE30.",
    "@ARCBLOODLINE30 Men of substance do not wait for permission. Enter the circle at @ARCBLOODLINE30.",
    "@ARCBLOODLINE30 Escape the consumer trap. Build sovereign assets with @ARCBLOODLINE30.",
    "@ARCBLOODLINE30 The rules were written to keep you compliant. Rewrite them inside @ARCBLOODLINE30."
]

def generate_unique_caption_batch(count):
    pool = list(ARC_AUTHORITY_CAPTIONS)
    random.shuffle(pool)
    micro_tags = ["", " ⚡", " 🗝️", " ↓", " ▪️"]
    return [f"{pool[i % len(pool)]}{random.choice(micro_tags)}".strip() for i in range(count)]

# ==========================================
# 3. UNIVERSAL MOBILE & WEB LINK RESOLVER + LEDGER
# ==========================================
def resolve_and_normalize_link(raw_line):
    """
    Accepts any mobile app share string or web link (Instagram ?igsh=, TikTok vm./vt./t/, YouTube ?si=, etc.),
    extracts the URL, resolves mobile shortlink redirects, and returns (clean_url, canonical_id).
    """
    if not raw_line:
        return None, None

    match = re.search(r'(https?://[^\s"\'<>]+)', raw_line.strip())
    if not match:
        return None, None

    url = match.group(1).strip()

    if any(short in url.lower() for short in ["vm.tiktok.com", "vt.tiktok.com", "/t/", "ig.me", "pin.it", "bit.ly", "tinyurl.com"]):
        try:
            r = requests.get(url, headers=BROWSER_HEADERS, allow_redirects=True, stream=True, timeout=15)
            if r.url and r.url.startswith("http"):
                url = r.url
            r.close()
        except Exception:
            pass

    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower().replace("m.instagram.com", "www.instagram.com").replace("m.tiktok.com", "www.tiktok.com")
    path = parsed.path.rstrip("/")

    ig_match = re.search(r'/(?:reel|reels|p)/([A-Za-z0-9_-]+)', path)
    if "instagram.com" in host and ig_match:
        shortcode = ig_match.group(1)
        clean_url = f"https://www.instagram.com/reel/{shortcode}/"
        return clean_url, f"ig_{shortcode}"

    tt_match = re.search(r'/video/(\d+)', path)
    if "tiktok.com" in host and tt_match:
        vid_id = tt_match.group(1)
        clean_url = f"https://www.tiktok.com{path}"
        return clean_url, f"tt_{vid_id}"

    yt_match = re.search(r'/(?:shorts|watch)/([A-Za-z0-9_-]{11})', path)
    if ("youtube.com" in host or "youtu.be" in host):
        if yt_match:
            vid_id = yt_match.group(1)
            return f"https://www.youtube.com/shorts/{vid_id}", f"yt_{vid_id}"
        qs = urllib.parse.parse_qs(parsed.query)
        if "v" in qs and qs["v"]:
            vid_id = qs["v"][0]
            return f"https://www.youtube.com/watch?v={vid_id}", f"yt_{vid_id}"

    clean_url = f"{parsed.scheme}://{host}{path}"
    if parsed.query and not any(k in parsed.query.lower() for k in ["igsh", "utm_", "si=", "_t="]):
        clean_url = f"{clean_url}?{parsed.query}"

    return clean_url, clean_url

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

def remove_link_from_queue(raw_line_to_remove, clean_url_to_remove=None):
    if not os.path.exists(LINKS_FILE):
        return
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            c_url, _ = resolve_and_normalize_link(stripped)
            if stripped == raw_line_to_remove.strip() or (clean_url_to_remove and c_url == clean_url_to_remove):
                continue
            f.write(f"{stripped}\n")

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
# 4. MULTI-LAYER MOBILE & WEB REEL DOWNLOADER
# ==========================================
def verify_video_has_real_frames(video_path):
    if not os.path.exists(video_path) or os.path.getsize(video_path) < 120000:
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
        r = requests.post(api_url, data={"url": target_url, "hd": 1}, headers=BROWSER_HEADERS, timeout=20)
        if r.status_code == 200 and r.text.strip().startswith("{"):
            data = r.json().get("data") or {}
            play_url = data.get("hdplay") or data.get("play")
            if play_url:
                if play_url.startswith("/"):
                    play_url = f"https://www.tikwm.com{play_url}"
                vid_bytes = requests.get(play_url, headers=BROWSER_HEADERS, timeout=35).content
                if len(vid_bytes) > 150000:
                    with open(out_path, "wb") as f:
                        f.write(vid_bytes)
                    return verify_video_has_real_frames(out_path)
    except Exception as e:
        log(f"[WARNING] TikWM extractor fallback skipped: {e}")
    return False

def download_instagram_mobile_or_web_reel(clean_url, out_path):
    try:
        vx_url = clean_url.replace("www.instagram.com", "d.ddinstagram.com")
        r = requests.get(vx_url, headers=BROWSER_HEADERS, allow_redirects=True, timeout=25)
        if r.status_code == 200 and len(r.content) > 150000 and "video" in r.headers.get("Content-Type", "").lower():
            with open(out_path, "wb") as f:
                f.write(r.content)
            if verify_video_has_real_frames(out_path):
                return True
    except Exception:
        pass

    ydl_opts = {
        "format": "bestvideo[height<=1920][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": out_path,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 25,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(clean_url, download=True)
        if verify_video_has_real_frames(out_path):
            return True
    except Exception:
        pass

    return False

def fetch_unblocked_premade_viral_edits(posted_history):
    discovered = []
    queries = random.sample(PREMADE_VIRAL_EDIT_QUERIES, min(3, len(PREMADE_VIRAL_EDIT_QUERIES)))

    for query in queries:
        log(f"[AUTO-HARVESTER] Searching premade viral edits for: '{query}'...")
        try:
            r = requests.post(
                "https://www.tikwm.com/api/feed/search",
                data={"keywords": query, "count": 25, "cursor": random.randint(0, 10)},
                headers=BROWSER_HEADERS,
                timeout=20
            )
            if r.status_code == 200 and r.text.strip().startswith("{"):
                res = r.json()
                videos = (res.get("data") or {}).get("videos") or []
                for v in videos:
                    vid_id = f"tt_{v.get('video_id', '')}"
                    duration = int(v.get("duration", 15))
                    play_url = v.get("play") or v.get("wmplay")
                    if play_url and 6 <= duration <= 22 and vid_id not in posted_history:
                        if play_url.startswith("/"):
                            play_url = f"https://www.tikwm.com{play_url}"
                        discovered.append((vid_id, play_url))
                if discovered:
                    break
            else:
                time.sleep(1.5)
        except Exception as e:
            log(f"[WARNING] TikWM search retry ({query}): {e}")
            time.sleep(1.5)

    random.shuffle(discovered)
    return discovered

def harvest_live_mixkit_luxury_mp4s(posted_history):
    discovered_urls = []
    for page_url in random.sample(MIXKIT_DISCOVERY_PAGES, min(3, len(MIXKIT_DISCOVERY_PAGES))):
        try:
            r = requests.get(page_url, headers=BROWSER_HEADERS, timeout=15)
            if r.status_code == 200:
                ids = re.findall(r'/free-stock-video/[a-z0-9\-]+-(\d+)/', r.text)
                for vid_id in ids:
                    mp4_url = f"https://assets.mixkit.co/videos/{vid_id}/{vid_id}-720.mp4"
                    if mp4_url not in posted_history and mp4_url not in discovered_urls:
                        discovered_urls.append(mp4_url)
        except Exception:
            pass

    fallback_ids = list(VERIFIED_LUXURY_VIDEO_IDS)
    random.shuffle(fallback_ids)
    for vid_id in fallback_ids:
        mp4_url = f"https://assets.mixkit.co/videos/{vid_id}/{vid_id}-720.mp4"
        if mp4_url not in posted_history and mp4_url not in discovered_urls:
            discovered_urls.append(mp4_url)

    return discovered_urls

def ingest_single_master_reel_for_wave(posted_history):
    os.makedirs(ASSETS_DIR, exist_ok=True)

    raw_queue_lines = []
    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, "r", encoding="utf-8") as f:
            raw_queue_lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

    for raw_line in raw_queue_lines:
        clean_url, canonical_id = resolve_and_normalize_link(raw_line)
        if not clean_url:
            remove_link_from_queue(raw_line)
            continue

        if canonical_id in posted_history or clean_url in posted_history or raw_line in posted_history:
            log(f"[SKIP] Reel already used in past wave ({canonical_id}). Removing from queue...")
            remove_link_from_queue(raw_line, clean_url)
            continue

        safe_id = abs(hash(canonical_id)) % (10 ** 8)
        full_path = os.path.join(ASSETS_DIR, f"master_wave_{safe_id}.mp4")
        log(f"[STEP 1/4] Ingesting Master Reel (Mobile/Web Link): {clean_url}")

        downloaded = False

        if clean_url.lower().endswith(".mp4"):
            try:
                r = requests.get(clean_url, headers=BROWSER_HEADERS, timeout=(10, 40))
                if r.status_code == 200 and len(r.content) > 150000:
                    with open(full_path, "wb") as f:
                        f.write(r.content)
                    downloaded = verify_video_has_real_frames(full_path)
            except Exception:
                pass

        if not downloaded and "tiktok.com" in clean_url.lower():
            downloaded = download_via_tikwm_api(clean_url, full_path)

        if not downloaded and "instagram.com" in clean_url.lower():
            downloaded = download_instagram_mobile_or_web_reel(clean_url, full_path)

        if not downloaded:
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
                    ydl.extract_info(clean_url, download=True)
                downloaded = verify_video_has_real_frames(full_path)
            except Exception as e:
                log(f"[WARNING] Link extraction failed ({clean_url}): {e}")

        append_to_set_file(HISTORY_FILE, canonical_id, posted_history)
        append_to_set_file(HISTORY_FILE, clean_url, posted_history)
        append_to_set_file(HISTORY_FILE, raw_line, posted_history)
        remove_link_from_queue(raw_line, clean_url)

        if downloaded:
            log(f"[MASTER LOCKED] Loaded {os.path.basename(full_path)} for all 23 variations & wiped from queue.")
            return full_path

    premade_candidates = fetch_unblocked_premade_viral_edits(posted_history)
    for vid_id, play_url in premade_candidates:
        full_path = os.path.join(ASSETS_DIR, f"master_{vid_id}.mp4")
        try:
            log(f"[STEP 1/4] Fetching premade viral master edit ({vid_id})...")
            r = requests.get(play_url, headers=BROWSER_HEADERS, timeout=35)
            if r.status_code == 200 and len(r.content) > 150000:
                with open(full_path, "wb") as f:
                    f.write(r.content)
                if verify_video_has_real_frames(full_path):
                    append_to_set_file(HISTORY_FILE, vid_id, posted_history)
                    log(f"[MASTER LOCKED] Premade viral edit verified for wave: {os.path.basename(full_path)}")
                    return full_path
        except Exception:
            continue

    log("[FALLBACK HARVESTER] Pulling direct HD luxury/supercar master stream...")
    luxury_mp4s = harvest_live_mixkit_luxury_mp4s(posted_history)
    for mp4_url in luxury_mp4s:
        safe_id = abs(hash(mp4_url)) % (10 ** 8)
        full_path = os.path.join(ASSETS_DIR, f"luxury_master_{safe_id}.mp4")
        try:
            r = requests.get(mp4_url, headers=BROWSER_HEADERS, timeout=(10, 35))
            if r.status_code == 200 and len(r.content) > 120000:
                with open(full_path, "wb") as f:
                    f.write(r.content)
                if verify_video_has_real_frames(full_path):
                    append_to_set_file(HISTORY_FILE, mp4_url, posted_history)
                    log(f"[MASTER LOCKED] HD Luxury master stream ready: {os.path.basename(full_path)}")
                    return full_path
        except Exception:
            continue

    raise RuntimeError("All 3 video harvester layers failed! Check network connectivity.")

def get_random_custom_song():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    valid_songs = [s.strip() for s in CUSTOM_SONG_LIBRARY if s and s.strip()]
    if not valid_songs:
        return None

    random.shuffle(valid_songs)
    for song_url in valid_songs:
        safe_id = abs(hash(song_url)) % (10 ** 8)
        out_path = os.path.join(ASSETS_DIR, f"song_{safe_id}.mp3")
        if os.path.exists(out_path) and os.path.getsize(out_path) > 30000:
            return out_path
        try:
            r = requests.get(song_url, headers=BROWSER_HEADERS, timeout=25)
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

def mutate_video_for_account(input_path, output_path, font_path, node_idx=0):
    log(f"[STEP 2/4] Rendering 4K HDR Variation #{node_idx + 1} + Anti-AI Stealth Hash ({os.path.basename(input_path)})...")

    raw_dur = get_media_duration(input_path)
    trim_start = round(random.uniform(0.03, 0.18), 3) if raw_dur > 6.0 else 0.0
    speed = round(random.uniform(0.993, 1.007), 4)
    final_duration = round(min(18.0, max(5.5, (raw_dur - trim_start - 0.08) / speed)), 2)

    last_30_start = round(final_duration * 0.70, 2)

    crop_keep = round(random.uniform(0.985, 0.994), 4)
    x_jitter = random.randint(-3, 3)
    y_jitter = random.randint(-3, 3)

    b_shift = round(random.uniform(0.002, 0.014), 4)
    c_shift = round(random.uniform(1.075, 1.115), 4)
    s_shift = round(random.uniform(1.120, 1.175), 4)
    g_shift = round(random.uniform(0.965, 0.990), 4)
    luma_sharp = round(random.uniform(0.94, 1.14), 2)

    rs = round(random.uniform(-0.018, -0.006), 4)
    gs = round(random.uniform(-0.008, 0.006), 4)
    bs = round(random.uniform(0.008, 0.022), 4)
    rh = round(random.uniform(0.005, 0.018), 4)
    gh = round(random.uniform(0.002, 0.012), 4)
    bh = round(random.uniform(-0.014, -0.004), 4)

    epoch_jitter = int(time.time()) - random.randint(600, 259200)

    msg_tuple = ARC_UNIFIED_MESSAGES[(node_idx + random.randint(0, len(ARC_UNIFIED_MESSAGES) - 1)) % len(ARC_UNIFIED_MESSAGES)]
    top_hook, center_line1, center_line2 = [t.replace("'", "") for t in msg_tuple]

    top_x_offset = random.randint(-6, 6)
    top_y = random.randint(250, 315)

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
        f"drawtext=fontfile={font_path}:text='{top_hook}':expansion=none:"
        f"fontcolor=white@0.92:fontsize=38:shadowcolor=black@0.85:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.58:boxborderw=14:"
        f"x=(w-text_w)/2+{top_x_offset}:y={top_y}:enable='lt(t,{last_30_start})',"
        f"drawbox=x=0:y={band_y}:w=iw:h=195:color=black@0.48:t=fill:enable='gte(t,{last_30_start})',"
        f"drawtext=fontfile={font_path}:text='{center_line1}':expansion=none:"
        f"fontcolor=white:fontsize=28:shadowcolor=black@0.95:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.88:boxborderw=16:"
        f"x=(w-text_w)/2:y={c1_y}:enable='gte(t,{last_30_start})',"
        f"drawtext=fontfile={font_path}:text='{center_line2}':expansion=none:"
        f"fontcolor=0xFFD700:fontsize=24:shadowcolor=black@0.95:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.88:boxborderw=16:"
        f"x=(w-text_w)/2:y={c2_y}:enable='gte(t,{last_30_start})'"
    )

    crf_val = str(random.choice([18, 19]))
    fade_out_st = round(max(1.0, final_duration - 0.7), 2)
    has_orig_audio = video_has_audio_stream(input_path)

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
            "-stream_loop", "-1", "-ss", str(trim_start), "-t", str(final_duration), "-i", input_path,
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
            cmd = [
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-stream_loop", "-1", "-ss", str(trim_start), "-t", str(final_duration), "-i", input_path,
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
# 8. MAIN EXECUTION (1 MASTER REEL -> 23 VARIATIONS PER WAVE)
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

    master_video = ingest_single_master_reel_for_wave(posted_history)
    success_count = 0

    try:
        for index, acc in enumerate(wave_accounts):
            log(f"\n--- NODE [{index+1}/{len(wave_accounts)}]: {acc['page_name']} ({acc['ig_user_id']}) ---")
            mutated_output = f"arc_4k_stealth_{index}.mp4"

            try:
                mutate_video_for_account(master_video, mutated_output, font_path, node_idx=index)
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
    finally:
        if master_video and os.path.exists(master_video):
            os.remove(master_video)

    log(f"\n=== WAVE COMPLETE: {success_count}/{len(wave_accounts)} UNIQUE 4K VARIATIONS OF MASTER REEL PUBLISHED ===")
    if success_count == 0:
        raise RuntimeError("0 Reels were published in this wave! Check node error logs above.")

if __name__ == "__main__":
    main()
