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
# 1. CORE 1-HOUR BRACKET CONFIGURATION
# ==========================================
META_TOKENS = [
    os.getenv("META_TOKEN_1"),
    os.getenv("META_TOKEN_2")
]

GRAPH_API_VERSION = "v20.0"

# All connected accounts post 1 Reel per 1-hour wave
ACCOUNTS_PER_WAVE = 23
# Target 3,180s (53 mins) across all accounts so the entire wave + git save finishes inside 1 hour (3,600s)
TARGET_WAVE_WINDOW_SECONDS = 3180

LINKS_FILE = "reel_links.txt"
HISTORY_FILE = "arc_ig_history.txt"
DEAD_SHORTCODES_FILE = "arc_dead_shortcodes.txt"
DISCOVERED_POOL_FILE = "arc_discovered_pool.txt"
ASSETS_DIR = "assets"
STYLISH_FONT_PATH = "Cinzel-Bold.ttf"

# Your exact 7 scraping accounts (intensecorb deduplicated automatically)
TARGET_IG_ACCOUNTS_TO_SCRAPE = [
    "https://www.instagram.com/luxereturns?utm_source=ig_web_button_share_sheet&mdxt=ZDNlZDc0MzIxNw==",
    "https://www.instagram.com/luxuriaaura?utm_source=ig_web_button_share_sheet&mdxt=ZDNlZDc0MzIxNw==",
    "https://www.instagram.com/intensecorb?utm_source=ig_web_button_share_sheet&mdxt=ZDNlZDc0MzIxNw==",
    "https://www.instagram.com/heritageclass?utm_source=ig_web_button_share_sheet&xtok=ZDNlZDc0MzIxNw==",
    "https://www.instagram.com/worthy?utm_source=ig_web_button_share_sheet&mdxt=ZDNlZDc0MzIxNw==",
    "https://www.instagram.com/luxurcore?utm_source=ig_web_button_share_sheet&rpxt=ZDNlZDc0MzIxNw==",
    "https://www.instagram.com/toptierclasy?utm_source=ig_web_button_share_sheet&exln=ZDNlZDc0MzIxNw=="
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

CAPTION_OPENERS = [
    "Most men spend their best years building someone else's dream.",
    "Hard work alone never made anyone wealthy—leverage and systems do.",
    "If you repeat the last 6 months for the next 5 years, nothing changes.",
    "The difference between wishing and owning is the system you execute daily.",
    "Stop watching from the sidelines while operators build real digital assets.",
    "Freedom isn't bought with a monthly salary. It's built with online cashflow.",
    "Nobody is coming to hand you the blueprint. You have to step up and claim it.",
    "Comfort is the most expensive trap a man can fall into."
]

CAPTION_BODIES = [
    "Inside ARC, we break down the exact digital wealth architecture to build independent online income from scratch.",
    "ARC gives you the private network, scalable digital models, and step-by-step execution blueprint.",
    "We built ARC for ambitious men ready to replace guesswork with a proven online income system.",
    "Step inside the private ARC ecosystem and start building real digital leverage alongside serious operators."
]

CAPTION_CTAS = [
    "Tap the link in bio to enter ARC today.",
    "Check @arcbloodline30 bio to claim your spot inside ARC.",
    "Access the private portal via @arcbloodline30 bio right now.",
    "Use the main link in bio (or visit @arcbloodline30) before doors close."
]

NICHE_TAGS_POOL = [
    "#luxurylifestyle", "#wealthmindset", "#entrepreneurship", "#digitalbusiness",
    "#financialfreedom", "#oldmoney", "#successmindset", "#onlineincome",
    "#billionairemindset", "#wealthbuilding", "#onlinebusiness", "#menwithclass",
    "#financialindependence", "#mindset", "#businessowner", "#millionairemindset",
    "#selfimprovement", "#oldmoneyaesthetic", "#moneymindset", "#wealthcreation"
]

NICHE_LABELS = [
    "Niche: Wealth Architecture • Digital Business • Luxury Mindset",
    "Category: Online Income Systems • Men's Self-Improvement • High-Status Living",
    "Focus: Financial Sovereignty • Digital Entrepreneurship • Private Wealth Network",
    "Topic: Scalable Online Assets • Wealth Creation • Executive Mindset"
]

def generate_unique_caption_batch(count):
    captions = []
    for _ in range(count):
        opener = random.choice(CAPTION_OPENERS)
        body = random.choice(CAPTION_BODIES)
        cta = random.choice(CAPTION_CTAS)
        label = random.choice(NICHE_LABELS)
        tags = " ".join(random.sample(NICHE_TAGS_POOL, k=4))
        captions.append(f"{opener}\n\n{body}\n\n{cta}\n\n{label}\n{tags}")
    return captions

# ==========================================
# 3. DEEP MULTI-ROUTE HARVESTER (ALL EXISTING REELS)
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

def select_hourly_ordered_accounts(all_accounts, batch_size):
    """
    Keeps a consistent account sequence across every 1-hour wave so Account #k
    always posts at approximately the same minute mark every hour (~60 mins apart).
    """
    sorted_accs = sorted(all_accounts, key=lambda x: str(x["ig_user_id"]))
    selected = sorted_accs[:min(batch_size, len(sorted_accs))]
    log(f"[HOURLY WAVE] Locked {len(selected)} accounts in 1-hour cadence order.")
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

def harvest_handle_all_existing_reels(handle, seen_shortcodes, dead_shortcodes, discovered_pool_set, catalog):
    count = 0
    # Route 1: Embed & Captioned Embed HTML extraction
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
                    if cid not in dead_shortcodes:
                        append_to_set_file(DISCOVERED_POOL_FILE, f"{handle}|{cid}", discovered_pool_set)
                        if cid not in seen_shortcodes:
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
                    if cid not in dead_shortcodes:
                        append_to_set_file(DISCOVERED_POOL_FILE, f"{handle}|{cid}", discovered_pool_set)
                        if cid not in seen_shortcodes:
                            seen_shortcodes.add(cid)
                            catalog.append((cid, "", f"https://www.instagram.com/reel/{sc}/", handle))
                            count += 1
        except Exception:
            continue

    # Route 2: Deep Reels Tab & Profile Timeline discovery via yt-dlp flat extraction
    for profile_url in [f"https://www.instagram.com/{handle}/reels/", f"https://www.instagram.com/{handle}/"]:
        try:
            ydl_opts = {
                "extract_flat": True,
                "playlistend": 60,
                "quiet": True,
                "no_warnings": True,
                "logger": SilentYTDLLogger(),
                "socket_timeout": 12,
                "http_headers": BROWSER_HEADERS
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(profile_url, download=False)
                entries = (info or {}).get("entries") or []
                for entry in entries:
                    if not entry:
                        continue
                    sc = entry.get("id") or ""
                    e_url = entry.get("url") or entry.get("webpage_url") or ""
                    if not sc and e_url:
                        m = re.search(r'/(?:reel|reels|p)/([A-Za-z0-9_-]{8,15})', e_url)
                        if m:
                            sc = m.group(1)
                    if sc and len(sc) >= 8:
                        cid = f"ig_{sc}"
                        if cid not in dead_shortcodes:
                            append_to_set_file(DISCOVERED_POOL_FILE, f"{handle}|{cid}", discovered_pool_set)
                            if cid not in seen_shortcodes:
                                seen_shortcodes.add(cid)
                                catalog.append((cid, "", f"https://www.instagram.com/reel/{sc}/", handle))
                                count += 1
        except Exception:
            continue

    return count

def build_master_reel_catalog_once(dead_shortcodes):
    catalog = []
    seen_shortcodes = set()
    discovered_pool_set = load_set_file(DISCOVERED_POOL_FILE)

    clean_handles = []
    for raw in TARGET_IG_ACCOUNTS_TO_SCRAPE:
        h = extract_ig_handle(raw)
        if h and h not in clean_handles:
            clean_handles.append(h)

    active_handles_set = set(clean_handles)
    random.shuffle(clean_handles)

    # 1. Harvest live reels across all 7 target accounts
    for handle in clean_handles:
        c = harvest_handle_all_existing_reels(handle, seen_shortcodes, dead_shortcodes, discovered_pool_set, catalog)
        log(f"[CATALOG] Harvested {c} video Reels from @{handle}")

    # 2. Load all previously discovered existing Reels belonging to these exact 7 accounts
    for entry in discovered_pool_set:
        if "|" in entry:
            h, cid = entry.split("|", 1)
            h = h.strip().lower()
            cid = cid.strip()
            if h in active_handles_set and cid.startswith("ig_") and cid not in seen_shortcodes and cid not in dead_shortcodes:
                sc = cid[3:]
                seen_shortcodes.add(cid)
                catalog.append((cid, "", f"https://www.instagram.com/reel/{sc}/", h))

    # 3. Also include any manual backup links from reel_links.txt
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

    # Purely shuffle the entire combined catalog so every target account has equal random probability
    random.shuffle(catalog)
    log(f"[CATALOG READY] {len(catalog)} total unique Reels pooled randomly across {len(clean_handles)} target accounts.")
    return catalog

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
    """
    Picks a completely random reel from all existing reels across all 7 scraped accounts.
    Strictly enforces that the same account NEVER reposts a reel it has already posted.
    """
    os.makedirs(ASSETS_DIR, exist_ok=True)
    # Strictly filter out any reel already posted on this specific account
    eligible = [
        item for item in master_catalog
        if item[0] not in dead_shortcodes and f"{ig_user_id}:{item[0]}" not in posted_history
    ]
    if not eligible:
        log(f"[HISTORY GUARD] Account {ig_user_id} has already posted all currently discovered reels.")
        return None, None

    # Pure random shuffle across all scraping accounts (preferring reels not yet used in the current wave)
    not_used_this_wave = [item for item in eligible if item[0] not in used_in_wave]
    already_used_this_wave = [item for item in eligible if item[0] in used_in_wave]
    random.shuffle(not_used_this_wave)
    random.shuffle(already_used_this_wave)
    candidates = not_used_this_wave + already_used_this_wave

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
# 4. GRAPH API ACCOUNT DISCOVERY
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
# 5. DEEP PHASH BREAKER + 3-4s GOLD FINAL LINES + UNCUT VOICEOVER
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
                    "-af", "silenceremove=start_periods=1:start_silence=0.04:start_threshold=-45dB",
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
    vo_dur = 3.8
    try:
        has_vo = generate_neural_voiceover(vo_path)
        if has_vo:
            measured = get_media_duration(vo_path)
            if measured > 1.5:
                vo_dur = measured
    except Exception:
        has_vo = False

    # Guarantee ARC Final Lines last AT LEAST 3.8 to 4.5+ seconds AND 0.85s longer than the voiceover
    outro_duration = max(4.0, round(vo_dur + 0.85, 2))

    # Deep pHash Breaker parameters (no hflip so text stays readable)
    speed_factor = round(random.uniform(1.03, 1.07), 3)
    pts_mult = round(1.0 / speed_factor, 4)
    zoom_w = random.randint(1124, 1168)
    zoom_h = int(zoom_w * 1920 / 1080)
    crop_x = random.randint(8, zoom_w - 1080 - 8)
    crop_y = random.randint(12, zoom_h - 1920 - 12)
    contrast_val = round(random.uniform(1.03, 1.07), 2)
    sat_val = round(random.uniform(1.04, 1.10), 2)
    gamma_val = round(random.uniform(0.96, 1.04), 2)

    raw_dur = get_media_duration(input_path) / speed_factor
    if 11.5 <= raw_dur <= 15.0:
        final_duration = round(raw_dur, 2)
    elif raw_dur > 15.0:
        final_duration = round(random.uniform(12.5, 15.0), 2)
    else:
        final_duration = round(random.uniform(12.0, 14.2), 2)

    # Ensure Top Gold Hook gets at least 6.0s before the 4.0s+ Gold Final Lines & Voiceover begin
    min_needed_dur = round(outro_duration + 6.0, 2)
    if final_duration < min_needed_dur:
        final_duration = min(15.5, min_needed_dur)

    pitch_start = round(final_duration - outro_duration, 2)
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
        f"setpts={pts_mult}*PTS,"
        f"scale={zoom_w}:{zoom_h}:force_original_aspect_ratio=increase:flags=lanczos+accurate_rnd+full_chroma_int,"
        f"crop=1080:1920:{crop_x}:{crop_y},fps=30,"
        f"eq=contrast={contrast_val}:saturation={sat_val}:gamma={gamma_val},"
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

    fade_out_st = round(max(1.0, final_duration - 0.25), 2)
    has_orig_audio = video_has_audio_stream(input_path)

    try:
        if has_orig_audio and has_vo:
            filter_complex = (
                f"[0:v]{vf_chain}[vout];"
                f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"atempo={speed_factor},highpass=f=55,lowpass=f=15200,"
                f"volume=1.0:enable='lt(t,{pitch_start})',volume=0.18:enable='gte(t,{pitch_start})'[bg];"
                f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"adelay={pitch_delay_ms}|{pitch_delay_ms},volume=2.20,apad=whole_dur={final_duration}[vo];"
                f"[bg][vo]amix=inputs=2:duration=first:dropout_transition=0,"
                f"afade=t=out:st={fade_out_st}:d=0.25[aout]"
            )
            cmd = [
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-stream_loop", "-1", "-t", str(round(final_duration * speed_factor + 1.5, 2)), "-i", input_path,
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
            "-stream_loop", "-1", "-t", str(round(final_duration * speed_factor + 1.5, 2)), "-i", input_path,
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
# 6. RELAY UPLOAD & GRAPH API PUBLISH
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
    log(f"[SUCCESS] PUBLISHED 1-HR CADENCE REEL! Media ID: {publish_res['id']}")

# ==========================================
# 7. MAIN EXECUTION (DYNAMIC 1-HOUR BRACKET PACING)
# ==========================================
def main():
    wave_start_ts = time.time()
    log("=== ARC 1-HOUR CADENCE ENGINE STARTED ===")
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

    wave_accounts = select_hourly_ordered_accounts(all_accounts, ACCOUNTS_PER_WAVE)
    total_nodes = len(wave_accounts)
    caption_batch = generate_unique_caption_batch(total_nodes)
    master_catalog = build_master_reel_catalog_once(dead_shortcodes)
    downloaded_cache = {}
    used_in_wave = set()
    success_count = 0

    try:
        for index, acc in enumerate(wave_accounts):
            ig_uid = str(acc["ig_user_id"])
            log(f"\n--- NODE [{index+1}/{total_nodes}]: {acc['page_name']} ({ig_uid}) ---")
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
                    log(f"[OVERFLOW] No unposted Reel available for {acc['page_name']}, moving to next node...")
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

            # Randomized spacing calculated to fit all accounts smoothly inside the 1-hour bracket
            remaining_nodes = total_nodes - 1 - index
            if remaining_nodes > 0:
                elapsed_so_far = time.time() - wave_start_ts
                time_left_in_window = max(0.0, TARGET_WAVE_WINDOW_SECONDS - elapsed_so_far)
                # Estimate ~52s of processing time per remaining account
                estimated_work_time = remaining_nodes * 52.0
                available_sleep_pool = max(remaining_nodes * 15.0, time_left_in_window - estimated_work_time)
                avg_sleep = available_sleep_pool / remaining_nodes
                jitter_min = max(12, int(avg_sleep * 0.65))
                jitter_max = max(jitter_min + 10, min(165, int(avg_sleep * 1.35)))
                cooldown_sec = random.randint(jitter_min, jitter_max)
                log(f"[1-HR PACING] Randomized spacing cooldown: {cooldown_sec}s before next account...")
                time.sleep(cooldown_sec)
    finally:
        for cached_file in downloaded_cache.values():
            if cached_file and os.path.exists(cached_file):
                try:
                    os.remove(cached_file)
                except Exception:
                    pass
    log(f"\n=== HOURLY WAVE COMPLETE: {success_count}/{total_nodes} REELS PUBLISHED IN {int(time.time() - wave_start_ts)}s ===")

if __name__ == "__main__":
    try:
        main()
    except Exception as fatal_err:
        log(f"[GLOBAL OVERFLOW] Exception caught: {fatal_err}")
        sys.exit(0)
