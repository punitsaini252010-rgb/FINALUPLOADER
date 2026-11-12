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
        subprocess.run(
            ["edge-tts", "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=True
        )
    except Exception:
        log("[INIT] Installing edge-tts for realistic neural voiceover...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", "edge-tts"],
                stdin=subprocess.DEVNULL,
                timeout=60
            )
        except Exception as e:
            log(f"[OVERFLOW] edge-tts install skipped, continuing safely: {e}")

# ==========================================
# 1. CORE CONFIGURATION & TARGET ACCOUNTS
# ==========================================
META_TOKENS = [
    os.getenv("META_TOKEN_1"),
    os.getenv("META_TOKEN_2")
]

ARC_DIRECT_LINK = os.getenv("ARC_JOIN_LINK", "https://www.instagram.com/arcbloodline30/")

GRAPH_API_VERSION = "v20.0"

ACCOUNTS_PER_WAVE = 12

MIN_COOLDOWN_SECONDS = 10
MAX_COOLDOWN_SECONDS = 28

LINKS_FILE = "reel_links.txt"
# Stores per-account history as "{ig_user_id}:{reel_id}" so an account never repeats a Reel,
# while other accounts that haven't posted it yet can still randomly pick and post it.
HISTORY_FILE = "arc_ig_history.txt"
REPLIED_COMMENTS_FILE = "replied_comments.txt"
CURSOR_FILE = "account_cursor.txt"
ASSETS_DIR = "assets"
CUSTOM_FONT_PATH = "Montserrat-ExtraBold.ttf"

TARGET_IG_ACCOUNTS_TO_SCRAPE = [
    "https://www.instagram.com/worthy?utm_source=ig_web_button_share_sheet&rpxt=ZDNlZDc0MzIxNw==",
    "https://www.instagram.com/aureonlux?utm_source=ig_web_button_share_sheet&dlrf=ZDNlZDc0MzIxNw==",
    "Luxurvault",
    "Luxurcore",
    "toptierpath",
    "toptierclasy",
    "toptierclassy",
    "leornabs"
]

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

DISCORD_BOT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

# ==========================================
# 2. HIGH-CONTRAST HOOKS & TRUST PITCH
# ==========================================
ARC_FINAL_LINE_1 = "A R C  -  P R I V A T E   O N L I N E   I N C O M E   S Y S T E M"
ARC_FINAL_LINE_2 = "F I N A L   S P O T S   C L O S I N G   ->   @ A R C B L O O D L I N E 3 0"

ARC_VOICEOVER_SCRIPTS = [
    "ARC is the private system where men build real online income. Final spots are closing. Check the bio.",
    "Stop trading your life for a paycheck. Step inside the ARC income system through the bio link right now.",
    "You do not need luck, you need a proven system. Join the private ARC network in the bio before doors lock.",
    "Most men just watch. Builders execute. Enter the ARC online wealth system via the bio link today.",
    "Escape the race and build real digital leverage. Tap the bio link and enter ARC before spots close."
]

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
    return [f"{random.choice(pool)}{random.choice(micro_tags)}".strip() for _ in range(count)]

# ==========================================
# 3. REAL-TIME 8-SECOND AUTO-COMMENT & DM CLOSER
# ==========================================
def run_realtime_comment_closer(all_accounts, stop_event):
    replied_ids = load_set_file(REPLIED_COMMENTS_FILE)
    log("[REAL-TIME CLOSER] 8-second Instant Comment-to-DM Daemon ACTIVE across all accounts.")

    while not stop_event.is_set():
        for acc in all_accounts:
            if stop_event.is_set():
                break
            ig_id = acc.get("ig_user_id")
            page_token = acc.get("page_token") or acc.get("token")
            user_token = acc.get("token")
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

                        reply_text = f"@{c.get('username', '')} Sent you the private access link. You can also enter ARC directly via @ARCBLOODLINE30 bio ⚡"
                        try:
                            requests.post(
                                f"https://graph.facebook.com/{GRAPH_API_VERSION}/{cid}/replies",
                                data={"message": reply_text, "access_token": user_token},
                                timeout=10
                            )
                        except Exception:
                            pass

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
                        try:
                            requests.post(
                                f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/messages",
                                params={"access_token": page_token},
                                json=dm_payload,
                                timeout=10
                            )
                        except Exception:
                            pass

                        append_to_set_file(REPLIED_COMMENTS_FILE, cid, replied_ids)
                        log(f"[INSTANT CLOSE] Auto-Replied & DM'd @{c_user} on {acc.get('page_name', 'Node')}!")
            except Exception:
                pass

        stop_event.wait(8.0)

# ==========================================
# 4. LIGHTWEIGHT ONCE-PER-WAVE SCRAPER & PER-ACCOUNT RANDOM PICKER
# ==========================================
def unescape_ig_payload(raw_text):
    """Unescapes Instagram HTML/JSON backslashes so regexes never truncate video URLs."""
    if not raw_text:
        return ""
    return (
        raw_text.replace(r"\\/", "/")
        .replace(r"\/", "/")
        .replace(r"\\u0026", "&")
        .replace(r"\u0026", "&")
        .replace(r'\\"', '"')
        .replace(r'\"', '"')
        .replace("&quot;", '"')
        .replace("&amp;", "&")
    )

def extract_ig_handle(raw_entry):
    if not raw_entry:
        return ""
    s = str(raw_entry).strip()
    if "instagram.com" in s.lower():
        try:
            parsed = urllib.parse.urlparse(s if s.startswith("http") else f"https://{s}")
            parts = [p for p in parsed.path.split("/") if p and p.lower() not in ("reel", "reels", "p", "stories", "tv")]
            if parts:
                return parts[0].strip().lstrip("@").lower()
        except Exception:
            pass
    return s.lstrip("@").split("?")[0].strip("/").strip().lower()

def resolve_and_normalize_link(raw_line):
    if not raw_line:
        return None, None
    match = re.search(r'(https?://[^\s"\'<>]+)', str(raw_line).strip())
    if not match:
        return None, None
    url = match.group(1).strip()

    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower().replace("m.instagram.com", "www.instagram.com")
    path = parsed.path.rstrip("/")

    ig_match = re.search(r'/(?:reel|reels|p)/([A-Za-z0-9_-]+)', path)
    if "instagram.com" in host and ig_match:
        shortcode = ig_match.group(1)
        return f"https://www.instagram.com/reel/{shortcode}/", f"ig_{shortcode}"

    clean_url = f"{parsed.scheme}://{host}{path}"
    return clean_url, clean_url

def load_set_file(filepath):
    if not os.path.exists(filepath):
        return set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except Exception:
        return set()

def append_to_set_file(filepath, identifier, memory_set):
    if not identifier:
        return
    clean = str(identifier).strip()
    if clean not in memory_set:
        memory_set.add(clean)
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(f"{clean}\n")
        except Exception:
            pass

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
    try:
        with open(CURSOR_FILE, "w", encoding="utf-8") as f:
            f.write(str(next_cursor))
    except Exception:
        pass

    random.shuffle(selected)
    log(f"[ROUND-ROBIN] Cursor {start_idx} -> {next_cursor} (Selected & randomized {len(selected)}/{total} accounts).")
    return selected

def verify_video_has_real_frames(video_path):
    if not os.path.exists(video_path) or os.path.getsize(video_path) < 70000:
        return False
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", video_path
        ]
        res = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        dims = res.stdout.decode("utf-8").strip().split("x")
        return int(dims[0]) >= 320 and int(dims[1]) >= 320
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

def build_master_reel_catalog_once():
    """
    Runs ONCE at the start of the wave.
    Uses Instagram's public /embed/ profile endpoint (works from GitHub Actions IPs without login)
    plus manual reel_links.txt to build a master pool of Reels from your target accounts.
    """
    catalog = []
    seen_shortcodes = set()

    # 1. Include any manual links from reel_links.txt
    if os.path.exists(LINKS_FILE):
        try:
            with open(LINKS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    clean_u, cid = resolve_and_normalize_link(line.strip())
                    if clean_u and cid and cid not in seen_shortcodes:
                        seen_shortcodes.add(cid)
                        catalog.append((cid, "", clean_u, "reel_links.txt"))
        except Exception:
            pass

    clean_handles = []
    for raw in TARGET_IG_ACCOUNTS_TO_SCRAPE:
        h = extract_ig_handle(raw)
        if h and h not in clean_handles:
            clean_handles.append(h)

    random.shuffle(clean_handles)

    for handle in clean_handles:
        handle_count = 0

        # Route A: Public Profile /embed/ page (Never blocked on GitHub Actions IPs)
        for embed_url in [
            f"https://www.instagram.com/{handle}/embed/",
            f"https://www.instagram.com/{handle}/embed/captioned/"
        ]:
            try:
                r = requests.get(embed_url, headers=BROWSER_HEADERS, timeout=15)
                if r.status_code == 200 and len(r.text) > 500:
                    clean_html = unescape_ig_payload(r.text)

                    # Extract pairs of shortcode + direct video_url if embedded in contextJSON
                    for match in re.finditer(
                        r'"shortcode"\s*:\s*"([A-Za-z0-9_-]{8,15})"[^{}]*?"video_url"\s*:\s*"(https?://[^"]+)"',
                        clean_html
                    ):
                        sc, v_url = match.group(1), match.group(2)
                        cid = f"ig_{sc}"
                        if cid not in seen_shortcodes:
                            seen_shortcodes.add(cid)
                            catalog.append((cid, v_url, f"https://www.instagram.com/reel/{sc}/", handle))
                            handle_count += 1

                    # Extract all post/reel shortcodes on the profile embed grid
                    shortcodes = re.findall(r'"shortcode"\s*:\s*"([A-Za-z0-9_-]{8,15})"', clean_html)
                    shortcodes += re.findall(r'/(?:reel|reels|p)/([A-Za-z0-9_-]{8,15})/', clean_html)

                    for sc in shortcodes:
                        if sc in ("embed", "captioned", handle):
                            continue
                        cid = f"ig_{sc}"
                        if cid not in seen_shortcodes:
                            seen_shortcodes.add(cid)
                            catalog.append((cid, "", f"https://www.instagram.com/reel/{sc}/", handle))
                            handle_count += 1

                if handle_count > 0:
                    break
            except Exception:
                continue

        # Route B: Secondary Web Profile API check if /embed/ returned 0
        if handle_count == 0:
            try:
                web_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={handle}"
                headers = dict(BROWSER_HEADERS)
                headers["X-IG-App-ID"] = "936619743392459"
                headers["Referer"] = f"https://www.instagram.com/{handle}/"
                r = requests.get(web_url, headers=headers, timeout=12)
                if r.status_code == 200:
                    clean_json = unescape_ig_payload(r.text)
                    for sc in re.findall(r'"shortcode"\s*:\s*"([A-Za-z0-9_-]{8,15})"', clean_json):
                        cid = f"ig_{sc}"
                        if cid not in seen_shortcodes:
                            seen_shortcodes.add(cid)
                            catalog.append((cid, "", f"https://www.instagram.com/reel/{sc}/", handle))
                            handle_count += 1
            except Exception:
                pass

        log(f"[CATALOG] Pulled {handle_count} items from @{handle}")

    random.shuffle(catalog)
    log(f"[CATALOG READY] Total unique items across target accounts: {len(catalog)}")
    return catalog

def download_instagram_reel_all_routes(clean_url, out_path):
    ig_match = re.search(r'/(?:reel|reels|p)/([A-Za-z0-9_-]+)', clean_url)
    shortcode = ig_match.group(1) if ig_match else ""
    if not shortcode:
        return False

    # Route 1: Unescaped Instagram /embed/captioned/ & /embed/ parser (Fixes the https: truncation bug)
    for path_prefix in ["reel", "p"]:
        for suffix in ["embed/captioned/", "embed/"]:
            try:
                embed_url = f"https://www.instagram.com/{path_prefix}/{shortcode}/{suffix}"
                r = requests.get(embed_url, headers=BROWSER_HEADERS, timeout=15)
                if r.status_code == 200 and len(r.text) > 500:
                    clean_html = unescape_ig_payload(r.text)
                    video_urls = re.findall(r'"video_url"\s*:\s*"(https?://[^"]+)"', clean_html)
                    video_urls += re.findall(r'"contentUrl"\s*:\s*"(https?://[^"]+)"', clean_html)
                    video_urls += re.findall(r'<meta[^>]+property="og:video"[^>]+content="(https?://[^"]+)"', clean_html)
for raw_cdn in video_urls:
                        if ".mp4" in raw_cdn or "cdninstagram.com" in raw_cdn or "fbcdn.net" in raw_cdn:
                            vid_res = requests.get(raw_cdn, headers=BROWSER_HEADERS, timeout=25)
                            if vid_res.status_code == 200 and len(vid_res.content) > 70000:
                                with open(out_path, "wb") as f:
                                    f.write(vid_res.content)
                                if verify_video_has_real_frames(out_path):
                                    return True
            except Exception:
                pass

    # Route 2: Discordbot Embed Fixers (vxinstagram / ddinstagram / kkinstagram)
    for host in ["www.vxinstagram.com", "d.ddinstagram.com", "www.ddinstagram.com", "www.kkinstagram.com"]:
        try:
            proxy_url = f"https://{host}/reel/{shortcode}"
            r = requests.get(proxy_url, headers=DISCORD_BOT_HEADERS, allow_redirects=True, timeout=18)
            if r.status_code == 200:
                if len(r.content) > 70000 and "video" in r.headers.get("Content-Type", "").lower():
                    with open(out_path, "wb") as f:
                        f.write(r.content)
                    if verify_video_has_real_frames(out_path):
                        return True
                else:
                    clean_html = unescape_ig_payload(r.text)
                    og_matches = re.findall(
                        r'<meta[^>]+property="og:video(?::secure_url)?"[^>]+content="(https?://[^"]+)"',
                        clean_html
                    )
                    for og_url in og_matches:
                        vid_res = requests.get(og_url, headers=BROWSER_HEADERS, allow_redirects=True, timeout=25)
                        if vid_res.status_code == 200 and len(vid_res.content) > 70000:
                            with open(out_path, "wb") as f:
                                f.write(vid_res.content)
                            if verify_video_has_real_frames(out_path):
                                return True
        except Exception:
            pass

    # Route 3: vxinstagram JSON API
    try:
        vx_api = f"https://api.vxinstagram.com/reel/{shortcode}"
        r = requests.get(vx_api, headers=DISCORD_BOT_HEADERS, timeout=15)
        if r.status_code == 200 and r.text.strip().startswith("{"):
            data = r.json()
            for m in data.get("media_extended") or []:
                v_url = m.get("url")
                if v_url and v_url.startswith("http"):
                    vid_res = requests.get(v_url, headers=BROWSER_HEADERS, timeout=25)
                    if vid_res.status_code == 200 and len(vid_res.content) > 70000:
                        with open(out_path, "wb") as f:
                            f.write(vid_res.content)
                        if verify_video_has_real_frames(out_path):
                            return True
    except Exception:
        pass

    # Route 4: Instagram GraphQL doc_id query (with full unescaping)
    for doc_id in ["8845758582119845", "10015901848480474"]:
        try:
            gql_headers = {
                "User-Agent": BROWSER_HEADERS["User-Agent"],
                "X-IG-App-ID": "936619743392459",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://www.instagram.com",
                "Referer": clean_url
            }
            gql_data = {"variables": json.dumps({"shortcode": shortcode}), "doc_id": doc_id}
            r = requests.post("https://www.instagram.com/graphql/query", headers=gql_headers, data=gql_data, timeout=15)
            if r.status_code == 200 and "video_url" in r.text:
                clean_json = unescape_ig_payload(r.text)
                for raw_cdn in re.findall(r'"video_url"\s*:\s*"(https?://[^"]+)"', clean_json):
                    vid_res = requests.get(raw_cdn, headers=BROWSER_HEADERS, timeout=25)
                    if vid_res.status_code == 200 and len(vid_res.content) > 70000:
                        with open(out_path, "wb") as f:
                            f.write(vid_res.content)
                        if verify_video_has_real_frames(out_path):
                            return True
        except Exception:
            pass

    # Route 5: yt-dlp Mobile Extractor
    ydl_opts = {
        "format": "bestvideo[height<=1920][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": out_path,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 18,
        "http_headers": BROWSER_HEADERS
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(clean_url, download=True)
        if verify_video_has_real_frames(out_path):
            return True
    except Exception:
        pass

    return False

def pick_random_reel_for_account(ig_user_id, master_catalog, posted_history, downloaded_cache, non_video_shortcodes, used_in_wave):
    """
    Randomly chooses a Reel for `ig_user_id` that `ig_user_id` has NEVER posted before.
    Other accounts that haven't posted that Reel CAN still pick and post it.
    Caches downloaded source files in `downloaded_cache` so the script never scrapes too hard.
    """
    os.makedirs(ASSETS_DIR, exist_ok=True)

    # Filter catalog to items this specific account has NOT posted yet (and skip known photo posts)
    eligible = [
        item for item in master_catalog
        if item[0] not in non_video_shortcodes and f"{ig_user_id}:{item[0]}" not in posted_history
    ]

    # If this account has somehow posted every single Reel in the catalog, allow full catalog pool
    if not eligible:
        eligible = [item for item in master_catalog if item[0] not in non_video_shortcodes]

    # Prefer Reels not yet used in this wave first, then any eligible Reel for this account
    fresh_for_wave = [item for item in eligible if item[0] not in used_in_wave]
    already_in_wave = [item for item in eligible if item[0] in used_in_wave]
    random.shuffle(fresh_for_wave)
    random.shuffle(already_in_wave)
    candidates = fresh_for_wave + already_in_wave

    for canonical_id, media_url, permalink, source_handle in candidates:
        # If already downloaded during this run, reuse the clean local master file
        if canonical_id in downloaded_cache and os.path.exists(downloaded_cache[canonical_id]):
            used_in_wave.add(canonical_id)
            log(f"[RANDOM PICK] Selected {canonical_id} (from @{source_handle}) for account {ig_user_id}")
            return canonical_id, downloaded_cache[canonical_id]

        full_path = os.path.join(ASSETS_DIR, f"master_{canonical_id}.mp4")
        downloaded = False

        if media_url:
            try:
                r = requests.get(media_url, headers=BROWSER_HEADERS, timeout=25)
                if r.status_code == 200 and len(r.content) > 70000:
                    with open(full_path, "wb") as f:
                        f.write(r.content)
                    downloaded = verify_video_has_real_frames(full_path)
            except Exception:
                downloaded = False

        if not downloaded and permalink:
            downloaded = download_instagram_reel_all_routes(permalink, full_path)

        if downloaded:
            downloaded_cache[canonical_id] = full_path
            used_in_wave.add(canonical_id)
            log(f"[RANDOM PICK] Downloaded & locked {canonical_id} (from @{source_handle}) for account {ig_user_id}")
            return canonical_id, full_path
        else:
            # Mark shortcode as non-video/unavailable for this run so no other node wastes time on it
            non_video_shortcodes.add(canonical_id)

    return None, None

# ==========================================
# 5. GRAPH API ACCOUNT DISCOVERY
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
# 6. 4K MUTATION & NEURAL VOICEOVER ENGINE
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

def generate_neural_voiceover(out_mp3_path):
    script_text = random.choice(ARC_VOICEOVER_SCRIPTS)
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

    msg_tuple = random.choice(ARC_UNIFIED_MESSAGES)
    top_hook, center_line1, center_line2 = [t.replace("'", "").replace(":", " -") for t in msg_tuple]
    hook_color = random.choice(HOOK_HIGH_CONTRAST_COLORS)

    top_x_offset = random.randint(-6, 6)
    top_y = random.randint(255, 315)

    center_y_shift = random.choice([-35, -15, 0, 15, 35])
    c1_y = f"(h/2)-48+{center_y_shift}"
    c2_y = f"(h/2)+22+{center_y_shift}"
    band_y = f"(h/2)-98+{center_y_shift}"

    mirror_filter = "hflip," if random.choice([True, False]) else ""

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
        f"drawtext=fontfile={font_path}:text='{top_hook}':expansion=none:"
        f"fontcolor={hook_color}:fontsize=27:shadowcolor=black@0.95:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.86:boxborderw=16:"
        f"x=(w-text_w)/2+{top_x_offset}:y={top_y}:enable='lt(t,{pitch_start})',"
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

    vo_path = f"vo_temp_{node_idx}_{random.randint(100,999)}.mp3"
    has_vo = False
    try:
        has_vo = generate_neural_voiceover(vo_path)
    except Exception:
        has_vo = False

    crf_val = str(random.choice([18, 19]))
    fade_out_st = round(max(1.0, final_duration - 0.35), 2)
    has_orig_audio = video_has_audio_stream(input_path)
    pitch_shift = round(random.uniform(0.992, 1.008), 4)
    eq_freq = random.randint(1200, 3800)
    eq_gain = random.choice([-1.4, -0.9, 0.9, 1.4])

    try:
        if has_orig_audio and has_vo:
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
            res = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
            if res.returncode == 0 and verify_video_has_real_frames(output_path):
                return output_path

        fallback_cmd = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-stream_loop", "-1", "-ss", str(trim_start), "-t", str(final_duration), "-i", input_path,
            "-vf", vf_chain,
            "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.1",
            "-crf", crf_val, "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-shortest", "-map_metadata", "-1", "-metadata", f"creation_time={epoch_jitter}",
            output_path
        ]
        res2 = subprocess.run(fallback_cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        if res2.returncode != 0:
            raise Exception(res2.stderr.decode("utf-8", errors="ignore"))
    finally:
        if os.path.exists(vo_path):
            try:
                os.remove(vo_path)
            except Exception:
                pass

    return output_path

# ==========================================
# 7. RELAY UPLOAD & GRAPH API PUBLISH
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
            res = requests.post("https://litterbox.catbox.moe/resources/internals/api.php", data={"reqtype": "fileupload", "time": "1h"}, files={"fileToUpload": f}, headers=headers, timeout=(15, 75))
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
            response = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, headers=headers, timeout=(15, 75)).json()
        if "data" in response and "url" in response["data"]:
            return response["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")
    except Exception:
        pass
    with open(file_path, "rb") as f:
        res = requests.post("https://0x0.st", files={"file": f}, headers=headers, timeout=(15, 75))
    if res.status_code == 200 and res.text.strip().startswith("https://"):
        return res.text.strip()
    raise Exception("All 5 relay upload hosts timed out.")

def publish_reel_to_instagram(ig_user_id, video_url, caption, token):
    container_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "thumb_offset": str(random.randint(1200, 2800)),
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
          
