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
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

def ensure_edge_tts_installed():
    try:
        subprocess.run(["edge-tts", "--version"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=True)
    except Exception:
        log("[INIT] Installing edge-tts for neural voiceover...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "edge-tts"], stdin=subprocess.DEVNULL, timeout=60)
        except Exception as e:
            log(f"[OVERFLOW] edge-tts install skipped: {e}")

# ==========================================
# 1. CORE CONFIGURATION & FLEET RULES
# ==========================================
META_TOKENS = [
    t.strip() for t in [
        os.getenv("META_TOKEN_1"),
        os.getenv("META_TOKEN_2"),
        os.getenv("META_TOKEN_3"),
    ]
    if t and t.strip()
]

YT_ID = (os.getenv("YT_CLIENT_ID") or "").strip()
YT_SEC = (os.getenv("YT_CLIENT_SECRET") or "").strip()
YT_TOKS = [t.strip() for t in re.split(r"[\n,]+", os.getenv("YT_REFRESH_TOKENS") or "") if t.strip()]

GRAPH_API_VERSION = "v26.0"

LOGO = "arc_logo.png"
FONT = "Cinzel-Bold.ttf"
EXTRA_BED = "bg_bed.mp3"
ENABLE_4K = True

LINKS_FILE = "reel_links.txt"
HISTORY_FILE = "arc_ig_history.txt"
DEAD_SHORTCODES_FILE = "arc_dead_shortcodes.txt"
DISCOVERED_POOL_FILE = "arc_discovered_pool.txt"
ASSETS_DIR = "assets"

GREEN = {
    "arcbloodline2", "arcbloodline3", "arcbloodline4", "arcbloodline9",
    "arcbloodline19", "arcbloodline20", "arcbloodline23", "arcbloodline25",
    "arcbloodline26",
}
FLAGGED = {f"arcbloodline{i}" for i in range(1, 27)} - GREEN

DEFAULT_TARGET_IG_ACCOUNTS = [
    "https://www.instagram.com/heriitageborn?bqrl=MWdybGdiZnp6NDJqbw==",
    "https://www.instagram.com/worthy?knvt=MWZzMG9oOXo0Z2plag==",
    "https://www.instagram.com/aureonlux?avpt=MTJzNmY5cGNpbWZi",
    "https://www.instagram.com/luxurclassy?dmpr=MWNnYnVsbGUxcGpjaw==",
    "https://www.instagram.com/leornabs?gwpx=cHUwejFhYWNqeTVx",
]

_ENV_SOURCES = [u.strip() for u in re.split(r"[\n,]+", os.getenv("IG_SOURCE_ACCOUNTS") or "") if u.strip()]
TARGET_IG_ACCOUNTS_TO_SCRAPE = _ENV_SOURCES if _ENV_SOURCES else DEFAULT_TARGET_IG_ACCOUNTS

USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"
]

BROWSER_HEADERS = {
    "User-Agent": USER_AGENTS[0],
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

BOT_EMBED_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)",
    "Accept": "*/*"
}

# ==========================================
# 2. ARC CTA ONE-LINERS, CAPTIONS & TITLES
# ==========================================
ONE_LINERS = [
    "Stop watching. Enter ARC.",
    "Your seat inside ARC waits.",
    "Build in silence. Enter ARC.",
    "Claim your place inside ARC.",
    "Doors to ARC are open.",
    "The blueprint lives inside ARC.",
    "Enter ARC. Link in bio.",
    "Step inside ARC today.",
    "Leave average behind. Enter ARC.",
]

BODIES = [
    "Most men spend years watching while a few quietly build leverage.\n\nEverything you need to leave the average lane is mapped out inside ARC.",
    "Nobody hands you freedom. Build an independent system now or trade your hours forever.\n\nARC is built for men who execute in silence.",
    "Your circle sets your ceiling. Sit with spectators and stay stuck. Step inside a room of operators building real online cashflow.",
    "A fixed paycheck caps your life before you even begin. Ownership buys your time back.\n\nSee what is waiting inside ARC.",
    "Discipline creates leverage. Leverage creates freedom.\n\nDoors inside ARC do not stay open forever.",
]

CTAS = [
    "Link in bio to enter ARC.",
    "Comment \"ARC\" or tap the bio link.",
    "Step inside ARC through the link in bio.",
    "Bio link is live. Enter ARC.",
]

TAGS = [
    "#wealthmindset", "#oldmoney", "#digitalbusiness", "#financialfreedom",
    "#entrepreneurship", "#onlineincome", "#successmindset", "#businessowner",
    "#selfimprovement", "#wealthbuilding", "#darkluxury", "#mindset",
]

TITLES = [
    "Build in Silence. Enter ARC. #Shorts",
    "Stop Watching. Start Building. #Shorts",
    "Why Silent Operators Always Win #Shorts",
    "Ownership Beats a Paycheck #Shorts",
    "The Blueprint Nobody Talks About #Shorts",
]

def build_caption(i):
    return f"{random.choice(BODIES)}\n\n{CTAS[i % len(CTAS)]}\n\n{' '.join(random.sample(TAGS, k=random.randint(2, 4)))}"

# ==========================================
# 3. 5-LAYER AUTONOMOUS REEL HARVESTER (UNMODIFIED)
# ==========================================
def unescape_ig_payload(raw_text):
    if not raw_text:
        return ""
    s = raw_text
    for _ in range(2):
        s = s.replace(r"\\/", "/").replace(r"\/", "/")
        s = s.replace(r"\\u0026", "&").replace(r"\u0026", "&")
        s = s.replace(r"\\u0022", '"').replace(r"\u0022", '"')
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

def register_shortcode(handle, sc, v_url, seen_shortcodes, dead_shortcodes, discovered_pool_set, catalog):
    if not sc or len(sc) < 8 or len(sc) > 15:
        return 0
    reserved = {"embed", "captioned", "reels", "stories", "explore", "accounts", handle.lower()}
    if sc.lower() in reserved:
        return 0
    cid = f"ig_{sc}"
    if cid in dead_shortcodes:
        return 0
    append_to_set_file(DISCOVERED_POOL_FILE, f"{handle}|{cid}", discovered_pool_set)
    if cid not in seen_shortcodes:
        seen_shortcodes.add(cid)
        catalog.append((cid, v_url or "", f"https://www.instagram.com/reel/{sc}/", handle))
        return 1
    return 0

def extract_all_shortcodes_from_text(handle, raw_text, seen_shortcodes, dead_shortcodes, discovered_pool_set, catalog):
    added = 0
    clean = unescape_ig_payload(raw_text)
    # 1. Direct shortcode + video_url pairs
    for m in re.finditer(r'"shortcode"\s*:\s*"([A-Za-z0-9_-]{8,15})".{0,1200}?"video_url"\s*:\s*"(https?://[^"]+)"', clean, re.DOTALL):
        added += register_shortcode(handle, m.group(1), m.group(2), seen_shortcodes, dead_shortcodes, discovered_pool_set, catalog)
    # 2. All JSON shortcode fields (fixes the nested dimensions object bug)
    for sc in re.findall(r'"shortcode"\s*:\s*"([A-Za-z0-9_-]{8,15})"', clean):
        added += register_shortcode(handle, sc, "", seen_shortcodes, dead_shortcodes, discovered_pool_set, catalog)
    # 3. All /reel/SHORTCODE and /p/SHORTCODE links in HTML or Markdown
    for sc in re.findall(r'instagram\.com/(?:[A-Za-z0-9_.-]+/)?(?:reel|reels|p)/([A-Za-z0-9_-]{8,15})', clean):
        added += register_shortcode(handle, sc, "", seen_shortcodes, dead_shortcodes, discovered_pool_set, catalog)
    for sc in re.findall(r'/(?:reel|reels|p)/([A-Za-z0-9_-]{8,15})/', clean):
        added += register_shortcode(handle, sc, "", seen_shortcodes, dead_shortcodes, discovered_pool_set, catalog)
    return added

def harvest_handle_all_existing_reels(handle, seen_shortcodes, dead_shortcodes, discovered_pool_set, catalog):
    count = 0
    session = requests.Session()

    # LAYER 1: Instagram Embed & Captioned Embed (Unrestricted JSON + HTML parser)
    for embed_url in [f"https://www.instagram.com/{handle}/embed/captioned/", f"https://www.instagram.com/{handle}/embed/"]:
        try:
            headers = dict(BROWSER_HEADERS)
            headers["User-Agent"] = random.choice(USER_AGENTS)
            r = session.get(embed_url, headers=headers, timeout=15)
            if r.status_code == 200 and len(r.text) > 400:
                count += extract_all_shortcodes_from_text(handle, r.text, seen_shortcodes, dead_shortcodes, discovered_pool_set, catalog)
        except Exception:
            pass

    # LAYER 2: Instagram Web Profile Info API + GraphQL 50-Reel Deep Pagination
    try:
        api_headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "X-IG-App-ID": "936619743392459",
            "X-ASBD-ID": "129477",
            "X-IG-WWW-Claim": "0",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "*/*",
            "Referer": f"https://www.instagram.com/{handle}/"
        }
        info_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={handle}"
        r = session.get(info_url, headers=api_headers, timeout=15)
        if r.status_code == 200 and len(r.text) > 200:
            count += extract_all_shortcodes_from_text(handle, r.text, seen_shortcodes, dead_shortcodes, discovered_pool_set, catalog)
            uid_match = re.search(r'"id"\s*:\s*"(\d{5,25})"', r.text)
            if uid_match:
                ig_uid = uid_match.group(1)
                variables = json.dumps({"id": ig_uid, "first": 50})
                for q_hash in ["69cba40317214236af40e7efa697781d", "e769aa130647d2354c40ea6a439bfc08"]:
                    gql_url = f"https://www.instagram.com/graphql/query/?query_hash={q_hash}&variables={urllib.parse.quote(variables)}"
                    gr = session.get(gql_url, headers=api_headers, timeout=15)
                    if gr.status_code == 200 and len(gr.text) > 200:
                        count += extract_all_shortcodes_from_text(handle, gr.text, seen_shortcodes, dead_shortcodes, discovered_pool_set, catalog)
    except Exception:
        pass

    # LAYER 3: Public Web Mirrors & Jina Reader Proxy (Bypasses Datacenter IP Blocks)
    mirror_urls = [
        f"https://r.jina.ai/https://www.instagram.com/{handle}/reels/",
        f"https://r.jina.ai/https://www.instagram.com/{handle}/",
        f"https://www.ddinstagram.com/u/{handle}"
    ]
    for m_url in mirror_urls:
        if count >= 12:
            break
        try:
            r = requests.get(m_url, headers=BROWSER_HEADERS, timeout=14)
            if r.status_code == 200 and len(r.text) > 200:
                count += extract_all_shortcodes_from_text(handle, r.text, seen_shortcodes, dead_shortcodes, discovered_pool_set, catalog)
        except Exception:
            pass

    # LAYER 4: yt-dlp Flat Profile Extraction
    if count < 8:
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
                    for entry in (info or {}).get("entries") or []:
                        if not entry:
                            continue
                        sc = entry.get("id") or ""
                        e_url = entry.get("url") or entry.get("webpage_url") or ""
                        if not sc and e_url:
                            m = re.search(r'/(?:reel|reels|p)/([A-Za-z0-9_-]{8,15})', e_url)
                            if m:
                                sc = m.group(1)
                        count += register_shortcode(handle, sc, "", seen_shortcodes, dead_shortcodes, discovered_pool_set, catalog)
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

    # 1. Harvest live reels across all target accounts
    for handle in clean_handles:
        c = harvest_handle_all_existing_reels(handle, seen_shortcodes, dead_shortcodes, discovered_pool_set, catalog)
        log(f"[CATALOG] Harvested {c} new Reels from @{handle}")
        time.sleep(random.uniform(1.0, 2.2))

    # 2. Load all previously discovered Reels from persistent pool for active handles
    restored = 0
    for entry in discovered_pool_set:
        if "|" in entry:
            h, cid = entry.split("|", 1)
            h, cid = h.strip().lower(), cid.strip()
            if h in active_handles_set and cid.startswith("ig_") and cid not in seen_shortcodes and cid not in dead_shortcodes:
                sc = cid[3:]
                seen_shortcodes.add(cid)
                catalog.append((cid, "", f"https://www.instagram.com/reel/{sc}/", h))
                restored += 1

    # 3. Optional manual backup links if reel_links.txt has any
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

    random.shuffle(catalog)
    log(f"[CATALOG READY] {len(catalog)} total unique Reels available across your {len(clean_handles)} sources ({restored} loaded from saved pool).")
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

def pick_random_reel_for_account(account_key, master_catalog, posted_history, downloaded_cache, dead_shortcodes, used_in_wave):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    # Never repost the same reel on the same account
    eligible = [
        item for item in master_catalog
        if item[0] not in dead_shortcodes and f"{account_key}:{item[0]}" not in posted_history
    ]
    if not eligible:
        log(f"[HISTORY GUARD] Account {account_key} has already posted all currently discovered reels.")
        return None, None

    not_used_this_wave = [item for item in eligible if item[0] not in used_in_wave]
    already_used_this_wave = [item for item in eligible if item[0] in used_in_wave]
    random.shuffle(not_used_this_wave)
    random.shuffle(already_used_this_wave)
    candidates = not_used_this_wave + already_used_this_wave

    for canonical_id, media_url, permalink, source_handle in candidates:
        if canonical_id in downloaded_cache and os.path.exists(downloaded_cache[canonical_id]):
            used_in_wave.add(canonical_id)
            log(f"[RANDOM PICK] Selected verified Reel {canonical_id} (from @{source_handle}) for {account_key}")
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
            log(f"[RANDOM PICK] Downloaded HD Reel {canonical_id} (from @{source_handle}) for {account_key}")
            return canonical_id, full_path
        append_to_set_file(DEAD_SHORTCODES_FILE, canonical_id, dead_shortcodes)
    return None, None

# ==========================================
# 4. GRAPH API ACCOUNT DISCOVERY & GREEN/FLAGGED FILTER
# ==========================================
def allowed_ig(username, page_name):
    u = (username or "").strip().lower()
    p = (page_name or "").strip().lower()
    if u in GREEN:
        return True
    if u in FLAGGED:
        return False
    return not any(re.search(rf"(^|[^a-z0-9]){re.escape(b)}([^0-9]|$)", p) for b in FLAGGED)

def get_connected_instagram_accounts(tokens):
    accounts, seen_ig_ids = [], set()
    for token in tokens:
        try:
            url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/accounts"
            params = {
                "fields": "id,name,access_token,instagram_business_account{id,username}",
                "limit": 100,
                "access_token": token
            }
            response = requests.get(url, params=params, timeout=(10, 20)).json()
            if "error" in response:
                log(f"[TOKEN WARN] {response['error'].get('message')}")
                continue
            for page in response.get("data", []):
                ig_biz = page.get("instagram_business_account")
                if not ig_biz or "id" not in ig_biz:
                    continue
                ig_id = str(ig_biz["id"])
                ig_user = ig_biz.get("username", "")
                page_name = page.get("name", "ARC")
                if ig_id not in seen_ig_ids and allowed_ig(ig_user, page_name):
                    seen_ig_ids.add(ig_id)
                    accounts.append({
                        "page_id": page.get("id"),
                        "page_name": page_name,
                        "page_token": page.get("access_token", token),
                        "ig_user_id": ig_id,
                        "ig_username": ig_user,
                        "token": token
                    })
        except Exception as e:
            log(f"[TOKEN ERR] {e}")
    log(f"[FLEET] {len(accounts)} active accounts: {[a['ig_username'] or a['page_name'] for a in accounts]}")
    return accounts

# ==========================================
# 5. ARC FFMPEG PIPELINE (4K/HD, 1ST INTACT, SHUFFLED CUTS, 2x0.5s LOGO, AUDIO BED + VO)
# ==========================================
def probe_dur(p):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", p],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15
        )
        return float(r.stdout.decode().strip())
    except Exception:
        return 0.0

def probe_aud(p):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", p],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15
        )
        return bool(r.stdout.decode().strip())
    except Exception:
        return False

def get_font():
    if os.path.exists(FONT) and os.path.getsize(FONT) > 15000:
        return FONT
    urls = [
        "https://github.com/google/fonts/raw/main/ofl/cinzel/static/Cinzel-Bold.ttf",
        "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf",
    ]
    for u in urls:
        try:
            r = requests.get(u, timeout=15)
            if r.status_code == 200 and len(r.content) > 15000:
                with open(FONT, "wb") as f:
                    f.write(r.content)
                return FONT
        except Exception:
            pass
    return "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

def detect_shots(src, thresh=0.32):
    """Detects scene cuts via FFmpeg and returns sliceable (filepath, start, duration) tuples."""
    tot = probe_dur(src)
    if tot <= 1.2:
        return []
    cuts = [0.0]
    try:
        r = subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-i", src,
             "-vf", f"select='gt(scene,{thresh})',showinfo", "-f", "null", "-"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45
        )
        for m in re.finditer(r"pts_time:([0-9]+\.?[0-9]*)", r.stderr.decode(errors="ignore")):
            t = float(m.group(1))
            if 0.5 <= t <= tot - 0.5 and (t - cuts[-1]) >= 0.55:
                cuts.append(t)
    except Exception:
        pass
    cuts.append(tot)

    shots = []
    for i in range(len(cuts) - 1):
        s, e = round(cuts[i] + 0.06, 2), round(cuts[i + 1] - 0.06, 2)
        d = round(e - s, 2)
        if d >= 0.7:
            if d > 2.3 and i > 0:
                seg = round(random.uniform(1.1, 1.9), 2)
                shots.append((src, round(s + random.uniform(0.0, d - seg), 2), seg))
            else:
                shots.append((src, s, min(d, 2.8) if i == 0 else d))

    if len(shots) < 2:
        shots, pos = [], 0.05
        while pos + 0.95 < tot - 0.1:
            seg = round(min(random.uniform(1.1, 1.9), tot - 0.1 - pos), 2)
            if seg >= 0.8:
                shots.append((src, round(pos, 2), seg))
            pos += seg
    return shots

def build_seq(primary_fp, clips, bank, target_main):
    """Keeps 1st clip intact, slices & shuffles remaining clips, inserts two 0.5s ARC logo flashes."""
    f_shots = bank.get(primary_fp) or []
    first_st, first_d = (
        (f_shots[0][1], f_shots[0][2])
        if f_shots
        else (0.0, min(2.2, max(1.2, probe_dur(primary_fp) * 0.3)))
    )

    other_fps = [c[0] for c in clips if c[0] != primary_fp]
    mix_fps = [primary_fp] + random.sample(other_fps, min(len(other_fps), 2))
    rem = [
        s for p in mix_fps for s in (bank.get(p) or [])
        if not (p == primary_fp and s[1] < first_st + first_d)
    ]
    if not rem:
        rem = [(p, 0.1, 1.3) for p in mix_fps]
    random.shuffle(rem)

    budget = max(2.5, round(target_main - first_d - 1.0, 2))
    cuts, acc = [], 0.0
    while acc < budget and len(cuts) < 8:
        for s in rem:
            if acc >= budget or len(cuts) >= 8:
                break
            d = s[2] if (budget - acc) >= s[2] else max(0.75, round(budget - acc, 2))
            cuts.append((s[0], s[1], round(d, 2)))
            acc = round(acc + d, 2)
        random.shuffle(rem)

    g1 = max(1, len(cuts) // 3) if len(cuts) >= 3 else 1
    g2 = max(g1 + 1, (2 * len(cuts)) // 3) if len(cuts) >= 3 else 2

    items = [("clip", primary_fp, first_st, first_d)]
    items += [("clip", *c) for c in cuts[:g1]] + [("logo", None, 0.0, 0.5)]
    items += [("clip", *c) for c in cuts[g1:g2]] + [("logo", None, 0.0, 0.5)]
    items += [("clip", *c) for c in cuts[g2:]]
    return items, primary_fp, first_st

def render(primary_fp, out_mp4, clips=None, bank=None, font=None, tag="arc"):
    """Full FFmpeg pipeline: 1st clip intact, shuffled cuts, 2x 0.5s logo flashes, 4K/HD grade, audio bed + AI VO CTA end card."""
    if clips is None:
        clips = [(primary_fp, "single", False)]
    if bank is None:
        bank = {c[0]: detect_shots(c[0]) for c in clips}
    else:
        for c in clips:
            if c[0] not in bank:
                bank[c[0]] = detect_shots(c[0])
    if not font:
        font = get_font()

    cta = random.choice(ONE_LINERS)
    vo = f"vo_{tag}_{random.randint(100, 999)}.mp3"
    voices = [
        "en-US-AndrewMultilingualNeural",
        "en-US-BrianMultilingualNeural",
        "en-US-ChristopherNeural",
    ]
    random.shuffle(voices)
    vo_ok = False
    for voice in voices:
        try:
            subprocess.run(
                ["edge-tts", "--voice", voice, "--rate=-2%", "--pitch=-4Hz", "--text", cta, "--write-media", vo],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=True
            )
            if os.path.exists(vo) and os.path.getsize(vo) > 1000:
                vo_ok = True
                break
        except Exception:
            continue
    if not vo_ok:
        raise Exception("edge-tts voiceover generation failed across all voices")

    end_d = round(max(2.0, min(3.8, probe_dur(vo) + 0.35)), 2)
    target_main = round(max(7.5, random.uniform(10.5, 12.8) - end_d), 2)
    items, first_src, first_st = build_seq(primary_fp, clips, bank, target_main)
    main_d = round(sum(it[3] for it in items), 2)
    tot_d = round(main_d + end_d, 2)

    logo_ok = os.path.exists(LOGO) and os.path.getsize(LOGO) > 500
    bed_ok = os.path.exists(EXTRA_BED) and os.path.getsize(EXTRA_BED) > 5000

    (
        ow, oh, pw, ph, mpx, bpx, fpx, tpx, cpx, epx,
        lxy, ty, edy, cy, eay, ecy, crf, pre, lvl, dx, dy
    ) = (
        (
            2160, 3840, 2224, 3954, 78, 660, 520, 54, 86, 210,
            "54:90", "98", "-230", "(h/2)+250", "(h/2)-250", "(h/2)+110",
            "17", "veryfast", "5.1", 28, 48
        )
        if ENABLE_4K else
        (
            1080, 1920, 1112, 1977, 39, 330, 260, 27, 44, 110,
            "27:45", "49", "-115", "(h/2)+125", "(h/2)-125", "(h/2)+55",
            "18", "faster", "4.2", 14, 24
        )
    )

    con = round(random.uniform(1.03, 1.07), 3)
    sat = round(random.uniform(1.03, 1.08), 3)
    gam = round(random.uniform(0.96, 1.02), 3)

    usrcs = list(dict.fromkeys([first_src] + [it[1] for it in items if it[0] == "clip"]))
    s2i = {s: i for i, s in enumerate(usrcs)}

    inputs = [x for s in usrcs for x in ("-stream_loop", "-1", "-i", s)] + ["-i", vo]
    vo_i, nxt = len(usrcs), len(usrcs) + 1
    if bed_ok:
        inputs += ["-stream_loop", "-1", "-i", EXTRA_BED]
        bed_i, nxt = nxt, nxt + 1
    if logo_ok:
        inputs += ["-i", LOGO]
        logo_i = nxt

    counts, used, splits, segs, lcnt = {}, {}, [], [], 0
    for it in items:
        if it[0] == "clip":
            counts[s2i[it[1]]] = counts.get(s2i[it[1]], 0) + 1

    for i, c in counts.items():
        if c > 1:
            splits.append(f"[{i}:v]split={c}" + "".join(f"[s{i}_{j}]" for j in range(c)) + ";")

    n_flashes = sum(1 for it in items if it[0] == "logo")
    if logo_ok:
        splits.append(
            f"[{logo_i}:v]split={2 + n_flashes}[l1][l2]"
            + "".join(f"[lf{j}]" for j in range(n_flashes))
            + ";"
        )

    for k, (kind, src, st, dur) in enumerate(items):
        if kind == "logo" and logo_ok:
            segs.append(
                f"color=c=0x080808:s={ow}x{oh}:d={dur}:r=30[lb{k}];"
                f"[lf{lcnt}]scale={fpx}:{fpx}:force_original_aspect_ratio=decrease:flags=lanczos,format=rgba[lg{k}];"
                f"[lb{k}][lg{k}]overlay=(W-w)/2:(H-h)/2:eof_action=repeat,fps=30,setsar=1,format=yuv420p[v{k}];"
            )
            lcnt += 1
        elif kind == "logo":
            segs.append(
                f"color=c=0x080808:s={ow}x{oh}:d={dur}:r=30,"
                f"drawtext=fontfile='{font}':text='A R C':fontcolor=0xFFD700:fontsize={epx}:"
                f"x=(w-text_w)/2:y=(h-text_h)/2,fps=30,setsar=1,format=yuv420p[v{k}];"
            )
        else:
            idx = s2i[src]
            u = used.get(idx, 0)
            used[idx] = u + 1
            pin = f"[s{idx}_{u}]" if counts[idx] > 1 else f"[{idx}:v]"

            if k == 0:
                crop = f"crop={ow}:{oh}:{(pw - ow) // 2}:{(ph - oh) // 2}"
            else:
                x0 = random.randint(0, max(1, pw - ow - dx))
                y0 = random.randint(0, max(1, ph - oh - dy))
                vx = random.choice([-1, 1]) * round(random.uniform(0.8, 2.0), 2)
                vy = random.choice([-1, 1]) * round(random.uniform(1.0, 3.0), 2)
                crop = f"crop={ow}:{oh}:x='clip({x0}+{vx}*t,0,iw-{ow})':y='clip({y0}+{vy}*t,0,ih-{oh})':exact=1"

            segs.append(
                f"{pin}trim=start={st}:duration={dur},setpts=PTS-STARTPTS,"
                f"scale={pw}:{ph}:force_original_aspect_ratio=increase:flags=lanczos,"
                f"{crop},unsharp=5:5:0.35:3:3:0.0,"
                f"eq=contrast={con}:saturation={sat}:gamma={gam}:brightness=0.004,"
                f"noise=alls=2:allf=t+u,fps=30,setsar=1,format=yuv420p[v{k}];"
            )

    cat = "".join(f"[v{k}]" for k in range(len(items)))
    csafe = cta.replace("'", "").replace(":", " -")
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(time.time()) - random.randint(600, 86400)))

    if logo_ok:
        vf = (
            "".join(splits + segs)
            + f"{cat}concat=n={len(items)}:v=1:a=0[mb];"
            + f"[l1]scale={mpx}:{mpx}:force_original_aspect_ratio=decrease:flags=lanczos,format=rgba,colorchannelmixer=aa=0.45[ml];"
            + f"[l2]scale={bpx}:{bpx}:force_original_aspect_ratio=decrease:flags=lanczos,format=rgba[bl];"
            + f"[mb][ml]overlay={lxy}:eof_action=repeat[mlo];"
            + f"[mlo]drawtext=fontfile='{font}':text='ARC':fontcolor=white@0.22:fontsize={tpx}:x=(w-text_w)/2:y={ty},format=yuv420p[mv];"
            + f"color=c=0x080808:s={ow}x{oh}:d={end_d}:r=30[eb];"
            + f"[eb][bl]overlay=(W-w)/2:(H-h)/2{edy}:eof_action=repeat[elo];"
            + f"[elo]drawtext=fontfile='{font}':text='{csafe}':fontcolor=0xFFD700:fontsize={cpx}:"
            + f"x=(w-text_w)/2:y={cy}:shadowcolor=black:shadowx=2:shadowy=2,fps=30,setsar=1,format=yuv420p[ev];"
            + "[mv][ev]concat=n=2:v=1:a=0[vout];"
        )
    else:
        vf = (
            "".join(splits + segs)
            + f"{cat}concat=n={len(items)}:v=1:a=0,"
            + f"drawtext=fontfile='{font}':text='ARC':fontcolor=white@0.22:fontsize={tpx}:x=(w-text_w)/2:y={ty},format=yuv420p[mv];"
            + f"color=c=0x080808:s={ow}x{oh}:d={end_d}:r=30,"
            + f"drawtext=fontfile='{font}':text='A R C':fontcolor=0xFFD700:fontsize={epx}:x=(w-text_w)/2:y={eay},"
            + f"drawtext=fontfile='{font}':text='{csafe}':fontcolor=white@0.95:fontsize={cpx}:x=(w-text_w)/2:y={ecy},"
            + "fps=30,setsar=1,format=yuv420p[ev];"
            + "[mv][ev]concat=n=2:v=1:a=0[vout];"
        )

    # Continuous original audio (95% main, ducked to 22% during AI end-card VO)
    aud_i = next((i for i, s in enumerate(usrcs) if probe_aud(s)), -1)
    ast = first_st if aud_i == 0 else 0.0
    if aud_i >= 0:
        oa = (
            f"[{aud_i}:a]atrim=start={ast}:duration={tot_d},asetpts=PTS-STARTPTS,"
            f"aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"volume='if(lt(t,{main_d}),0.95,0.22)':eval=frame,"
            f"apad=whole_dur={tot_d},atrim=0:{tot_d}[oa];"
        )
    else:
        oa = (
            f"aevalsrc=0.04*sin(2*PI*55*t)+0.02*sin(2*PI*82.4*t):s=48000:d={tot_d},"
            f"aformat=sample_fmts=fltp:channel_layouts=stereo[oa];"
        )

    # Low-volume extra background track or synthesized harmonic bed for audio fingerprint shift
    if bed_ok:
        ea = (
            f"[{bed_i}:a]atrim=start=0:duration={tot_d},asetpts=PTS-STARTPTS,"
            f"aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"volume={round(random.uniform(0.025, 0.045), 4)},"
            f"apad=whole_dur={tot_d},atrim=0:{tot_d}[ea];"
        )
    else:
        f1 = round(random.uniform(44.0, 66.0), 1)
        f2 = round(f1 * 1.5, 1)
        f3 = round(random.uniform(118.0, 162.0), 1)
        sv1 = round(random.uniform(0.010, 0.013), 4)
        sv2 = round(random.uniform(0.006, 0.009), 4)
        sv3 = round(random.uniform(0.004, 0.006), 4)
        ea = (
            f"aevalsrc={sv1}*sin(2*PI*{f1}*t)+{sv2}*sin(2*PI*{f2}*t)+{sv3}*sin(2*PI*{f3}*t):"
            f"s=48000:d={tot_d},aformat=sample_fmts=fltp:channel_layouts=stereo[ea];"
        )

    # Mix original audio + low-volume bed + end-card AI voiceover
    af = (
        oa
        + ea
        + f"[{vo_i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
        + f"volume=1.65,adelay={int(main_d * 1000)}|{int(main_d * 1000)},"
        + f"apad=whole_dur={tot_d},atrim=0:{tot_d}[va];"
        + "[oa][ea][va]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,"
        + f"alimiter=limit=0.95,afade=t=out:st={round(tot_d - 0.25, 2)}:d=0.25[aout]"
    )

    cmd = (
        ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y"]
        + inputs
        + [
            "-filter_complex", vf + af,
            "-map", "[vout]", "-map", "[aout]",
            "-t", str(tot_d),
            "-c:v", "libx264", "-profile:v", "high", "-level:v", lvl,
            "-crf", crf, "-maxrate", "22M", "-bufsize", "44M",
            "-preset", pre, "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-map_metadata", "-1", "-metadata", f"creation_time={ts}",
            out_mp4,
        ]
    )

    try:
        res = subprocess.run(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300
        )
        if res.returncode != 0 or not os.path.exists(out_mp4):
            raise Exception(res.stderr.decode(errors="ignore"))
        log(f"[RENDER] {ow}x{oh} | {tot_d}s | 1st intact + {len(items) - 3} shuffled + 2x0.5s ARC | '{cta}'")
        return out_mp4
    finally:
        if os.path.exists(vo):
            try:
                os.remove(vo)
            except Exception:
                pass

# ==========================================
# 6. 5-HOST RELAY UPLOAD + IG REELS & YT SHORTS PUBLISHING
# ==========================================
def upload_for_meta_download(file_path):
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", "Accept-Language": "en-US,en;q=0.9"}
    try:
        with open(file_path, "rb") as f:
            res = requests.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload"}, files={"fileToUpload": f}, headers=headers, timeout=(15, 120))
        if res.status_code == 200 and res.text.strip().startswith("https://"):
            return res.text.strip()
    except Exception:
        pass
    try:
        with open(file_path, "rb") as f:
            res = requests.post("https://litterbox.catbox.moe/resources/internals/api.php", data={"reqtype": "fileupload", "time": "1h"}, files={"fileToUpload": f}, headers=headers, timeout=(15, 120))
        if res.status_code == 200 and res.text.strip().startswith("https://"):
            return res.text.strip()
    except Exception:
        pass
    try:
        with open(file_path, "rb") as f:
            res = requests.post("https://uguu.se/upload", files={"files[]": f}, headers=headers, timeout=(15, 120)).json()
        if res.get("success") and res.get("files"):
            return res["files"][0]["url"]
    except Exception:
        pass
    try:
        with open(file_path, "rb") as f:
            response = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, headers=headers, timeout=(15, 120)).json()
        if "data" in response and "url" in response["data"]:
            return response["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")
    except Exception:
        pass
    with open(file_path, "rb") as f:
        res = requests.post("https://0x0.st", files={"file": f}, headers=headers, timeout=(15, 120))
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
    time.sleep(20)
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
    log(f"[IG OK] Media ID: {publish_res['id']}")

def publish_short_to_youtube(file_path, title, description, refresh_token):
    tok_res = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": YT_ID,
            "client_secret": YT_SEC,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=20,
    ).json()
    access_token = tok_res.get("access_token")
    if not access_token:
        raise Exception(f"YT OAuth failed: {tok_res}")
    init = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        data=json.dumps({
            "snippet": {"title": title[:95], "description": description, "categoryId": "22"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        }),
        timeout=30,
    )
    upload_url = init.headers.get("Location")
    if not upload_url:
        raise Exception(f"YT init failed: {init.text}")
    with open(file_path, "rb") as f:
        up = requests.put(upload_url, headers={"Content-Type": "video/mp4"}, data=f, timeout=180)
    if up.status_code not in (200, 201):
        raise Exception(f"YT upload failed: {up.text}")
    log(f"[YT OK] Video ID: {up.json().get('id')}")

# ==========================================
# 7. MAIN EXECUTION (SUB-2-MIN PACING, RANDOM ACCOUNTS & UNIQUE REELS)
# ==========================================
def main():
    wave_start_ts = time.time()
    log("=== ARC AUTONOMOUS ENGINE STARTED ===")
    ensure_edge_tts_installed()

    if not META_TOKENS and not (YT_ID and YT_SEC and YT_TOKS):
        log("[ERROR] Neither META_TOKEN nor YT credentials found in environment.")
        return

    font_path = get_font()
    posted_history = load_set_file(HISTORY_FILE)
    dead_shortcodes = load_set_file(DEAD_SHORTCODES_FILE)

    wave_accounts = get_connected_instagram_accounts(META_TOKENS) if META_TOKENS else []
    random.shuffle(wave_accounts)

    master_catalog = build_master_reel_catalog_once(dead_shortcodes)
    if not master_catalog:
        log("[ERROR] Zero Reels discovered in catalog. Exiting cleanly.")
        return

    downloaded_cache = {}
    shot_bank = {}
    used_in_wave = set()
    ig_ok, yt_ok = 0, 0

    try:
        total_ig = len(wave_accounts)
        for index, acc in enumerate(wave_accounts):
            ig_uid = str(acc["ig_user_id"])
            label = acc["ig_username"] or acc["page_name"]
            log(f"\n--- IG [{index + 1}/{total_ig}]: {label} ({ig_uid}) ---")
            out_mp4 = f"arc_ig_{index}.mp4"
            posted_this_node = False
            try:
                chosen_id, source_video = pick_random_reel_for_account(
                    ig_uid,
                    master_catalog,
                    posted_history,
                    downloaded_cache,
                    dead_shortcodes,
                    used_in_wave,
                )
                if not source_video or not os.path.exists(source_video):
                    log(f"[OVERFLOW] No unposted Reel available for {label}, moving to next account...")
                    continue

                pool_clips = [(p, cid, False) for cid, p in downloaded_cache.items() if os.path.exists(p)]
                render(source_video, out_mp4, clips=pool_clips, bank=shot_bank, font=font_path, tag=f"ig{index}")
                public_url = upload_for_meta_download(out_mp4)
                publish_reel_to_instagram(ig_uid, public_url, build_caption(index), acc["token"])
                append_to_set_file(HISTORY_FILE, f"{ig_uid}:{chosen_id}", posted_history)
                ig_ok += 1
                posted_this_node = True
            except Exception as e:
                log(f"[IG SKIP] {label}: {e}")
            finally:
                if os.path.exists(out_mp4):
                    try:
                        os.remove(out_mp4)
                    except Exception:
                        pass

            if posted_this_node and index < total_ig - 1:
                wait_s = random.randint(45, 115)
                log(f"[WAIT] {wait_s}s before next account (within 2 mins)...")
                time.sleep(wait_s)

        if YT_ID and YT_SEC and YT_TOKS:
            total_yt = len(YT_TOKS)
            for index, rtok in enumerate(YT_TOKS):
                yt_key = f"yt_{index}"
                log(f"\n--- YT [{index + 1}/{total_yt}] ---")
                out_mp4 = f"arc_yt_{index}.mp4"
                posted_this_node = False
                try:
                    chosen_id, source_video = pick_random_reel_for_account(
                        yt_key,
                        master_catalog,
                        posted_history,
                        downloaded_cache,
                        dead_shortcodes,
                        used_in_wave,
                    )
                    if not source_video or not os.path.exists(source_video):
                        log(f"[OVERFLOW] No unposted Reel available for YT [{index + 1}], moving on...")
                        continue

                    pool_clips = [(p, cid, False) for cid, p in downloaded_cache.items() if os.path.exists(p)]
                    render(source_video, out_mp4, clips=pool_clips, bank=shot_bank, font=font_path, tag=f"yt{index}")
                    publish_short_to_youtube(out_mp4, random.choice(TITLES), build_caption(index), rtok)
                    append_to_set_file(HISTORY_FILE, f"{yt_key}:{chosen_id}", posted_history)
                    yt_ok += 1
                    posted_this_node = True
                except Exception as e:
                    log(f"[YT SKIP] channel {index + 1}: {e}")
                finally:
                    if os.path.exists(out_mp4):
                        try:
                            os.remove(out_mp4)
                        except Exception:
                            pass

                if posted_this_node and index < total_yt - 1:
                    wait_s = random.randint(25, 60)
                    log(f"[WAIT] {wait_s}s before next YouTube channel...")
                    time.sleep(wait_s)
    finally:
        for cached_file in downloaded_cache.values():
            if cached_file and os.path.exists(cached_file):
                try:
                    os.remove(cached_file)
                except Exception:
                    pass

    log(f"\n=== WAVE DONE: {ig_ok}/{len(wave_accounts)} IG | {yt_ok}/{len(YT_TOKS)} YT in {int(time.time() - wave_start_ts)}s ===")

if __name__ == "__main__":
    try:
        main()
    except Exception as fatal_err:
        log(f"[GLOBAL OVERFLOW] Exception caught: {fatal_err}")
        sys.exit(0)
