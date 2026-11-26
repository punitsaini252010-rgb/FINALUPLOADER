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

class SilentLogger:
    def debug(self, m): pass
    def warning(self, m): pass
    def error(self, m): pass

META_TOKENS = [t.strip() for t in [os.getenv("META_TOKEN_1"), os.getenv("META_TOKEN_2"), os.getenv("META_TOKEN_3")] if t and t.strip()]
YT_CLIENT_ID = (os.getenv("YT_CLIENT_ID") or "").strip()
YT_CLIENT_SECRET = (os.getenv("YT_CLIENT_SECRET") or "").strip()
YT_REFRESH_TOKENS = [t.strip() for t in re.split(r"[\n,]+", os.getenv("YT_REFRESH_TOKENS") or "") if t.strip()]

API = "v20.0"
GREEN_HANDLES = {"arcbloodline2", "arcbloodline3", "arcbloodline4", "arcbloodline9", "arcbloodline19", "arcbloodline20", "arcbloodline23", "arcbloodline25", "arcbloodline26"}
FLAGGED_HANDLES = {f"arcbloodline{i}" for i in range(1, 27)} - GREEN_HANDLES
ASSETS_DIR, LOCAL_REELS_DIR, ARC_LOGO_PATH, FONT_PATH = "assets", "reels", "arc_logo.png", "Cinzel-Bold.ttf"
ENABLE_4K_UPSCALE = True

SOURCE_YT_CHANNELS = [
    "https://www.youtube.com/@SparkleOfLife-d2y/shorts",
    "https://www.youtube.com/@Luxurylife4628/shorts",
]

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

def make_caption(idx):
    tags = " ".join(random.sample(NICHE_TAGS, k=random.randint(2, 4)))
    return f"{random.choice(CAPTION_BODIES)}\n\n{CAPTION_CTAS[idx % len(CAPTION_CTAS)]}\n\n{tags}"

def is_allowed_ig(username, page_name):
    u, p = (username or "").strip().lower(), (page_name or "").strip().lower()
    if u in GREEN_HANDLES:
        return True
    if u in FLAGGED_HANDLES:
        return False
    return not any(re.search(rf"(^|[^a-z0-9]){re.escape(b)}([^0-9]|$)", p) for b in FLAGGED_HANDLES)

def get_ig_accounts():
    accs, seen = [], set()
    for tok in META_TOKENS:
        res = requests.get(f"https://graph.facebook.com/{API}/me/accounts", params={"fields": "id,name,instagram_business_account{id,username}", "limit": 100, "access_token": tok}, timeout=(10, 20)).json()
        if "error" in res:
            log(f"[TOKEN WARN] {res['error'].get('message')}")
            continue
        for pg in res.get("data", []):
            ig = pg.get("instagram_business_account")
            if ig and ig.get("id") and ig["id"] not in seen:
                uname, pname = ig.get("username", ""), pg.get("name", "ARC_Node")
                if is_allowed_ig(uname, pname):
                    seen.add(ig["id"])
                    accs.append({"page_name": pname, "ig_user_id": ig["id"], "ig_username": uname, "token": tok})
    log(f"[IG FLEET] Clean accounts ({len(accs)}): {[a['ig_username'] or a['page_name'] for a in accs]}")
    return accs

def media_dur(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        return float(r.stdout.decode().strip())
    except Exception:
        return 0.0

def has_audio(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", path], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        return bool(r.stdout.decode().strip())
    except Exception:
        return False

def collect_clips(target=9):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    clips = []
    if os.path.isdir(LOCAL_REELS_DIR):
        for fn in os.listdir(LOCAL_REELS_DIR):
            fp = os.path.join(LOCAL_REELS_DIR, fn)
            if fn.lower().endswith(".mp4") and media_dur(fp) >= 8.0:
                clips.append((fp, False))
    urls, chans = [], list(SOURCE_YT_CHANNELS)
    random.shuffle(chans)
    for ch in chans:
        try:
            with yt_dlp.YoutubeDL({"extract_flat": True, "playlistend": 60, "quiet": True, "no_warnings": True, "logger": SilentLogger(), "socket_timeout": 20}) as ydl:
                info = ydl.extract_info(ch, download=False)
            for e in (info.get("entries") or []):
                u = (e or {}).get("url") or (f"https://www.youtube.com/shorts/{e['id']}" if (e or {}).get("id") else None)
                if u and 8 <= ((e or {}).get("duration") or 20) <= 90:
                    urls.append(u if u.startswith("http") else f"https://www.youtube.com/shorts/{u}")
        except Exception as err:
            log(f"[SOURCE WARN] {ch}: {err}")
    random.shuffle(urls)
    for i, u in enumerate(urls[:30]):
        if len(clips) >= target:
            break
        out = os.path.join(ASSETS_DIR, f"src_{i}_{random.randint(100,999)}.mp4")
        try:
            with yt_dlp.YoutubeDL({"format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "merge_output_format": "mp4", "outtmpl": out, "noplaylist": True, "quiet": True, "no_warnings": True, "logger": SilentLogger(), "socket_timeout": 25}) as ydl:
                ydl.extract_info(u, download=True)
        except Exception:
            pass
        if os.path.exists(out) and os.path.getsize(out) > 200000 and media_dur(out) >= 8.0:
            clips.append((out, True))
            log(f"[PICKED] {u}")
        elif os.path.exists(out):
            os.remove(out)
    random.shuffle(clips)
    return clips

def get_font():
    if os.path.exists(FONT_PATH) and os.path.getsize(FONT_PATH) > 15000:
        return FONT_PATH
    for u in ["https://github.com/google/fonts/raw/main/ofl/cinzel/static/Cinzel-Bold.ttf", "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf"]:
        try:
            r = requests.get(u, timeout=15)
            if r.status_code == 200 and len(r.content) > 15000:
                with open(FONT_PATH, "wb") as f:
                    f.write(r.content)
                return FONT_PATH
        except Exception:
            pass
    return "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

def make_vo(text, out_mp3):
    v = random.choice(["en-US-AndrewMultilingualNeural", "en-US-BrianMultilingualNeural", "en-US-ChristopherNeural"])
    subprocess.run(["edge-tts", "--voice", v, "--rate=-2%", "--pitch=-4Hz", "--text", text, "--write-media", out_mp3], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=True)
    return media_dur(out_mp3)

def render_reel(src, out_mp4, font, tag):
    cta = random.choice(ARC_ONE_LINER_CTAS)
    vo = f"vo_{tag}_{random.randint(100,999)}.mp3"
    vo_d = make_vo(cta, vo)
    end_d = round(max(2.0, min(3.8, vo_d + 0.35)), 2)
    tot_d = round(random.uniform(10.5, 12.8), 2)
    main_d = round(max(7.5, tot_d - end_d), 2)
    tot_d = round(main_d + end_d, 2)
    st = round(random.uniform(0.15, 0.45), 2) if media_dur(src) > tot_d + 1.0 else 0.0
    logo_ok = os.path.exists(ARC_LOGO_PATH) and os.path.getsize(ARC_LOGO_PATH) > 500
    if ENABLE_4K_UPSCALE:
        ow, oh, pw, ph, mpx, bpx, tpx, cpx, epx, lxy, ty, edy, cy, eay, ecy, crf, pre, lvl = 2160, 3840, 2204, 3917, 78, 660, 54, 86, 210, "54:90", "98", "-230", "(h/2)+250", "(h/2)-250", "(h/2)+110", "17", "veryfast", "5.1"
    else:
        ow, oh, pw, ph, mpx, bpx, tpx, cpx, epx, lxy, ty, edy, cy, eay, ecy, crf, pre, lvl = 1080, 1920, 1102, 1958, 39, 330, 27, 44, 110, "27:45", "49", "-115", "(h/2)+125", "(h/2)-125", "(h/2)+55", "18", "faster", "4.2"
    f1, f3 = round(random.uniform(44.0, 66.0), 1), round(random.uniform(118.0, 162.0), 1)
    f2 = round(f1 * 1.5, 1)
    sv1, sv2, sv3 = round(random.uniform(0.010, 0.013), 4), round(random.uniform(0.006, 0.009), 4), round(random.uniform(0.004, 0.006), 4)
    cta_safe = cta.replace("'", "").replace(":", " -")
    ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(time.time()) - random.randint(600, 86400)))
    if logo_ok:
        vf = f"[2:v]split=2[l1][l2];[l1]scale={mpx}:{mpx}:force_original_aspect_ratio=decrease:flags=lanczos,format=rgba,colorchannelmixer=aa=0.45[ml];[l2]scale={bpx}:{bpx}:force_original_aspect_ratio=decrease:flags=lanczos,format=rgba[bl];[0:v]trim=start={st}:duration={main_d},setpts=PTS-STARTPTS,scale={pw}:{ph}:force_original_aspect_ratio=increase:flags=lanczos,crop={ow}:{oh},unsharp=5:5:0.45:3:3:0.0,fps=30,setsar=1,eq=contrast=1.02:saturation=1.03:brightness=0.005[mb];[mb][ml]overlay={lxy}[mlo];[mlo]drawtext=fontfile='{font}':text='ARC':fontcolor=white@0.22:fontsize={tpx}:x=(w-text_w)/2:y={ty},format=yuv420p[mv];color=c=0x080808:s={ow}x{oh}:d={end_d}:r=30[eb];[eb][bl]overlay=(W-w)/2:(H-h)/2{edy}[elo];[elo]drawtext=fontfile='{font}':text='{cta_safe}':fontcolor=0xFFD700:fontsize={cpx}:x=(w-text_w)/2:y={cy}:shadowcolor=black:shadowx=2:shadowy=2,fps=30,setsar=1,format=yuv420p[ev];[mv][ev]concat=n=2:v=1:a=0[vout];"
    else:
        vf = f"[0:v]trim=start={st}:duration={main_d},setpts=PTS-STARTPTS,scale={pw}:{ph}:force_original_aspect_ratio=increase:flags=lanczos,crop={ow}:{oh},unsharp=5:5:0.45:3:3:0.0,fps=30,setsar=1,eq=contrast=1.02:saturation=1.03:brightness=0.005,drawtext=fontfile='{font}':text='ARC':fontcolor=white@0.22:fontsize={tpx}:x=(w-text_w)/2:y={ty},format=yuv420p[mv];color=c=0x080808:s={ow}x{oh}:d={end_d}:r=30,drawtext=fontfile='{font}':text='A R C':fontcolor=0xFFD700:fontsize={epx}:x=(w-text_w)/2:y={eay},drawtext=fontfile='{font}':text='{cta_safe}':fontcolor=white@0.95:fontsize={cpx}:x=(w-text_w)/2:y={ecy},fps=30,setsar=1,format=yuv420p[ev];[mv][ev]concat=n=2:v=1:a=0[vout];"
    oa = f"[0:a]atrim=start={st}:duration={tot_d},asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume='if(lt(t,{main_d}),0.85,0.22)':eval=frame,apad=whole_dur={tot_d},atrim=0:{tot_d}[oa];" if has_audio(src) else f"aevalsrc=0.04*sin(2*PI*55*t)+0.02*sin(2*PI*82.4*t):s=48000:d={tot_d},aformat=sample_fmts=fltp:channel_layouts=stereo[oa];"
    af = oa + f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=1.65,adelay={int(main_d*1000)}|{int(main_d*1000)},apad=whole_dur={tot_d},atrim=0:{tot_d}[va];aevalsrc={sv1}*sin(2*PI*{f1}*t)+{sv2}*sin(2*PI*{f2}*t)+{sv3}*sin(2*PI*{f3}*t):s=48000:d={tot_d},aformat=sample_fmts=fltp:channel_layouts=stereo[sb];[oa][va][sb]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95,afade=t=out:st={round(tot_d-0.25,2)}:d=0.25[aout]"
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-stream_loop", "-1", "-i", src, "-i", vo] + (["-i", ARC_LOGO_PATH] if logo_ok else []) + ["-filter_complex", vf + af, "-map", "[vout]", "-map", "[aout]", "-t", str(tot_d), "-c:v", "libx264", "-profile:v", "high", "-level:v", lvl, "-crf", crf, "-maxrate", "22M", "-bufsize", "44M", "-preset", pre, "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-map_metadata", "-1", "-metadata", f"creation_time={ts_iso}", out_mp4]
    try:
        res = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=240)
        if res.returncode != 0 or not os.path.exists(out_mp4):
            raise Exception(res.stderr.decode(errors="ignore"))
        log(f"[RENDER] {ow}x{oh} | {tot_d}s | '{cta}'")
    finally:
        if os.path.exists(vo):
            os.remove(vo)
    return out_mp4

def upload_relay(fp):
    for u, d in [("https://catbox.moe/user/api.php", {"reqtype": "fileupload"}), ("https://litterbox.catbox.moe/resources/internals/api.php", {"reqtype": "fileupload", "time": "1h"})]:
        try:
            with open(fp, "rb") as f:
                r = requests.post(u, data=d, files={"fileToUpload": f}, headers={"User-Agent": "Mozilla/5.0"}, timeout=(15, 120))
            if r.status_code == 200 and r.text.strip().startswith("https://"):
                return r.text.strip()
        except Exception:
            pass
    raise Exception("Relay upload failed.")

def publish_ig(uid, vurl, cap, tok):
    r = requests.post(f"https://graph.facebook.com/{API}/{uid}/media", data={"media_type": "REELS", "video_url": vurl, "caption": cap, "share_to_feed": "true", "access_token": tok}, timeout=(10, 30)).json()
    if "id" not in r:
        raise Exception(f"IG Container failed: {r}")
    cid = r["id"]
    time.sleep(20)
    for _ in range(18):
        st = requests.get(f"https://graph.facebook.com/{API}/{cid}", params={"fields": "status_code", "access_token": tok}, timeout=15).json()
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise Exception(f"Meta rejected: {st}")
        time.sleep(10)
    pub = requests.post(f"https://graph.facebook.com/{API}/{uid}/media_publish", data={"creation_id": cid, "access_token": tok}, timeout=(10, 30)).json()
    if "id" not in pub:
        raise Exception(f"IG Publish failed: {pub}")
    log(f"[IG SUCCESS] Media ID: {pub['id']}")

def publish_yt(fp, title, desc, rtok):
    atok = requests.post("https://oauth2.googleapis.com/token", data={"client_id": YT_CLIENT_ID, "client_secret": YT_CLIENT_SECRET, "refresh_token": rtok, "grant_type": "refresh_token"}, timeout=20).json().get("access_token")
    if not atok:
        raise Exception("YT OAuth failed")
    init = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status", headers={"Authorization": f"Bearer {atok}", "Content-Type": "application/json; charset=UTF-8"}, data=json.dumps({"snippet": {"title": title[:95], "description": desc, "categoryId": "22"}, "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}), timeout=30)
    up_url = init.headers.get("Location")
    if not up_url:
        raise Exception(f"YT init failed: {init.text}")
    with open(fp, "rb") as f:
        up = requests.put(up_url, headers={"Content-Type": "video/mp4"}, data=f, timeout=180)
    if up.status_code not in (200, 201):
        raise Exception(f"YT upload failed: {up.text}")
    log(f"[YT SUCCESS] Video ID: {up.json().get('id')}")

def main():
    log("=== ARC ENGINE STARTED ===")
    font = get_font()
    clips = collect_clips(target=9)
    if not clips:
        log("[ERROR] No clips found.")
        return
    try:
        ig_accs = get_ig_accounts()
        random.shuffle(ig_accs)
        ig_ok = 0
        for i, acc in enumerate(ig_accs):
            log(f"\n--- IG [{i+1}/{len(ig_accs)}]: {acc['ig_username'] or acc['page_name']} ---")
            out = f"arc_ig_{i}.mp4"
            try:
                render_reel(random.choice(clips)[0], out, font, f"ig{i}")
                publish_ig(acc["ig_user_id"], upload_relay(out), make_caption(i), acc["token"])
                ig_ok += 1
            except Exception as e:
                log(f"[IG SKIP] {e}")
            finally:
                if os.path.exists(out):
                    os.remove(out)
            if i < len(ig_accs) - 1:
                time.sleep(random.randint(40, 80))
        yt_ok = 0
        if YT_CLIENT_ID and YT_CLIENT_SECRET and YT_REFRESH_TOKENS:
            for i, rtok in enumerate(YT_REFRESH_TOKENS):
                log(f"\n--- YT [{i+1}/{len(YT_REFRESH_TOKENS)}] ---")
                out = f"arc_yt_{i}.mp4"
                try:
                    render_reel(random.choice(clips)[0], out, font, f"yt{i}")
                    publish_yt(out, random.choice(YT_TITLES), make_caption(i), rtok)
                    yt_ok += 1
                except Exception as e:
                    log(f"[YT SKIP] {e}")
                finally:
                    if os.path.exists(out):
                        os.remove(out)
                if i < len(YT_REFRESH_TOKENS) - 1:
                    time.sleep(random.randint(20, 45))
        log(f"\n=== WAVE DONE: {ig_ok}/{len(ig_accs)} IG | {yt_ok}/{len(YT_REFRESH_TOKENS)} YT ===")
    finally:
        for fp, tmp in clips:
            if tmp and os.path.exists(fp):
                os.remove(fp)

if __name__ == "__main__":
    main()
# END OF FILE
