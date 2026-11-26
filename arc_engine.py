import os
import re
import sys
import json
import time
import random
import requests
import subprocess
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
        subprocess.run(
            ["edge-tts", "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=True,
        )
    except Exception:
        log("[INIT] Installing edge-tts...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "edge-tts"],
            stdin=subprocess.DEVNULL,
            timeout=60,
        )


# ==========================================
# 1. TOKENS, ACCOUNTS & SOURCES
# ==========================================
META_TOKENS = [
    t.strip()
    for t in [
        os.getenv("META_TOKEN_1"),
        os.getenv("META_TOKEN_2"),
        os.getenv("META_TOKEN_3"),
    ]
    if t and t.strip()
]

YT_CLIENT_ID = (os.getenv("YT_CLIENT_ID") or "").strip()
YT_CLIENT_SECRET = (os.getenv("YT_CLIENT_SECRET") or "").strip()
YT_REFRESH_TOKENS = [
    t.strip()
    for t in re.split(r"[\n,]+", os.getenv("YT_REFRESH_TOKENS") or "")
    if t.strip()
]

GRAPH_API_VERSION = "v20.0"

GREEN_HANDLES = {
    "arcbloodline2",
    "arcbloodline3",
    "arcbloodline4",
    "arcbloodline9",
    "arcbloodline19",
    "arcbloodline20",
    "arcbloodline23",
    "arcbloodline25",
    "arcbloodline26",
}
FLAGGED_HANDLES = {f"arcbloodline{i}" for i in range(1, 27)} - GREEN_HANDLES

ASSETS_DIR = "assets"
LOCAL_REELS_DIR = "reels"
ARC_LOGO_PATH = "arc_logo.png"
STYLISH_FONT_PATH = "Cinzel-Bold.ttf"
GOLD_HEX = "0xFFD700"

# True = 2160x3840 4K Lanczos + unsharp | False = 1080x1920 fast HD
ENABLE_4K_UPSCALE = True

# Add more YouTube /shorts channel URLs here anytime
SOURCE_YT_CHANNELS = [
    "https://www.youtube.com/@SparkleOfLife-d2y/shorts",
    "https://www.youtube.com/@Luxurylife4628/shorts",
]


# ==========================================
# 2. IRRESISTIBLE 3-5 WORD CTAS & CAPTIONS
# ==========================================
ARC_ONE_LINER_CTAS = [
    "Stop watching. Enter ARC.",
    "Your seat inside ARC waits.",
    "Build in silence. Enter ARC.",
    "Claim your place inside ARC.",
    "Doors to ARC are open.",
    "The blueprint lives inside ARC.",
    "Enter ARC. Link in bio.",
    "Step inside ARC today.",
]

CAPTION_BODIES = [
    "Most men spend years watching while a few quietly build leverage.\n\nEverything you need to leave the average lane is mapped out inside ARC.",
    "Nobody hands you freedom. Build an independent system now or trade your hours forever.\n\nARC is built for men who execute in silence.",
    "Your circle sets your ceiling. Sit with spectators and stay stuck. Step inside a room of operators building real online cashflow.",
    "A fixed paycheck caps your life before you even begin. Ownership buys your time back.\n\nSee what is waiting inside ARC.",
    "Discipline creates leverage. Leverage creates freedom.\n\nDoors inside ARC do not stay open forever.",
]

CAPTION_CTAS = [
    "Link in bio to enter ARC.",
    "Comment \"ARC\" or tap the bio link.",
    "Step inside ARC through the link in bio.",
    "Bio link is live. Enter ARC.",
]

NICHE_TAGS = [
    "#wealthmindset", "#oldmoney", "#digitalbusiness", "#financialfreedom",
    "#entrepreneurship", "#onlineincome", "#successmindset", "#businessowner",
    "#selfimprovement", "#wealthbuilding", "#darkluxury", "#mindset",
]

YT_TITLES = [
    "Build in Silence. Enter ARC. #Shorts",
    "Stop Watching. Start Building. #Shorts",
    "Why Silent Operators Always Win #Shorts",
    "Ownership Beats a Paycheck #Shorts",
    "The Blueprint Nobody Talks About #Shorts",
]


def generate_clean_caption(idx):
    body = random.choice(CAPTION_BODIES)
    cta = CAPTION_CTAS[idx % len(CAPTION_CTAS)]
    tags = " ".join(random.sample(NICHE_TAGS, k=random.choice([2, 3, 4])))
    return f"{body}\n\n{cta}\n\n{tags}"


# ==========================================
# 3. INSTAGRAM ACCOUNT DISCOVERY
# ==========================================
def is_allowed_ig_account(username, page_name):
    u = (username or "").strip().lower()
    p = (page_name or "").strip().lower()
    if u in GREEN_HANDLES:
        return True
    if u in FLAGGED_HANDLES:
        return False
    for bad in FLAGGED_HANDLES:
        if re.search(rf"(^|[^a-z0-9]){re.escape(bad)}([^0-9]|$)", p):
            return False
    return True


def get_all_healthy_ig_accounts():
    all_accs = []
    seen = set()
    for token in META_TOKENS:
        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/accounts"
        params = {
            "fields": "id,name,instagram_business_account{id,username}",
            "limit": 100,
            "access_token": token,
        }
        res = requests.get(url, params=params, timeout=(10, 20)).json()
        if "error" in res:
            log(f"[TOKEN WARN] {res['error'].get('message')}")
            continue
        for page in res.get("data", []):
            ig_biz = page.get("instagram_business_account")
            if ig_biz and "id" in ig_biz and ig_biz["id"] not in seen:
                uname = ig_biz.get("username", "")
                pname = page.get("name", "ARC_Node")
                if is_allowed_ig_account(uname, pname):
                    seen.add(ig_biz["id"])
                    all_accs.append({
                        "page_name": pname,
                        "ig_user_id": ig_biz["id"],
                        "ig_username": uname,
                        "token": token,
                    })
                else:
                    log(f"[BLOCKED FLAGGED] Skipping {uname or pname}")
    names = [a["ig_username"] or a["page_name"] for a in all_accs]
    log(f"[IG FLEET] Active clean accounts ({len(all_accs)}): {names}")
    return all_accs


# ==========================================
# 4. RANDOM CLIP PICKER FROM SOURCE CHANNELS
# ==========================================
def get_media_duration(path):
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path,
        ]
        res = subprocess.run(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=15,
        )
        return float(res.stdout.decode("utf-8").strip())
    except Exception:
        return 0.0


def has_audio_stream(path):
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "a",
            "-show_entries", "stream=codec_type", "-of", "csv=p=0", path,
        ]
        res = subprocess.run(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=15,
        )
        return bool(res.stdout.decode("utf-8").strip())
    except Exception:
        return False


def fetch_random_urls_from_channels(channel_urls, pool_size=30):
    candidates = []
    channels = list(channel_urls)
    random.shuffle(channels)

    for ch_url in channels:
        ydl_opts = {
            "extract_flat": True,
            "playlistend": 60,
            "quiet": True,
            "no_warnings": True,
            "logger": SilentYTDLLogger(),
            "socket_timeout": 20,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(ch_url, download=False)
            for e in (info.get("entries") or []):
                if not e:
                    continue
                vid_url = e.get("url")
                if not vid_url and e.get("id"):
                    vid_url = f"https://www.youtube.com/shorts/{e['id']}"
                dur = e.get("duration") or 20
                if vid_url and 8 <= dur <= 90:
                    if not vid_url.startswith("http"):
                        vid_url = f"https://www.youtube.com/shorts/{vid_url}"
                    candidates.append(vid_url)
        except Exception as err:
            log(f"[SOURCE WARN] Could not scan {ch_url}: {err}")

    random.shuffle(candidates)
    return candidates[:pool_size]


def collect_source_clips(target_count=9):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    clips = []

    if os.path.isdir(LOCAL_REELS_DIR):
        for fname in os.listdir(LOCAL_REELS_DIR):
            if fname.lower().endswith(".mp4"):
                fpath = os.path.join(LOCAL_REELS_DIR, fname)
                if get_media_duration(fpath) >= 8.0:
                    clips.append((fpath, False))
    random.shuffle(clips)

    candidate_urls = fetch_random_urls_from_channels(SOURCE_YT_CHANNELS, pool_size=30)
    for idx, vid_url in enumerate(candidate_urls):
        if len(clips) >= target_count:
            break
        out_path = os.path.join(ASSETS_DIR, f"src_yt_{idx}_{random.randint(100, 999)}.mp4")
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "outtmpl": out_path,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "logger": SilentYTDLLogger(),
            "socket_timeout": 25,
            "match_filter": yt_dlp.utils.match_filter_func("duration >= 8 & duration <= 90"),
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(vid_url, download=True)
        except Exception:
            pass

        if os.path.exists(out_path) and os.path.getsize(out_path) > 200000 and get_media_duration(out_path) >= 8.0:
            clips.append((out_path, True))
            log(f"[RANDOM PICK] Downloaded {vid_url} (audio={has_audio_stream(out_path)})")
        elif os.path.exists(out_path):
            try:
                os.remove(out_path)
            except Exception:
                pass

    random.shuffle(clips)
    return clips


def ensure_stylish_font():
    if os.path.exists(STYLISH_FONT_PATH) and os.path.getsize(STYLISH_FONT_PATH) > 15000:
        return STYLISH_FONT_PATH
    font_urls = [
        "https://github.com/google/fonts/raw/main/ofl/cinzel/static/Cinzel-Bold.ttf",
        "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf",
    ]
    for url in font_urls:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200 and len(r.content) > 15000:
                with open(STYLISH_FONT_PATH, "wb") as f:
                    f.write(r.content)
                return STYLISH_FONT_PATH
        except Exception:
            continue
    return "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


def generate_cta_voiceover(cta_text, out_mp3):
    voice = random.choice([
        "en-US-AndrewMultilingualNeural",
        "en-US-BrianMultilingualNeural",
        "en-US-ChristopherNeural",
    ])
    cmd = [
        "edge-tts",
        "--voice", voice,
        "--rate=-2%",
        "--pitch=-4Hz",
        "--text", cta_text,
        "--write-media", out_mp3,
    ]
    subprocess.run(
        cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=30, check=True,
    )
    return get_media_duration(out_mp3)


# ==========================================
# 5. FFMPEG RENDERER (4K, NO FLIP, 10-13s, LOGO + CTA + 2.5% BED)
# ==========================================
def render_arc_reel(src_clip, output_path, font_path, tag_id):
    cta_text = random.choice(ARC_ONE_LINER_CTAS)
    vo_path = f"vo_{tag_id}_{random.randint(100, 999)}.mp3"
    vo_dur = generate_cta_voiceover(cta_text, vo_path)

    end_dur = round(max(2.0, min(3.8, vo_dur + 0.35)), 2)
    target_total = round(random.uniform(10.5, 12.8), 2)
    main_dur = round(max(7.5, target_total - end_dur), 2)
    total_dur = round(main_dur + end_dur, 2)

    src_dur = get_media_duration(src_clip)
    st = round(random.uniform(0.15, 0.45), 2) if src_dur > total_dur + 1.0 else 0.0

    clip_has_audio = has_audio_stream(src_clip)
    logo_exists = os.path.exists(ARC_LOGO_PATH) and os.path.getsize(ARC_LOGO_PATH) > 500

    if ENABLE_4K_UPSCALE:
        out_w, out_h = 2160, 3840
        pre_w, pre_h = 2204, 3917
        mini_px, big_px = 78, 660
        top_px, cta_px, end_arc_px = 54, 86, 210
        logo_xy, top_y = "54:90", "98"
        end_logo_dy, cta_y = "-230", "(h/2)+250"
        end_arc_y, end_cta_y = "(h/2)-250", "(h/2)+110"
        crf_val, preset_val = "17", "veryfast"
        v_level = "5.1"
    else:
        out_w, out_h = 1080, 1920
        pre_w, pre_h = 1102, 1958
        mini_px, big_px = 39, 330
        top_px, cta_px, end_arc_px = 27, 44, 110
        logo_xy, top_y = "27:45", "49"
        end_logo_dy, cta_y = "-115", "(h/2)+125"
        end_arc_y, end_cta_y = "(h/2)-125", "(h/2)+55"
        crf_val, preset_val = "18", "faster"
        v_level = "4.2"

    # Sub-audible custom synth bed (~2.5% total amplitude)
    f1 = round(random.uniform(44.0, 66.0), 1)
    f2 = round(f1 * 1.5, 1)
    f3 = round(random.uniform(118.0, 162.0), 1)
    sv1 = round(random.uniform(0.010, 0.013), 4)
    sv2 = round(random.uniform(0.006, 0.009), 4)
    sv3 = round(random.uniform(0.004, 0.006), 4)

    cta_safe = cta_text.replace("'", "").replace(":", " -")
    delay_ms = int(main_dur * 1000)
    ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(time.time()) - random.randint(600, 86400)))

    if logo_exists:
        v_filter = (
            f"[2:v]split=2[l1][l2];"
            f"[l1]scale={mini_px}:{mini_px}:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"format=rgba,colorchannelmixer=aa=0.45[mini_logo];"
            f"[l2]scale={big_px}:{big_px}:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"format=rgba[big_logo];"
            f"[0:v]trim=start={st}:duration={main_dur},setpts=PTS-STARTPTS,"
            f"scale={pre_w}:{pre_h}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={out_w}:{out_h},unsharp=5:5:0.45:3:3:0.0,"
            f"fps=30,setsar=1,eq=contrast=1.02:saturation=1.03:brightness=0.005[m_base];"
            f"[m_base][mini_logo]overlay={logo_xy}[m_logo];"
            f"[m_logo]drawtext=fontfile='{font_path}':text='ARC':fontcolor=white@0.22:fontsize={top_px}:"
            f"x=(w-text_w)/2:y={top_y},format=yuv420p[main_v];"
            f"color=c=0x080808:s={out_w}x{out_h}:d={end_dur}:r=30[e_bg];"
            f"[e_bg][big_logo]overlay=(W-w)/2:(H-h)/2{end_logo_dy}[e_logo];"
            f"[e_logo]drawtext=fontfile='{font_path}':text='{cta_safe}':fontcolor={GOLD_HEX}:fontsize={cta_px}:"
            f"x=(w-text_w)/2:y={cta_y}:shadowcolor=black:shadowx=2:shadowy=2,"
            f"fps=30,setsar=1,format=yuv420p[end_v];"
            f"[main_v][end_v]concat=n=2:v=1:a=0[vout];"
        )
    else:
        log("[WARN] arc_logo.png missing in repo root — using gold text fallback.")
        v_filter = (
            f"[0:v]trim=start={st}:duration={main_dur},setpts=PTS-STARTPTS,"
            f"scale={pre_w}:{pre_h}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={out_w}:{out_h},unsharp=5:5:0.45:3:3:0.0,"
            f"fps=30,setsar=1,eq=contrast=1.02:saturation=1.03:brightness=0.005,"
            f"drawtext=fontfile='{font_path}':text='ARC':fontcolor=white@0.22:fontsize={top_px}:"
            f"x=(w-text_w)/2:y={top_y},format=yuv420p[main_v];"
            f"color=c=0x080808:s={out_w}x{out_h}:d={end_dur}:r=30,"
            f"drawtext=fontfile='{font_path}':text='A R C':fontcolor={GOLD_HEX}:fontsize={end_arc_px}:"
            f"x=(w-text_w)/2:y={end_arc_y},"
            f"drawtext=fontfile='{font_path}':text='{cta_safe}':fontcolor=white@0.95:fontsize={cta_px}:"
            f"x=(w-text_w)/2:y={end_cta_y},"
            f"fps=30,setsar=1,format=yuv420p[end_v];"
            f"[main_v][end_v]concat=n=2:v=1:a=0[vout];"
        )

    if clip_has_audio:
        orig_a = (
            f"[0:a]atrim=start={st}:duration={total_dur},asetpts=PTS-STARTPTS,"
            f"aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"volume='if(lt(t,{main_dur}),0.85,0.22)':eval=frame,"
            f"apad=whole_dur={total_dur},atrim=0:{total_dur}[orig_a];"
        )
    else:
        orig_a = (
            f"aevalsrc=0.04*sin(2*PI*55*t)+0.02*sin(2*PI*82.4*t):s=48000:d={total_dur},"
            f"aformat=sample_fmts=fltp:channel_layouts=stereo[orig_a];"
        )

    a_filter = (
        orig_a
        + f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
        f"volume=1.65,adelay={delay_ms}|{delay_ms},"
        f"apad=whole_dur={total_dur},atrim=0:{total_dur}[vo_a];"
        f"aevalsrc={sv1}*sin(2*PI*{f1}*t)+{sv2}*sin(2*PI*{f2}*t)+{sv3}*sin(2*PI*{f3}*t):"
        f"s=48000:d={total_dur},aformat=sample_fmts=fltp:channel_layouts=stereo[sub_bed];"
        f"[orig_a][vo_a][sub_bed]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,"
        f"alimiter=limit=0.95,afade=t=out:st={round(total_dur - 0.25, 2)}:d=0.25[aout]"
    )

    cmd = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-stream_loop", "-1", "-i", src_clip,
        "-i", vo_path,
    ]
    if logo_exists:
        cmd.extend(["-i", ARC_LOGO_PATH])

    cmd.extend([
        "-filter_complex", v_filter + a_filter,
        "-map", "[vout]", "-map", "[aout]",
        "-t", str(total_dur),
        "-c:v", "libx264", "-profile:v", "high", "-level:v", v_level,
        "-crf", crf_val, "-maxrate", "22M", "-bufsize", "44M",
        "-preset", preset_val, "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-map_metadata", "-1", "-metadata", f"creation_time={ts_iso}",
        output_path,
    ])

    try:
        res = subprocess.run(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=240,
        )
        if res.returncode != 0 or not os.path.exists(output_path):
            raise Exception(res.stderr.decode("utf-8", errors="ignore"))
        log(f"[RENDER] {out_w}x{out_h} | {total_dur}s (Main {main_dur}s + End {end_dur}s | '{cta_text}')")
    finally:
        if os.path.exists(vo_path):
            try:
                os.remove(vo_path)
            except Exception:
                pass
    return output_path


# ==========================================
# 6. INSTAGRAM & YOUTUBE PUBLISHERS
# ==========================================
def upload_for_meta_download(file_path):
    headers = {"User-Agent": "Mozilla/5.0"}
    relays = [
        ("https://catbox.moe/user/api.php", {"reqtype": "fileupload"}),
        ("https://litterbox.catbox.moe/resources/internals/api.php", {"reqtype": "fileupload", "time": "1h"}),
    ]
    for url, data in relays:
        try:
            with open(file_path, "rb") as f:
                r = requests.post(
                    url, data=data, files={"fileToUpload": f},
                    headers=headers, timeout=(15, 120),
                )
            if r.status_code == 200 and r.text.strip().startswith("https://"):
                return r.text.strip()
        except Exception:
            pass
    raise Exception("Relay upload failed.")


def publish_ig_reel(ig_user_id, video_url, caption, token):
    r = requests.post(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": token,
        },
        timeout=(10, 30),
    ).json()
    if "id" not in r:
        raise Exception(f"IG Container failed: {r}")

cid = r["id"]
    time.sleep(20)
    for _ in range(18):
        st = requests.get(
            f"https://graph.facebook.com/{GRAPH_API_VERSION}/{cid}",
            params={"fields": "status_code", "access_token": token},
            timeout=15,
        ).json()
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise Exception(f"Meta rejected: {st}")
        time.sleep(10)

    pub = requests.post(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}/media_publish",
        data={"creation_id": cid, "access_token": token},
        timeout=(10, 30),
    ).json()
    if "id" not in pub:
        raise Exception(f"IG Publish failed: {pub}")
    log(f"[IG SUCCESS] Published Reel! Media ID: {pub['id']}")


def publish_yt_short(file_path, title, description, refresh_token):
    tok_res = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": YT_CLIENT_ID,
            "client_secret": YT_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=20,
    ).json()
    access_token = tok_res.get("access_token")
    if not access_token:
        raise Exception(f"YT OAuth refresh failed: {tok_res}")

    meta = {
        "snippet": {"title": title[:95], "description": description, "categoryId": "22"},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    init_res = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        data=json.dumps(meta),
        timeout=30,
    )
    upload_url = init_res.headers.get("Location")
    if not upload_url:
        raise Exception(f"YT init failed: {init_res.text}")

    with open(file_path, "rb") as f:
        up_res = requests.put(
            upload_url, headers={"Content-Type": "video/mp4"}, data=f, timeout=180
        )
    if up_res.status_code not in (200, 201):
        raise Exception(f"YT upload failed: {up_res.text}")
    log(f"[YT SUCCESS] Published Short! Video ID: {up_res.json().get('id')}")


# ==========================================
# 7. MAIN EXECUTION
# ==========================================
def main():
    log("=== ARC AUTONOMOUS DISTRIBUTION ENGINE STARTED ===")
    ensure_edge_tts_installed()
    font_path = ensure_stylish_font()

    clip_pool = collect_source_clips(target_count=9)
    if not clip_pool:
        log("[ERROR] No source clips available.")
        return

    try:
        ig_accounts = get_all_healthy_ig_accounts()
        random.shuffle(ig_accounts)
        ig_ok = 0

        for idx, acc in enumerate(ig_accounts):
            label = acc["ig_username"] or acc["page_name"]
            log(f"\n--- IG [{idx + 1}/{len(ig_accounts)}]: {label} ---")
            out_file = f"arc_ig_{idx}.mp4"
            try:
                src_clip, _ = random.choice(clip_pool)
                render_arc_reel(src_clip, out_file, font_path, f"ig{idx}")
                pub_url = upload_for_meta_download(out_file)
                publish_ig_reel(acc["ig_user_id"], pub_url, generate_clean_caption(idx), acc["token"])
                ig_ok += 1
            except Exception as e:
                log(f"[IG SKIP] {e}")
            finally:
                if os.path.exists(out_file):
                    try:
                        os.remove(out_file)
                    except Exception:
                        pass
            if idx < len(ig_accounts) - 1:
                wait_s = random.randint(40, 80)
                log(f"[PACING] Sleeping {wait_s}s...")
                time.sleep(wait_s)

        yt_ok = 0
        if YT_CLIENT_ID and YT_CLIENT_SECRET and YT_REFRESH_TOKENS:
            for idx, r_tok in enumerate(YT_REFRESH_TOKENS):
                log(f"\n--- YT CHANNEL [{idx + 1}/{len(YT_REFRESH_TOKENS)}] ---")
                out_file = f"arc_yt_{idx}.mp4"
                try:
                    src_clip, _ = random.choice(clip_pool)
                    render_arc_reel(src_clip, out_file, font_path, f"yt{idx}")
                    publish_yt_short(out_file, random.choice(YT_TITLES), generate_clean_caption(idx), r_tok)
                    yt_ok += 1
                except Exception as e:
                    log(f"[YT SKIP] {e}")
                finally:
                    if os.path.exists(out_file):
                        try:
                            os.remove(out_file)
                        except Exception:
                            pass
                if idx < len(YT_REFRESH_TOKENS) - 1:
                    time.sleep(random.randint(20, 45))
        else:
            log("[YT INFO] YouTube secrets not added yet — skipping YT lane cleanly.")

        log(
            f"\n=== WAVE COMPLETE: {ig_ok}/{len(ig_accounts)} IG REELS | "
            f"{yt_ok}/{len(YT_REFRESH_TOKENS)} YT SHORTS ==="
        )
    finally:
        for fpath, is_temp in clip_pool:
            if is_temp and os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass


if __name__ == "__main__":
    main()
