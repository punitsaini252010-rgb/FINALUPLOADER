import os
import re
import sys
import json
import time
import threading
import urllib.parse
import subprocess
import requests
import random
import yt_dlp

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def ensure_edge_tts_installed():
    """Automatically installs edge-tts on the runner if not already present."""
    try:
        subprocess.run(["edge-tts", "--version"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=True)
    except Exception:
        log("[INIT] Installing edge-tts for realistic neural voiceover...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "edge-tts"], stdin=subprocess.DEVNULL, timeout=60)

# ==========================================
# 1. CORE CONFIGURATION & 30-MINUTE BLITZ SETTINGS
# ==========================================
META_TOKENS = [
    os.getenv("META_TOKEN_1"),
    os.getenv("META_TOKEN_2")
]

# Optional: Set ARC_JOIN_LINK in GitHub Secrets (defaults to @arcbloodline30 profile if unset)
ARC_DIRECT_LINK = os.getenv("ARC_JOIN_LINK", "https://www.instagram.com/arcbloodline30/")

GRAPH_API_VERSION = "v20.0"

# 12 accounts per 30-minute wave = All 23 accounts post 1 distinct Reel every hour with zero runner collisions
ACCOUNTS_PER_WAVE = 12
MAX_ACCOUNTS_PER_VIDEO = 1

# Fast stagger so 12 accounts finish inside ~14 minutes per 30-minute cron
MIN_COOLDOWN_SECONDS = 10
MAX_COOLDOWN_SECONDS = 28

LINKS_FILE = "reel_links.txt"
HISTORY_FILE = "posted_history.txt"
REPLIED_COMMENTS_FILE = "replied_comments.txt"
CURSOR_FILE = "account_cursor.txt"
ASSETS_DIR = "assets"
CUSTOM_FONT_PATH = "Montserrat-ExtraBold.ttf"

USE_CUSTOM_SONG_OVER_EDIT = False

CUSTOM_SONG_LIBRARY = [
    "https://assets.mixkit.co/music/403/403.mp3",
    "https://assets.mixkit.co/music/841/841.mp3",
    "https://assets.mixkit.co/music/171/171.mp3",
    "https://assets.mixkit.co/music/130/130.mp3",
    "https://assets.mixkit.co/music/132/132.mp3",
    "https://assets.mixkit.co/music/371/371.mp3"
]

# ==========================================
# TARGET INSTAGRAM ACCOUNTS FOR GRAPH API SCRAPER
# Add or replace any public IG Business/Creator handles here
# ==========================================
TARGET_IG_ACCOUNTS_TO_SCRAPE = [
    "wealth",
    "millionaire_mentor",
    "billionaire.word",
    "luxury_listings",
    "thetrillionairelife",
    "gentbelike",
    "classy_men",
    "onlyforluxury",
    "supercarblondie",
    "mensluxury",
    "luxurylifestylemagazine",
    "richkids_official",
    "billionaires.lifestyle",
    "success.minded",
    "mindset.therapy",
    "entrepreneur_ulia",
    "business.mindset101",
    "oldmoney.aesthetic",
    "dark.luxury.aesthetic",
    "luxurymansions"
]

PREMADE_VIRAL_EDIT_QUERIES = [
    "dark luxury lifestyle velocity edit",
    "billionaire mindset aesthetic edit",
    "old money luxury night edit",
    "supercar night pov velocity edit",
    "private jet billionaire edit",
    "monaco yacht luxury edit",
    "dark psychology wealth edit",
    "high status men luxury edit",
    "rolls royce night aesthetic edit",
    "penthouse night view luxury edit"
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
# 2. HIGH-CONTRAST HOOKS (FIRST 58%) + SHORT TRUST PITCH & VOICEOVER (FINAL 42%)
# ==========================================
ARC_FINAL_LINE_1 = "A R C  -  P R I V A T E   O N L I N E   I N C O M E   S Y S T E M"
ARC_FINAL_LINE_2 = "F I N A L   S P O T S   C L O S I N G   ->   @ A R C B L O O D L I N E 3 0"

# Spoken by the deep neural voiceover during the final 42% while background music ducks to 25%
ARC_VOICEOVER_SCRIPTS = [
    "ARC is the private system where men build real online income. Final spots are closing. Check the bio.",
    "Stop trading your life for a paycheck. Step inside the ARC income system through the bio link right now.",
    "You do not need luck, you need a proven system. Join the private ARC network in the bio before doors lock.",
    "Most men just watch. Builders execute. Enter the ARC online wealth system via the bio link today.",
    "Escape the race and build real digital leverage. Tap the bio link and enter ARC before spots close."
]

# High-contrast colors that immediately pop against dark luxury/supercar edits
HOOK_HIGH_CONTRAST_COLORS = [
    "0xFFE600",  # Signal Yellow
    "0x00F5D4",  # Electric Cyan
    "0xFF3B30",  # Alert Crimson
    "0x00FF66"   # Matrix Neon Green
]

ARC_TOP_HOOKS = [
    "Y O U   A R E   T O O   S M A R T   T O   B E   B R O K E",
    "Y O U R   S A L A R Y   I S   B U Y I N G   Y O U R   S I L E N C E",
    "9 9 %   O F   M E N   D I E   W I T H   R E G R E T",
    "N O B O D Y   I S   C O M I N G   T O   S A V E   Y O U",
    "H A R D   W O R K   W I T H O U T   A   S Y S T E M   F A I L S",
    "W H Y   W A T C H   O T H E R   M E N   L I V E   Y O U R   L I F E ?",
    "T H E   M O N T H L Y   P A Y C H E C K   T R A P",
    "S I L E N C E   T H E   N O I S E .   B U I L D   L E V E R A G E .",
    "C O M F O R T   I S   S L O W L Y   K I L L I N G   Y O U R   F U T U R E",
    "Y O U   D O N T   L A C K   T A L E N T .   Y O U   L A C K   A   S Y S T E M .",
    "S T O P   R E N T I N G   Y O U R   O W N   L I F E",
    "O B E D I E N C E   W I L L   N E V E R   M A K E   Y O U   R I C H"
]

ARC_UNIFIED_MESSAGES = [
    (hook, ARC_FINAL_LINE_1, ARC_FINAL_LINE_2) for hook in ARC_TOP_HOOKS
]

ARC_AUTHORITY_CAPTIONS = [
    (
        "What is ARC?\n\n"
        "ARC is a private online income and business network built to give you the exact digital systems to make money from scratch.\n"
        "• Proven step-by-step execution blueprints\n"
        "• Direct private network of builders & operators\n\n"
        "-> Join ARC now via the link in @ARCBLOODLINE30 bio (or comment 'ARC' for an instant DM).\n\n"
        "#wealth #business #mindset #entrepreneur #success"
    ),
    (
        "Stop watching other men live the life you were meant to build.\n\n"
        "Inside ARC, you get the exact digital business models, automation systems, and private network to build independent cashflow.\n"
        "No fluff. Just raw execution before doors lock.\n\n"
        "-> Tap @ARCBLOODLINE30 and click the bio link to enter ARC right now (or comment 'ARC' below).\n\n"
        "#entrepreneurship #money #luxury #mindset #wealth"
    ),
    (
        "Why 99% of men stay stuck in the paycheck cycle:\n\n"
        "They work hard inside someone else's system instead of owning their own.\n"
        "ARC gives you the complete online income blueprint and private community to build real leverage.\n\n"
        "-> Enter ARC right now via @ARCBLOODLINE30 bio (or drop 'ARC' in the comments for the direct link).\n\n"
        "#success #onlinebusiness #wealth #motivation #mindset"
    ),
    (
        "Read this before you scroll past:\n\n"
        "If you repeat the last 6 months for the next 5 years, nothing changes.\n"
        "We built ARC for men ready to lock in and build automated digital income alongside serious operators.\n\n"
        "-> Claim your spot in @ARCBLOODLINE30 bio before the gates close (or comment 'ARC').\n\n"
        "#wealth #mindset #luxury #business #entrepreneur"
    )
]

def generate_unique_caption_batch(count):
    pool = list(ARC_AUTHORITY_CAPTIONS)
    random.shuffle(pool)
    micro_tags = ["", "\n⚡", "\n🗝️", "\n▪️"]
    return [f"{pool[i % len(pool)]}{random.choice(micro_tags)}".strip() for i in range(count)]

# ==========================================
# 3. REAL-TIME 8-SECOND AUTO-COMMENT & DM CLOSER DAEMON
# ==========================================
def run_realtime_comment_closer(all_accounts, stop_event):
    """
    Polls all 23 accounts in the background every 8 seconds while videos render/upload.
    Instantly replies to any new comment AND sends a private DM with the direct ARC link.
    """
    replied_ids = load_set_file(REPLIED_COMMENTS_FILE)
    log("[REAL-TIME CLOSER] 8-second Instant Comment-to-DM Daemon ACTIVE across all accounts.")

    while not stop_event.is_set():
        for acc in all_accounts:
            if stop_event.is_set():
                break
            ig_id = acc["ig_user_id"]
            page_token = acc.get("page_token") or acc["token"]
            user_token = acc["token"]
            own_username = (acc.get("ig_username") or "").lower()

            try:
                media_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_id}/media"
                m_res = requests.get(
                    media_url,
                    params={"fields": "id,comments.limit(10){id,text,username}", "limit": 5, "access_token": user_token},
                    timeout=10
                ).json()

                for media in m_res.get("data", []):
                    comments = (media.get("comments") or {}).get("data") or []
                    for c in comments:
                        cid = str(c.get("id", ""))
                        c_user = str(c.get("username", "")).lower()
                        if not cid or cid in replied_ids or (own_username and c_user == own_username):
                            continue

                        # 1. Instant Public Comment Reply
                        reply_text = f"@{c.get('username', '')} Sent you the private access link. You can also enter ARC directly via @ARCBLOODLINE30 bio ⚡"
                        requests.post(
                            f"https://graph.facebook.com/{GRAPH_API_VERSION}/{cid}/replies",
                            data={"message": reply_text, "access_token": user_token},
                            timeout=10
                        )

                        # 2. Instant Private DM via Instagram Graph Messaging API
                        dm_payload = {
                            "recipient": {"comment_id": cid},
                            "message": {
                                "text": (
                                    "A R C  —  P R I V A T E   O N L I N E   I N C O M E   S Y S T E M\n\n"
                                    f"Step inside ARC directly here: {ARC_DIRECT_LINK}\n\n"
                                    "Or tap the main portal in @ARCBLOODLINE30 bio before spots lock."
                                )
                            }
                        }
                        requests.post(
                            f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/messages",
                            params={"access_token": page_token},
                            json=dm_payload,
                            timeout=10
                        )

                        append_to_set_file(REPLIED_COMMENTS_FILE, cid, replied_ids)
                        log(f"[INSTANT CLOSE] Auto-Replied & DM'd @{c_user} on {acc['page_name']}!")
            except Exception:
                pass

        stop_event.wait(8.0)

# ==========================================
# 4. LINK LEDGER + GRAPH API IG SCRAPER & AUDIO-BLOCK BYPASS
# ==========================================
def resolve_and_normalize_link(raw_line):
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
        return f"https://www.instagram.com/reel/{shortcode}/", f"ig_{shortcode}"

    tt_match = re.search(r'/video/(\d+)', path)
    if "tiktok.com" in host and tt_match:
        vid_id = tt_match.group(1)
        return f"https://www.tiktok.com{path}", f"tt_{vid_id}"

    yt_match = re.search(r'/(?:shorts|watch)/([A-Za-z0-9_-]{11})', path)
    if ("youtube.com" in host or "youtu.be" in host) and yt_match:
        vid_id = yt_match.group(1)
        return f"https://www.youtube.com/shorts/{vid_id}", f"yt_{vid_id}"

    clean_url = f"{parsed.scheme}://{host}{path}"
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

def scrape_target_ig_accounts_via_graph_api(scanner_acc, posted_history):
    """
    Uses Meta's official business_discovery Graph API endpoint to scrape fresh viral Reels
    from TARGET_IG_ACCOUNTS_TO_SCRAPE without getting IP-blocked on GitHub Actions.
    """
    discovered = []
    ig_user_id = scanner_acc["ig_user_id"]
    token = scanner_acc["token"]
    sample_handles = random.sample(TARGET_IG_ACCOUNTS_TO_SCRAPE, min(6, len(TARGET_IG_ACCOUNTS_TO_SCRAPE)))

    for handle in sample_handles:
        handle_clean = handle.strip().lstrip("@")
        log(f"[IG GRAPH SCRAPER] Scanning @{handle_clean} via business_discovery...")
        try:
            url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}"
            fields = f"business_discovery.username({handle_clean}){{media.limit(15){{id,permalink,media_url,media_type,like_count,comments_count}}}}"
            r = requests.get(url, params={"fields": fields, "access_token": token}, timeout=15).json()
            media_list = (((r.get("business_discovery") or {}).get("media") or {}).get("data")) or []

            media_list.sort(
                key=lambda m: int(m.get("like_count", 0) or 0) + (int(m.get("comments_count", 0) or 0) * 4),
                reverse=True
            )

            for m in media_list:
                if m.get("media_type") != "VIDEO":
                    continue
                permalink = m.get("permalink", "")
                media_url = m.get("media_url", "")
                _, canonical_id = resolve_and_normalize_link(permalink)
                if not canonical_id or canonical_id in posted_history:
                    continue
                discovered.append((canonical_id, media_url, permalink))
        except Exception:
            continue

    return discovered

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
    except Exception:
        pass
    return False

def download_instagram_mobile_or_web_reel(clean_url, out_path):
    # Route 1: Direct ddinstagram proxy
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

    # Route 2: Instagram /embed/captioned/ bypass (extracts raw CDN mp4 when copyrighted audio hides media_url)
    try:
        embed_url = f"{clean_url.rstrip('/')}/embed/captioned/"
        r = requests.get(embed_url, headers=BROWSER_HEADERS, timeout=20)
        if r.status_code == 200:
            match = re.search(r'"video_url"\s*:\s*"([^"]+)"', r.text)
            if match:
                raw_cdn_url = match.group(1).encode("utf-8").decode("unicode_escape").replace(r"\/", "/")
                vid_res = requests.get(raw_cdn_url, headers=BROWSER_HEADERS, timeout=30)
                if vid_res.status_code == 200 and len(vid_res.content) > 150000:
                    with open(out_path, "wb") as f:
                        f.write(vid_res.content)
                    if verify_video_has_real_frames(out_path):
                        return True
    except Exception:
        pass

    # Route 3: Mobile Safari yt-dlp extractor
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
    queries = random.sample(PREMADE_VIRAL_EDIT_QUERIES, min(4, len(PREMADE_VIRAL_EDIT_QUERIES)))
    for query in queries:
        log(f"[AUTO-HARVESTER] Harvesting high-retention viral edits for: '{query}'...")
        try:
            r = requests.post(
                "https://www.tikwm.com/api/feed/search",
                data={"keywords": query, "count": 35, "cursor": random.randint(0, 12)},
                headers=BROWSER_HEADERS,
                timeout=20
            )
            if r.status_code == 200 and r.text.strip().startswith("{"):
                res = r.json()
                videos = (res.get("data") or {}).get("videos") or []
                videos.sort(key=lambda x: int(x.get("play_count", 0) or 0), reverse=True)
                for v in videos:
                    vid_id = f"tt_{v.get('video_id', '')}"
                    duration = int(v.get("duration", 15))
                    play_url = v.get("play") or v.get("wmplay")
                    if play_url and 5 <= duration <= 25 and vid_id not in posted_history:
                        if play_url.startswith("/"):
                            play_url = f"https://www.tikwm.com{play_url}"
                        discovered.append((vid_id, play_url))
                if len(discovered) >= 20:
                    break
            time.sleep(1.0)
        except Exception:
            time.sleep(1.0)
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

def ingest_single_fresh_reel(scanner_acc, posted_history, cached_ig_pool, cached_viral_pool):
    os.makedirs(ASSETS_DIR, exist_ok=True)

    # LAYER 1: Manual Queue in reel_links.txt
    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, "r", encoding="utf-8") as f:
            raw_queue_lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        for raw_line in raw_queue_lines:
            clean_url, canonical_id = resolve_and_normalize_link(raw_line)
            if not clean_url or canonical_id in posted_history:
                remove_link_from_queue(raw_line, clean_url)
                continue
            safe_id = abs(hash(canonical_id)) % (10 ** 8)
            full_path = os.path.join(ASSETS_DIR, f"queue_{safe_id}.mp4")
            downloaded = False
            if "instagram.com" in clean_url.lower():
                downloaded = download_instagram_mobile_or_web_reel(clean_url, full_path)
            elif "tiktok.com" in clean_url.lower():
                downloaded = download_via_tikwm_api(clean_url, full_path)
            append_to_set_file(HISTORY_FILE, canonical_id, posted_history)
            remove_link_from_queue(raw_line, clean_url)
            if downloaded:
                return full_path

    # LAYER 2: Graph API Instagram Account Scraper (business_discovery)
    if not cached_ig_pool:
        cached_ig_pool.extend(scrape_target_ig_accounts_via_graph_api(scanner_acc, posted_history))

    while cached_ig_pool:
        canonical_id, media_url, permalink = cached_ig_pool.pop(0)
        if canonical_id in posted_history:
            continue
        full_path = os.path.join(ASSETS_DIR, f"{canonical_id}.mp4")
        downloaded = False
        if media_url:
            try:
                r = requests.get(media_url, headers=BROWSER_HEADERS, timeout=30)
                if r.status_code == 200 and len(r.content) > 150000:
                    with open(full_path, "wb") as f:
                        f.write(r.content)
                    downloaded = verify_video_has_real_frames(full_path)
            except Exception:
                pass
        if not downloaded and permalink:
            downloaded = download_instagram_mobile_or_web_reel(permalink, full_path)

        append_to_set_file(HISTORY_FILE, canonical_id, posted_history)
        if downloaded:
            log(f"[IG SCRAPER LOCKED] Pulled viral IG Reel: {canonical_id}")
            return full_path

    # LAYER 3: Proven Viral Edits Harvester
    if not cached_viral_pool:
        cached_viral_pool.extend(fetch_unblocked_premade_viral_edits(posted_history))

    while cached_viral_pool:
        vid_id, play_url = cached_viral_pool.pop(0)
        if vid_id in posted_history:
            continue
        full_path = os.path.join(ASSETS_DIR, f"viral_{vid_id}.mp4")
        try:
            r = requests.get(play_url, headers=BROWSER_HEADERS, timeout=35)
            if r.status_code == 200 and len(r.content) > 150000:
                with open(full_path, "wb") as f:
                    f.write(r.content)
                if verify_video_has_real_frames(full_path):
                    append_to_set_file(HISTORY_FILE, vid_id, posted_history)
                    return full_path
        except Exception:
            continue

    # LAYER 4: Direct Luxury Stream Fallback
    for mp4_url in harvest_live_mixkit_luxury_mp4s(posted_history):
        safe_id = abs(hash(mp4_url)) % (10 ** 8)
        full_path = os.path.join(ASSETS_DIR, f"luxury_{safe_id}.mp4")
        try:
            r = requests.get(mp4_url, headers=BROWSER_HEADERS, timeout=30)
            if r.status_code == 200 and len(r.content) > 120000:
                with open(full_path, "wb") as f:
                    f.write(r.content)
                if verify_video_has_real_frames(full_path):
                    append_to_set_file(HISTORY_FILE, mp4_url, posted_history)
                    return full_path
        except Exception:
            continue

    raise RuntimeError("All 4 harvester layers failed!")

def get_random_custom_song():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    valid_songs = [s.strip() for s in CUSTOM_SONG_LIBRARY if s and s.strip()]
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
# 6. 4K HYPER-LOOP + HIGH-CONTRAST HOOK + NEURAL VOICEOVER ENGINE
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

def generate_neural_voiceover(out_mp3_path, node_idx=0):
    """Generates a deep studio voiceover using Microsoft Edge Neural TTS (0 API keys required)."""
    script_text = ARC_VOICEOVER_SCRIPTS[node_idx % len(ARC_VOICEOVER_SCRIPTS)]
    cmd = [
        "edge-tts",
        "--voice", "en-US-ChristopherNeural",
        "--rate=+8%",
        "--pitch=-6Hz",
        "--text", script_text,
        "--write-media", out_mp3_path
    ]
    subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
    return os.path.exists(out_mp3_path) and os.path.getsize(out_mp3_path) > 4000

def mutate_video_for_account(input_path, output_path, font_path, node_idx=0):
    raw_dur = get_media_duration(input_path)
    trim_start = round(random.uniform(0.05, 0.25), 3) if raw_dur > 6.5 else 0.0
    speed = round(random.uniform(0.992, 1.008), 4)

    # 7.0s to 8.2s gives ~4.2s for the colored top hook and ~3.2s for the voiceover + ARC pitch
    target_loop_dur = round(random.uniform(7.0, 8.2), 2)
    final_duration = round(min(target_loop_dur, max(6.4, (raw_dur - trim_start - 0.08) / speed)), 2)
    pitch_start = round(final_duration * 0.58, 2)
    pitch_delay_ms = int(pitch_start * 1000)

    crop_keep = round(random.uniform(0.975, 0.992), 4)
    x_jitter = random.randint(-4, 4)
    y_jitter = random.randint(-4, 4)

    b_shift = round(random.uniform(0.004, 0.016), 4)
    c_shift = round(random.uniform(1.080, 1.125), 4)
    s_shift = round(random.uniform(1.125, 1.185), 4)
    g_shift = round(random.uniform(0.960, 0.988), 4)
    luma_sharp = round(random.uniform(0.96, 1.18), 2)

    rs = round(random.uniform(-0.018, -0.006), 4)
    gs = round(random.uniform(-0.008, 0.006), 4)
    bs = round(random.uniform(0.008, 0.022), 4)
    rh = round(random.uniform(0.005, 0.018), 4)
    gh = round(random.uniform(0.002, 0.012), 4)
    bh = round(random.uniform(-0.014, -0.004), 4)

    epoch_jitter = int(time.time()) - random.randint(600, 259200)

    msg_tuple = ARC_UNIFIED_MESSAGES[(node_idx + random.randint(0, len(ARC_UNIFIED_MESSAGES) - 1)) % len(ARC_UNIFIED_MESSAGES)]
    top_hook, center_line1, center_line2 = [t.replace("'", "").replace(":", " -") for t in msg_tuple]
    hook_color = HOOK_HIGH_CONTRAST_COLORS[node_idx % len(HOOK_HIGH_CONTRAST_COLORS)]

    top_x_offset = random.randint(-6, 6)
    top_y = random.randint(255, 315)

    center_y_shift = random.choice([-35, -15, 0, 15, 35])
    c1_y = f"(h/2)-48+{center_y_shift}"
    c2_y = f"(h/2)+22+{center_y_shift}"
    band_y = f"(h/2)-98+{center_y_shift}"

    mirror_filter = "hflip," if (node_idx % 2 == 1) else ""

    vf_chain = (
        f"setpts=PTS/{speed},"
        f"{mirror_filter}"
        f"crop=iw*{crop_keep}:ih*{crop_keep}:(iw-ow)/2+{x_jitter}:(ih-oh)/2+{y_jitter},"
        f"scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos+accurate_rnd+full_chroma_int,"
        f"crop=1080:1920,fps=30,"
        f"colorbalance=rs={rs}:gs={gs}:bs={bs}:rh={rh}:gh={gh}:bh={bh},"
        f"eq=brightness={b_shift}:contrast={c_shift}:saturation={s_shift}:gamma={g_shift},"
        f"unsharp=lx=5:ly=5:la={luma_sharp}:cx=3:cy=3:ca=0.25,"
        f"noise=alls=1:allf=t,"
        f"fade=t=in:st=0:d=0.12:color=white,"
        # STAGE 1 (First 58%): High-Contrast Colored Hook on Top
        f"drawtext=fontfile={font_path}:text='{top_hook}':expansion=none:"
        f"fontcolor={hook_color}:fontsize=27:shadowcolor=black@0.95:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.86:boxborderw=16:"
        f"x=(w-text_w)/2+{top_x_offset}:y={top_y}:enable='lt(t,{pitch_start})',"
        # STAGE 2 (Final 42%): Short Trust & Scarcity Pitch in Center
        f"drawbox=x=0:y={band_y}:w=iw:h=185:color=black@0.65:t=fill:enable='gte(t,{pitch_start})',"
        f"drawtext=fontfile={font_path}:text='{center_line1}':expansion=none:"
        f"fontcolor=white:fontsize=22:shadowcolor=black@0.95:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.92:boxborderw=14:"
        f"x=(w-text_w)/2:y={c1_y}:enable='gte(t,{pitch_start})',"
        f"drawtext=fontfile={font_path}:text='{center_line2}':expansion=none:"
        f"fontcolor=0xFFD700:fontsize=24:shadowcolor=black@0.95:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.92:boxborderw=14:"
        f"x=(w-text_w)/2:y={c2_y}:enable='gte(t,{pitch_start})'"
    )

    vo_path = f"vo_temp_{node_idx}.mp3"
    has_vo = False
    try:
        has_vo = generate_neural_voiceover(vo_path, node_idx)
    except Exception:
        has_vo = False

    crf_val = str(random.choice([18, 19]))
    fade_out_st = round(max(1.0, final_duration - 0.35), 2)
    has_orig_audio = video_has_audio_stream(input_path)

    pitch_shift = round(random.uniform(0.992, 1.008), 4)
    eq_freq = random.randint(1200, 3800)
    eq_gain = random.choice([-1.4, -0.9, 0.9, 1.4])

    try:
        if has_orig_audio and not USE_CUSTOM_SONG_OVER_EDIT and has_vo:
            # Ducks original background audio to 25% volume when neural voiceover enters at pitch_start
            filter_complex = (
                f"[0:v]{vf_chain}[vout];"
                f"[0:a]asetrate=48000*{pitch_shift},aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"equalizer=f={eq_freq}:width_type=h:width=250:g={eq_gain},"
                f"volume=1.05:enable='lt(t,{pitch_start})',volume=0.25:enable='gte(t,{pitch_start})'[bg];"
                f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"adelay={pitch_delay_ms}|{pitch_delay_ms},bass=g=3:f=110,volume=1.90[vo];"
                f"[bg][vo]amix=inputs=2:duration=first:dropout_transition=0,"
                f"afade=t=in:st=0:d=0.12,afade=t=out:st={fade_out_st}:d=0.35[aout]"
            )
            cmd = [
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-stream_loop", "-1", "-ss", str(trim_start), "-t", str(final_duration), "-i", input_path,
                "-i", vo_path,
                "-filter_complex", filter_complex,
                "-map", "[vout]", "-map", "[aout]",
                "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.1",
                "-crf", crf_val, "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-shortest", "-map_metadata", "-1", "-metadata", f"creation_time={epoch_jitter}",
                output_path
            ]
        elif has_orig_audio and not USE_CUSTOM_SONG_OVER_EDIT:
            af_chain = (
                f"asetrate=48000*{pitch_shift},aresample=48000,"
                f"equalizer=f={eq_freq}:width_type=h:width=250:g={eq_gain},"
                f"bass=g=2.8:f=95:w=0.5,volume=1.05,"
                f"afade=t=in:st=0:d=0.12,afade=t=out:st={fade_out_st}:d=0.35"
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
                if has_vo:
                    filter_complex = (
                        f"[0:v]{vf_chain}[vout];"
                        f"[1:a]asetrate=48000*{pitch_shift},aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                        f"volume=0.95:enable='lt(t,{pitch_start})',volume=0.25:enable='gte(t,{pitch_start})'[bg];"
                        f"[2:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                        f"adelay={pitch_delay_ms}|{pitch_delay_ms},bass=g=3:f=110,volume=1.90[vo];"
                        f"[bg][vo]amix=inputs=2:duration=first:dropout_transition=0,"
                        f"afade=t=in:st=0:d=0.15,afade=t=out:st={fade_out_st}:d=0.35[aout]"
                    )
                    cmd = [
                        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                        "-stream_loop", "-1", "-ss", str(trim_start), "-t", str(final_duration), "-i", input_path,
                        "-stream_loop", "-1", "-ss", str(song_start), "-t", str(final_duration), "-i", custom_song,
                        "-i", vo_path,
                        "-filter_complex", filter_complex,
                        "-map", "[vout]", "-map", "[aout]",
                        "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.1",
                        "-crf", crf_val, "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                        "-shortest", "-map_metadata", "-1", "-metadata", f"creation_time={epoch_jitter}",
                        output_path
                    ]
                else:
                    af_chain = (
                        f"asetrate=48000*{pitch_shift},aresample=48000,"
                        f"equalizer=f={eq_freq}:width_type=h:width=250:g={eq_gain},"
                        f"volume=0.95,afade=t=in:st=0:d=0.15,afade=t=out:st={fade_out_st}:d=0.35"
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
    finally:
        if os.path.exists(vo_path):
            try:
                os.remove(vo_path)
            except Exception:
                pass

    return output_path

# ==========================================
# 7. RELAY UPLOAD & GRAPH API PUBLISH (WITH THUMB_OFFSET FIX)
# ==========================================
def upload_for_meta_download(file_path):
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", "Accept-Language": "en-US,en;q=0.9"}
    try:
        with open(file_path, "rb") as f:
            res = requests.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload"}, files={"fileToUpload": f}, headers=headers, timeout=(15, 75))
        if res.status_code == 200 and res.text.strip().startswith("https://"):
            return res.text.strip()
    except Exception:
        pass
    try:
        with open(file_path, "rb") as f:
            res = requests.post("https://uguu.se/upload", files={"files[]": f}, headers=headers, timeout=(15, 75)).json()
        if res.get("success") and res.get("files"):
            return res["files"][0]["url"]
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
        "thumb_offset": str(random.randint(1200, 2800)),  # Picks sharp frame 1.2s-2.8s in (fixes frame-0 blank cover)
        "access_token": token
    }
    res = requests.post(container_url, data=payload, timeout=(10, 30)).json()
    if "id" not in res:
        raise Exception(f"Container failed: {res}")

    creation_id = res["id"]
    status_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{creation_id}"
    time.sleep(30)
    for _ in range(15):
        status_res = requests.get(status_url, params={"fields": "status_code,status", "access_token": token}, timeout=(10, 20)).json()
        status_code = status_res.get("status_code")
        if status_code == "FINISHED":
            break
        elif status_code in ("ERROR", "EXPIRED"):
            raise Exception(f"Meta rejected video: {status_res}")
        time.sleep(12)
    else:
        raise Exception("Meta video processing timed out.")

    publish_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}/media_publish"
    publish_res = requests.post(publish_url, data={"creation_id": creation_id, "access_token": token}, timeout=(10, 30)).json()
    if "id" not in publish_res:
        raise Exception(f"Publish failed: {publish_res}")

    log(f"[SUCCESS] PUBLISHED LIVE! Media ID: {publish_res['id']}")

# ==========================================
# 8. MAIN EXECUTION (30-MIN IG SCRAPER + VO + 8-SEC INSTANT CLOSER)
# ==========================================
def main():
    log("=== ARC 30-MINUTE IG SCRAPER, NEURAL VO & 8-SECOND CLOSER STARTED ===")
    ensure_edge_tts_installed()

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

    # Start 8-second real-time Comment & DM Closer daemon thread
    stop_event = threading.Event()
    closer_thread = threading.Thread(target=run_realtime_comment_closer, args=(all_accounts, stop_event), daemon=True)
    closer_thread.start()

    wave_accounts = select_round_robin_accounts(all_accounts, ACCOUNTS_PER_WAVE)
    caption_batch = generate_unique_caption_batch(len(wave_accounts))

    cached_ig_pool = []
    cached_viral_pool = []
    current_video = None
    success_count = 0

    try:
        for index, acc in enumerate(wave_accounts):
            if index % MAX_ACCOUNTS_PER_VIDEO == 0 or not current_video:
                if current_video and os.path.exists(current_video):
                    try:
                        os.remove(current_video)
                    except Exception:
                        pass
                current_video = ingest_single_fresh_reel(acc, posted_history, cached_ig_pool, cached_viral_pool)

            log(f"\n--- NODE [{index+1}/{len(wave_accounts)}]: {acc['page_name']} ({acc['ig_user_id']}) ---")
            mutated_output = f"arc_4k_stealth_{index}.mp4"

            try:
                mutate_video_for_account(current_video, mutated_output, font_path, node_idx=index)
                public_url = upload_for_meta_download(mutated_output)
                publish_reel_to_instagram(acc["ig_user_id"], public_url, caption_batch[index], acc["token"])
                success_count += 1
            except Exception as e:
                log(f"[ERROR] Failed on {acc['page_name']}: {e}")
            finally:
                if os.path.exists(mutated_output):
                    try:
                        os.remove(mutated_output)
                    except Exception:
                        pass

            if index < len(wave_accounts) - 1:
                cooldown_sec = random.randint(MIN_COOLDOWN_SECONDS, MAX_COOLDOWN_SECONDS)
                log(f"[TIMER] Waiting {cooldown_sec}s before next upload (8s Auto-DM Closer active in background)...")
                time.sleep(cooldown_sec)
    finally:
        stop_event.set()
        if current_video and os.path.exists(current_video):
            try:
                os.remove(current_video)
            except Exception:
                pass

    log(f"\n=== 30-MIN WAVE COMPLETE: {success_count}/{len(wave_accounts)} DISTINCT 4K REELS PUBLISHED ===")
    if success_count == 0:
        raise RuntimeError("0 Reels were published in this wave!")

if __name__ == "__main__":
    main()
