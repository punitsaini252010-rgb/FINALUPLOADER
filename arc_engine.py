import os
import re
import sys
import json
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

class SilentYTDLLogger:
    def debug(self, msg):
        pass
    def warning(self, msg):
        pass
    def error(self, msg):
        pass

def ensure_edge_tts_installed():
    try:
        subprocess.run(["edge-tts", "--version"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=True)
    except Exception:
        log("[INIT] Installing edge-tts for realistic neural voiceover...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "edge-tts"], stdin=subprocess.DEVNULL, timeout=60)
        except Exception as e:
            log(f"[OVERFLOW] edge-tts install skipped: {e}")

# ==========================================
# 1. CORE CONFIGURATION & TARGET ACCOUNTS
# ==========================================
META_TOKENS = [
    os.getenv("META_TOKEN_1"),
    os.getenv("META_TOKEN_2")
]

GRAPH_API_VERSION = "v20.0"
ACCOUNTS_PER_WAVE = 23
MIN_COOLDOWN_SECONDS = 3
MAX_COOLDOWN_SECONDS = 7

LINKS_FILE = "reel_links.txt"
HISTORY_FILE = "arc_ig_history.txt"
DEAD_SHORTCODES_FILE = "arc_dead_shortcodes.txt"
CURSOR_FILE = "account_cursor.txt"
ASSETS_DIR = "assets"
STYLISH_FONT_PATH = "Cinzel-Bold.ttf"

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

BOT_EMBED_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)",
    "Accept": "*/*"
}

# ==========================================
# 2. GOLD STYLISH HOOKS, GOLD FINAL LINES & REALISTIC VOICEOVER
# ==========================================
GOLD_HEX = "0xFFD700"

ARC_FINAL_LINE_1 = "A R C  -  P R I V A T E   O N L I N E   W E A L T H   S Y S T E M"
ARC_FINAL_LINE_2 = "J O I N   A R C   N O W   -   @ A R C B L O O D L I N E 3 0   B I O"

ARC_VOICEOVER_SCRIPTS = [
    "ARC is the private online wealth system. Join now through the link in the bio.",
    "Stop trading your time for a paycheck. Enter the ARC wealth system in the bio right now.",
    "You do not need luck, you need a proven system. Join the private ARC network in the bio.",
    "Most men just watch while builders execute. Step inside ARC through the bio link today.",
    "Escape the rat race and build real digital income. Tap the bio link and join ARC now."
]

HOOK_HIGH_CONTRAST_COLORS = [
    "0xFFE600",
    "0x00F5D4",
    "0xFF3B30",
    "0x00FF66"
]

ARC_TOP_HOOKS = [
    "Y O U   A R E   T O O   S M A R T   T O   S T A Y   B R O K E",
    "Y O U R   S A L A R Y   I S   B U Y I N G   Y O U R   S I L E N C E",
    "9 9 %   O F   M E N   D I E   W I T H   R E G R E T",
    "N O B O D Y   I S   C O M I N G   T O   S A V E   Y O U",
    "H A R D   W O R K   W I T H O U T   A   S Y S T E M   F A I L S",
    "W H Y   W A T C H   O T H E R   M E N   L I V E   Y O U R   L I F E",
    "T H E   M O N T H L Y   P A Y C H E C K   I S   A   T R A P",
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
        "ARC is a private online wealth and digital business system built for men ready to create independent online income from scratch.\n"
        "• Proven step-by-step digital income blueprints\n"
        "• Direct private network of high-level builders & operators\n\n"
        "-> Join ARC now via the link in @ARCBLOODLINE30 bio.\n\n"
        "Niche & Category: Luxury Lifestyle • Wealth Creation • Digital Entrepreneurship • Financial Freedom\n"
        "#luxurylifestyle #wealthmindset #entrepreneurship #digitalbusiness #financialfreedom #oldmoney #successmindset #onlineincome"
    ),
    (
        "Stop watching other men live the life you were meant to build.\n\n"
        "Inside ARC, you unlock the exact digital business models, scalable systems, and private execution network to build real online cashflow.\n"
        "No fluff. Pure execution.\n\n"
        "-> Tap @ARCBLOODLINE30 and click the bio link to enter ARC right now.\n\n"
        "Niche & Category: Billionaire Mindset • Online Business • High-Status Living • Wealth Systems\n"
        "#billionairemindset #luxurycars #wealthbuilding #onlinebusiness #menwithclass #financialindependence #entrepreneur #success"
    ),
    (
        "Why 99% of men stay trapped in the paycheck cycle:\n\n"
        "They work hard inside someone else's system instead of owning digital leverage.\n"
        "ARC gives you the complete online wealth blueprint and private community to take control of your income.\n\n"
        "-> Enter ARC right now via @ARCBLOODLINE30 bio.\n\n"
        "Niche & Category: Men's Self-Improvement • Wealth Architecture • Luxury Aesthetic • Business Systems\n"
        "#mindset #wealth #luxury #businessowner #millionairemindset #selfimprovement #oldmoneyaesthetic #moneymindset"
    ),
    (
        "Read this before you scroll past:\n\n"
        "If you repeat the last 6 months for the next 5 years, nothing changes.\n"
        "ARC was built for ambitious men ready to lock in and build automated digital income alongside serious operators.\n\n"
        "-> Claim your spot in @ARCBLOODLINE30 bio before doors close.\n\n"
        "Niche & Category: Private Wealth Network • Digital Assets • Luxury Motivation • Financial Sovereignty\n"
        "#luxurylife #wealthcreation #businessmindset #entrepreneurlife #successdriven #financialfreedom #richmindset #luxury"
    )
]

def generate_unique_caption_batch(count):
    pool = list(ARC_AUTHORITY_CAPTIONS)
    random.shuffle(pool)
    micro_tags = ["", "\n⚡", "\n🗝️", "\n▪️"]
    return [f"{pool[i % len(pool)]}{random.choice(micro_tags)}".strip() for i in range(count)]

# ==========================================
# 3. VIDEO-ONLY SCRAPER (NO SONG CLIPS / NO PHOTO POSTS)
# ==========================================
def unescape_ig_payload(raw_text):
    if not raw_text:
        return ""
    s = raw_text.replace(r"\\/", "/").replace(r"\/", "/")
    s = s.replace(r"\\u0026", "&").replace(r"\u0026", "&")
    s = s.replace(r'\\"', '"').replace(r'\"', '"')
    return s.replace("&quot;", '"').replace("&amp;", "&")

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
    log(f"[FLEET WAVE] Selected & randomized {len(selected)}/{total} accounts for this 30-min cycle.")
    return selected

def get_media_duration(input_path):
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_path]
        res = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        return float(res.stdout.decode("utf-8").strip())
    except Exception:
        return 0.0

def verify_high_quality_reel_source(video_path):
    if not os.path.exists(video_path) or os.path.getsize(video_path) < 350000:
        return False
    try:
        dur = get_media_duration(video_path)
        if dur < 9.0 or dur > 90.0:
            return False
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,nb_frames",
            "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ]
        res = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        lines = [x.strip() for x in res.stdout.decode("utf-8").strip().splitlines() if x.strip()]
        if len(lines) < 2:
            return False
        w, h = int(lines[0]), int(lines[1])
        if w < 480 or h < 640:
            return False
        if len(lines) >= 3 and lines[2].isdigit() and int(lines[2]) < 180:
            return False
        return True
    except Exception:
        return False

def video_has_audio_stream(video_path):
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path]
        res = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        return len(res.stdout.decode("utf-8").strip()) > 0
    except Exception:
        return False

def save_and_verify_stream(raw_url, out_path, headers=None):
    if not raw_url or not raw_url.startswith("http"):
        return False
    req_headers = headers or BROWSER_HEADERS
    try:
        r = requests.get(raw_url, headers=req_headers, allow_redirects=True, timeout=25)
        if r.status_code == 200 and len(r.content) > 350000:
            with open(out_path, "wb") as f:
                f.write(r.content)
            if verify_high_quality_reel_source(out_path):
                return True
            if os.path.exists(out_path):
                os.remove(out_path)
    except Exception:
        pass
    return False

def harvest_handle_videos_only(handle, seen_shortcodes, dead_shortcodes, catalog):
    count = 0
    embed_urls = [
        f"https://www.instagram.com/{handle}/embed/",
        f"https://www.instagram.com/{handle}/embed/captioned/"
    ]
    for embed_url in embed_urls:
        try:
            r = requests.get(embed_url, headers=BROWSER_HEADERS, timeout=15)
            if r.status_code == 200 and len(r.text) > 500:
                clean_html = unescape_ig_payload(r.text)
                pair_pattern = r'"shortcode"\s*:\s*"([A-Za-z0-9_-]{8,15})"[^{}]*?"video_url"\s*:\s*"(https?://[^"]+)"'
                for match in re.finditer(pair_pattern, clean_html):
                    sc, v_url = match.group(1), match.group(2)
                    cid = f"ig_{sc}"
                    if cid not in seen_shortcodes and cid not in dead_shortcodes:
                        seen_shortcodes.add(cid)
                        catalog.append((cid, v_url, f"https://www.instagram.com/reel/{sc}/", handle))
                        count += 1
                video_node_scs = re.findall(r'"__typename"\s*:\s*"GraphVideo"[^{}]*?"shortcode"\s*:\s*"([A-Za-z0-9_-]{8,15})"', clean_html)
                video_node_scs += re.findall(r'"shortcode"\s*:\s*"([A-Za-z0-9_-]{8,15})"[^{}]*?"is_video"\s*:\s*true', clean_html)
                video_node_scs += re.findall(r'/reel/([A-Za-z0-9_-]{8,15})/', clean_html)
                for sc in video_node_scs:
                    if sc in ("embed", "captioned", handle):
                        continue
                    cid = f"ig_{sc}"
                    if cid not in seen_shortcodes and cid not in dead_shortcodes:
                        seen_shortcodes.add(cid)
                        catalog.append((cid, "", f"https://www.instagram.com/reel/{sc}/", handle))
                        count += 1
            if count > 0:
                break
        except Exception:
            continue
    return count

def build_master_reel_catalog_once(dead_shortcodes):
    catalog = []
    seen_shortcodes = set()
    if os.path.exists(LINKS_FILE):
        try:
            with open(LINKS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    clean_u, cid = resolve_and_normalize_link(line.strip())
                    if clean_u and cid and cid not in seen_shortcodes and cid not in dead_shortcodes:
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
        c = harvest_handle_videos_only(handle, seen_shortcodes, dead_shortcodes, catalog)
        log(f"[CATALOG] Pulled {c} verified video Reels from @{handle}")
    with_cdn = [x for x in catalog if x[1]]
    without_cdn = [x for x in catalog if not x[1]]
    random.shuffle(with_cdn)
    random.shuffle(without_cdn)
    combined = with_cdn + without_cdn
    log(f"[CATALOG READY] {len(combined)} video Reels available ({len(with_cdn)} with direct HD stream)")
    return combined

def try_route_embed_page(shortcode, out_path):
    for prefix in ["reel", "p"]:
        for suffix in ["embed/captioned/", "embed/"]:
            embed_url = f"https://www.instagram.com/{prefix}/{shortcode}/{suffix}"
            try:
                r = requests.get(embed_url, headers=BROWSER_HEADERS, timeout=15)
                if r.status_code == 200 and len(r.text) > 500:
                    clean_html = unescape_ig_payload(r.text)
                    if '"is_video":false' in clean_html and '"video_url"' not in clean_html:
                        return False
                    urls = re.findall(r'"video_url"\s*:\s*"(https?://[^"]+)"', clean_html)
                    urls += re.findall(r'"contentUrl"\s*:\s*"(https?://[^"]+)"', clean_html)
                    urls += re.findall(r'<meta[^>]+property="og:video"[^>]+content="(https?://[^"]+)"', clean_html)
                    for u in urls:
                        if save_and_verify_stream(u, out_path):
                            return True
            except Exception:
                pass
    return False

def try_route_bot_proxies(shortcode, out_path):
    for host in ["www.vxinstagram.com", "d.ddinstagram.com", "www.ddinstagram.com", "www.kkinstagram.com"]:
        proxy_url = f"https://{host}/reel/{shortcode}"
        try:
            r = requests.get(proxy_url, headers=BOT_EMBED_HEADERS, allow_redirects=True, timeout=18)
            if r.status_code == 200:
                if len(r.content) > 350000 and "video" in r.headers.get("Content-Type", "").lower():
                    with open(out_path, "wb") as f:
                        f.write(r.content)
                    if verify_high_quality_reel_source(out_path):
                        return True
                    if os.path.exists(out_path):
                        os.remove(out_path)
                clean_html = unescape_ig_payload(r.text)
                og_urls = re.findall(r'<meta[^>]+property="og:video(?::secure_url)?"[^>]+content="(https?://[^"]+)"', clean_html)
                for og_u in og_urls:
                    if save_and_verify_stream(og_u, out_path):
                        return True
        except Exception:
            pass
    try:
        vx_api = f"https://api.vxinstagram.com/reel/{shortcode}"
        r = requests.get(vx_api, headers=BOT_EMBED_HEADERS, timeout=15)
        if r.status_code == 200 and r.text.strip().startswith("{"):
            for m in r.json().get("media_extended") or []:
                if m.get("type") in ("video", "reel", None) and save_and_verify_stream(m.get("url", ""), out_path):
                    return True
    except Exception:
        pass
    return False

def try_route_graphql_and_ytdlp(shortcode, clean_url, out_path):
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
                    if save_and_verify_stream(raw_cdn, out_path):
                        return True
        except Exception:
            pass
    ydl_opts = {
        "format": "bestvideo[height<=1920][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": out_path,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "logger": SilentYTDLLogger(),
        "socket_timeout": 18,
        "http_headers": BROWSER_HEADERS
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(clean_url, download=True)
        if verify_high_quality_reel_source(out_path):
            return True
        if os.path.exists(out_path):
            os.remove(out_path)
    except Exception:
        if os.path.exists(out_path):
            try:
                os.remove(out_path)
            except Exception:
                pass
    return False

def download_instagram_reel_all_routes(clean_url, out_path):
    ig_match = re.search(r'/(?:reel|reels|p)/([A-Za-z0-9_-]+)', clean_url)
    shortcode = ig_match.group(1) if ig_match else ""
    if not shortcode:
        return False
    if try_route_embed_page(shortcode, out_path):
        return True
    if try_route_bot_proxies(shortcode, out_path):
        return True
    if try_route_graphql_and_ytdlp(shortcode, clean_url, out_path):
        return True
    return False

def pick_random_reel_for_account(ig_user_id, master_catalog, posted_history, downloaded_cache, dead_shortcodes, used_in_wave):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    eligible = [
        item for item in master_catalog
        if item[0] not in dead_shortcodes and f"{ig_user_id}:{item[0]}" not in posted_history
    ]
    if not eligible:
        eligible = [item for item in master_catalog if item[0] not in dead_shortcodes]
    fresh_with_cdn = [item for item in eligible if item[0] not in used_in_wave and item[1]]
    fresh_no_cdn = [item for item in eligible if item[0] not in used_in_wave and not item[1]]
    used_already = [item for item in eligible if item[0] in used_in_wave]
    random.shuffle(fresh_with_cdn)
    random.shuffle(fresh_no_cdn)
    random.shuffle(used_already)
    candidates = fresh_with_cdn + fresh_no_cdn + used_already
    for canonical_id, media_url, permalink, source_handle in candidates:
        if canonical_id in downloaded_cache and os.path.exists(downloaded_cache[canonical_id]):
            used_in_wave.add(canonical_id)
            log(f"[RANDOM PICK] Selected verified Reel {canonical_id} (from @{source_handle}) for {ig_user_id}")
            return canonical_id, downloaded_cache[canonical_id]
        full_path = os.path.join(ASSETS_DIR, f"master_{canonical_id}.mp4")
        downloaded = False
        if media_url:
            downloaded = save_and_verify_stream(media_url, full_path)
        if not downloaded and permalink:
            downloaded = download_instagram_reel_all_routes(permalink, full_path)
        if downloaded:
            downloaded_cache[canonical_id] = full_path
            used_in_wave.add(canonical_id)
            log(f"[RANDOM PICK] Downloaded HD Reel {canonical_id} (from @{source_handle}) for {ig_user_id}")
            return canonical_id, full_path
        append_to_set_file(DEAD_SHORTCODES_FILE, canonical_id, dead_shortcodes)
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
# 6. ULTRA-HD GOLD STYLISH FONT & UNCUT AI VOICEOVER ENGINE
# ==========================================
def ensure_stylish_luxury_font():
    if os.path.exists(STYLISH_FONT_PATH) and os.path.getsize(STYLISH_FONT_PATH) > 15000:
        return STYLISH_FONT_PATH
    font_urls = [
        "https://github.com/google/fonts/raw/main/ofl/cinzel/static/Cinzel-Bold.ttf",
        "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/static/PlayfairDisplay-Bold.ttf",
        "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf"
    ]
    for f_url in font_urls:
        try:
            res = requests.get(f_url, timeout=(10, 20))
            if res.status_code == 200 and len(res.content) > 15000:
                with open(STYLISH_FONT_PATH, "wb") as f:
                    f.write(res.content)
                return STYLISH_FONT_PATH
        except Exception:
            continue
    return "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

def generate_neural_voiceover(out_mp3_path):
    script_text = random.choice(ARC_VOICEOVER_SCRIPTS)
    raw_vo = f"{out_mp3_path}_raw.mp3"
    voices = ["en-US-AndrewMultilingualNeural", "en-US-BrianMultilingualNeural", "en-US-ChristopherNeural"]
    for voice_name in voices:
        try:
            cmd = [
                "edge-tts",
                "--voice", voice_name,
                "--rate=+2%",
                "--pitch=-2Hz",
                "--text", script_text,
                "--write-media", raw_vo
            ]
            subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
            if os.path.exists(raw_vo) and os.path.getsize(raw_vo) > 4000:
                trim_cmd = [
                    "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                    "-i", raw_vo,
                    "-af", "silenceremove=start_periods=1:start_silence=0.05:start_threshold=-45dB",
                    out_mp3_path
                ]
                subprocess.run(trim_cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
                if os.path.exists(raw_vo):
                    os.remove(raw_vo)
                if os.path.exists(out_mp3_path) and os.path.getsize(out_mp3_path) > 3000:
                    return True
        except Exception:
            continue
    if os.path.exists(raw_vo):
        try:
            os.remove(raw_vo)
        except Exception:
            pass
    return False

def mutate_video_for_account(input_path, output_path, font_path, node_idx=0):
    vo_path = f"vo_temp_{node_idx}_{random.randint(100,999)}.mp3"
    has_vo = False
    vo_dur = 4.2
    try:
        has_vo = generate_neural_voiceover(vo_path)
        if has_vo:
            measured = get_media_duration(vo_path)
            if measured > 1.5:
                vo_dur = measured
    except Exception:
        has_vo = False

    raw_dur = get_media_duration(input_path)
    if 11.0 <= raw_dur <= 15.0:
        final_duration = round(raw_dur, 2)
    elif raw_dur > 15.0:
        final_duration = round(random.uniform(12.5, 15.0), 2)
    else:
        final_duration = round(random.uniform(11.5, 13.8), 2)

    min_needed_dur = round(vo_dur + 6.0, 2)
    if final_duration < min_needed_dur:
        final_duration = min(15.0, min_needed_dur)

    pitch_start = round(max(4.5, final_duration - vo_dur - 0.55), 2)
    pitch_delay_ms = int(pitch_start * 1000)

    epoch_jitter = int(time.time()) - random.randint(600, 259200)
    msg_tuple = random.choice(ARC_UNIFIED_MESSAGES)
    top_hook, center_line1, center_line2 = [t.replace("'", "").replace(":", " -") for t in msg_tuple]

    top_y = random.randint(235, 275)
    center_y_shift = random.choice([-20, 0, 20])
    c1_y = f"(h/2)-44+{center_y_shift}"
    c2_y = f"(h/2)+26+{center_y_shift}"
    band_y = f"(h/2)-96+{center_y_shift}"

    vf_chain = (
        f"scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos+accurate_rnd+full_chroma_int,"
        f"crop=1080:1920,fps=30,"
        f"eq=contrast=1.04:saturation=1.06,"
        f"unsharp=lx=5:ly=5:la=0.65:cx=3:cy=3:ca=0.15,"
        f"drawtext=fontfile={font_path}:text='{top_hook}':expansion=none:"
        f"fontcolor={GOLD_HEX}:fontsize=26:shadowcolor=black@0.98:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.82:boxborderw=16:"
        f"x=(w-text_w)/2:y={top_y}:enable='lt(t,{pitch_start})',"
        f"drawbox=x=0:y={band_y}:w=iw:h=185:color=black@0.72:t=fill:enable='gte(t,{pitch_start})',"
        f"drawtext=fontfile={font_path}:text='{center_line1}':expansion=none:"
        f"fontcolor={GOLD_HEX}:fontsize=22:shadowcolor=black@0.98:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.92:boxborderw=14:"
        f"x=(w-text_w)/2:y={c1_y}:enable='gte(t,{pitch_start})',"
        f"drawtext=fontfile={font_path}:text='{center_line2}':expansion=none:"
        f"fontcolor={GOLD_HEX}:fontsize=23:shadowcolor=black@0.98:shadowx=2:shadowy=2:"
        f"box=1:boxcolor=black@0.92:boxborderw=14:"
        f"x=(w-text_w)/2:y={c2_y}:enable='gte(t,{pitch_start})'"
    )

    fade_out_st = round(max(1.0, final_duration - 0.30), 2)
    has_orig_audio = video_has_audio_stream(input_path)

    try:
        if has_orig_audio and has_vo:
            filter_complex = (
                f"[0:v]{vf_chain}[vout];"
                f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"volume=1.0:enable='lt(t,{pitch_start})',volume=0.20:enable='gte(t,{pitch_start})'[bg];"
                f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"adelay={pitch_delay_ms}|{pitch_delay_ms},volume=2.10,apad[vo];"
                f"[bg][vo]amix=inputs=2:duration=first:dropout_transition=0,"
                f"afade=t=out:st={fade_out_st}:d=0.30[aout]"
            )
            cmd = [
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-stream_loop", "-1", "-t", str(final_duration), "-i", input_path,
                "-i", vo_path,
                "-filter_complex", filter_complex,
                "-map", "[vout]", "-map", "[aout]",
                "-t", str(final_duration),
                "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.2",
                "-crf", "16", "-maxrate", "10M", "-bufsize", "16M",
                "-preset", "faster", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-map_metadata", "-1", "-metadata", f"creation_time={epoch_jitter}",
                output_path
            ]
            res = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
            if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 200000:
                return output_path

        fallback_cmd = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-stream_loop", "-1", "-t", str(final_duration), "-i", input_path,
            "-vf", vf_chain,
            "-t", str(final_duration),
            "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.2",
            "-crf", "16", "-maxrate", "10M", "-bufsize", "16M",
            "-preset", "faster", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-map_metadata", "-1", "-metadata", f"creation_time={epoch_jitter}",
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
            res = requests.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload"}, files={"fileToUpload": f}, headers=headers, timeout=(15, 90))
        if res.status_code == 200 and res.text.strip().startswith("https://"):
            return res.text.strip()
    except Exception:
        pass
    try:
        with open(file_path, "rb") as f:
            res = requests.post("https://litterbox.catbox.moe/resources/internals/api.php", data={"reqtype": "fileupload", "time": "1h"}, files={"fileToUpload": f}, headers=headers, timeout=(15, 90))
        if res.status_code == 200 and res.text.strip().startswith("https://"):
            return res.text.strip()
    except Exception:
        pass
    try:
        with open(file_path, "rb") as f:
            res = requests.post("https://uguu.se/upload", files={"files[]": f}, headers=headers, timeout=(15, 90)).json()
        if res.get("success") and res.get("files"):
            return res["files"][0]["url"]
    except Exception:
        pass
    try:
        with open(file_path, "rb") as f:
            response = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, headers=headers, timeout=(15, 90)).json()
        if "data" in response and "url" in response["data"]:
            return response["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")
    except Exception:
        pass
    with open(file_path, "rb") as f:
        res = requests.post("https://0x0.st", files={"file": f}, headers=headers, timeout=(15, 90))
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
        "thumb_offset": str(random.randint(1500, 3500)),
        "access_token": token
    }
    res = requests.post(container_url, data=payload, timeout=(10, 30)).json()
    if "id" not in res:
        raise Exception(f"Container failed: {res}")
    creation_id = res["id"]
    status_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{creation_id}"
    time.sleep(22)
    for _ in range(18):
        status_res = requests.get(status_url, params={"fields": "status_code,status", "access_token": token}, timeout=(10, 20)).json()
        status_code = status_res.get("status_code")
        if status_code == "FINISHED":
            break
        elif status_code in ("ERROR", "EXPIRED"):
            raise Exception(f"Meta rejected video: {status_res}")
        time.sleep(10)
    else:
        raise Exception("Meta video processing timed out.")
    publish_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}/media_publish"
    publish_res = requests.post(publish_url, data={"creation_id": creation_id, "access_token": token}, timeout=(10, 30)).json()
    if "id" not in publish_res:
        raise Exception(f"Publish failed: {publish_res}")
    log(f"[SUCCESS] PUBLISHED ULTRA-HD REEL! Media ID: {publish_res['id']}")

# ==========================================
# 8. MAIN EXECUTION
# ==========================================
def main():
    log("=== ARC ULTRA-HD GOLD PUBLISHING ENGINE STARTED ===")
    ensure_edge_tts_installed()
    active_tokens = [t.strip() for t in META_TOKENS if t and t.strip()]
    if not active_tokens:
        log("[OVERFLOW] META_TOKEN_1 not found in environment. Exiting cleanly.")
        return
    font_path = ensure_stylish_luxury_font()
    posted_history = load_set_file(HISTORY_FILE)
    dead_shortcodes = load_set_file(DEAD_SHORTCODES_FILE)
    all_accounts = []
    seen_ig_ids = set()
    for token in active_tokens:
        try:
            for a in get_connected_instagram_accounts(token):
                if a["ig_user_id"] not in seen_ig_ids:
                    seen_ig_ids.add(a["ig_user_id"])
                    all_accounts.append(a)
        except Exception as e:
            log(f"[OVERFLOW] Token check warning bypassed: {e}")
    if not all_accounts:
        log("[OVERFLOW] Zero Instagram Business accounts discovered. Exiting cleanly.")
        return

    wave_accounts = select_round_robin_accounts(all_accounts, ACCOUNTS_PER_WAVE)
    caption_batch = generate_unique_caption_batch(len(wave_accounts))
    master_catalog = build_master_reel_catalog_once(dead_shortcodes)
    downloaded_cache = {}
    used_in_wave = set()
    success_count = 0
    try:
        for index, acc in enumerate(wave_accounts):
            ig_uid = str(acc["ig_user_id"])
            log(f"\n--- NODE [{index+1}/{len(wave_accounts)}]: {acc['page_name']} ({ig_uid}) ---")
            mutated_output = f"arc_uhd_gold_{index}.mp4"
            try:
                chosen_id, source_video = pick_random_reel_for_account(
                    ig_uid,
                    master_catalog,
                    posted_history,
                    downloaded_cache,
                    dead_shortcodes,
                    used_in_wave
                )
                if not source_video or not os.path.exists(source_video):
                    log(f"[OVERFLOW] No downloadable 10-15s Reel found for {acc['page_name']}, moving to next node...")
                    continue
                mutate_video_for_account(source_video, mutated_output, font_path, node_idx=index)
                public_url = upload_for_meta_download(mutated_output)
                publish_reel_to_instagram(ig_uid, public_url, caption_batch[index], acc["token"])
                append_to_set_file(HISTORY_FILE, f"{ig_uid}:{chosen_id}", posted_history)
                success_count += 1
            except Exception as e:
                log(f"[OVERFLOW] Bypassed error on {acc['page_name']} and continuing wave: {e}")
            finally:
                if os.path.exists(mutated_output):
                    try:
                        os.remove(mutated_output)
                    except Exception:
                        pass
            if index < len(wave_accounts) - 1:
                cooldown_sec = random.randint(MIN_COOLDOWN_SECONDS, MAX_COOLDOWN_SECONDS)
                log(f"[TIMER] Waiting {cooldown_sec}s before next account...")
                time.sleep(cooldown_sec)
    finally:
        for cached_file in downloaded_cache.values():
            if cached_file and os.path.exists(cached_file):
                try:
                    os.remove(cached_file)
                except Exception:
                    pass
    log(f"\n=== WAVE COMPLETE: {success_count}/{len(wave_accounts)} ULTRA-HD GOLD REELS PUBLISHED ===")

if __name__ == "__main__":
    try:
        main()
    except Exception as fatal_err:
        log(f"[GLOBAL OVERFLOW] Exception caught: {fatal_err}")
        sys.exit(0)
