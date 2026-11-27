import os, re, sys, glob, json, time, random, requests, subprocess, yt_dlp

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

class Silent:
    def debug(self, m): pass
    def warning(self, m): pass
    def error(self, m): pass

TOKENS = [t.strip() for t in [os.getenv("META_TOKEN_1"), os.getenv("META_TOKEN_2"), os.getenv("META_TOKEN_3")] if t and t.strip()]
YT_ID, YT_SEC = (os.getenv("YT_CLIENT_ID") or "").strip(), (os.getenv("YT_CLIENT_SECRET") or "").strip()
YT_TOKS = [t.strip() for t in re.split(r"[\n,]+", os.getenv("YT_REFRESH_TOKENS") or "") if t.strip()]
IG_COOKIES_TXT = (os.getenv("IG_COOKIES_TXT") or "").strip()

DEFAULT_IG_SOURCES = "heriitageborn,worthy,aureonlux,luxurclassy,leornabs"
IG_SOURCES = [
    re.sub(r"\?.*$", "", u.strip().rstrip("/").split("/")[-1]).lstrip("@")
    for u in re.split(r"[\n,]+", os.getenv("IG_SOURCE_ACCOUNTS") or DEFAULT_IG_SOURCES)
    if u.strip()
]

API, LOGO, FONT, EXTRA_BED, HISTORY_FILE, ENABLE_4K = "v26.0", "arc_logo.png", "Cinzel-Bold.ttf", "bg_bed.mp3", "posted_history.json", True
GREEN = {"arcbloodline2", "arcbloodline3", "arcbloodline4", "arcbloodline9", "arcbloodline19", "arcbloodline20", "arcbloodline23", "arcbloodline25", "arcbloodline26"}
FLAGGED = {f"arcbloodline{i}" for i in range(1, 27)} - GREEN

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
CTAS = ["Link in bio to enter ARC.", "Comment \"ARC\" or tap the bio link.", "Step inside ARC through the link in bio.", "Bio link is live. Enter ARC."]
TAGS = ["#wealthmindset", "#oldmoney", "#digitalbusiness", "#financialfreedom", "#entrepreneurship", "#onlineincome", "#successmindset", "#businessowner", "#selfimprovement", "#wealthbuilding", "#darkluxury", "#mindset"]
TITLES = ["Build in Silence. Enter ARC. #Shorts", "Stop Watching. Start Building. #Shorts", "Why Silent Operators Always Win #Shorts", "Ownership Beats a Paycheck #Shorts", "The Blueprint Nobody Talks About #Shorts"]

def caption(i): return f"{random.choice(BODIES)}\n\n{CTAS[i % len(CTAS)]}\n\n{' '.join(random.sample(TAGS, k=random.randint(2, 4)))}"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            data = json.load(open(HISTORY_FILE, "r", encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("accounts", {})
                data.setdefault("global_counts", {})
                return data
        except Exception:
            pass
    return {"accounts": {}, "global_counts": {}}

def save_history(hist):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(hist, f, indent=2)
    except Exception as e:
        log(f"[HIST WARN] {e}")

def record_post(hist, acc_key, clip_id):
    acc_list = hist["accounts"].setdefault(acc_key, [])
    if clip_id not in acc_list:
        acc_list.append(clip_id)
    hist["global_counts"][clip_id] = hist["global_counts"].get(clip_id, 0) + 1
    save_history(hist)

def allowed_ig(u, p):
    u, p = (u or "").strip().lower(), (p or "").strip().lower()
    if u in GREEN: return True
    if u in FLAGGED: return False
    return not any(re.search(rf"(^|[^a-z0-9]){re.escape(b)}([^0-9]|$)", p) for b in FLAGGED)

def get_accounts():
    accs, seen = [], set()
    for tok in TOKENS:
        res = requests.get(f"https://graph.facebook.com/{API}/me/accounts", params={"fields": "id,name,instagram_business_account{id,username}", "limit": 100, "access_token": tok}, timeout=(10, 20)).json()
        if "error" in res:
            log(f"[TOKEN WARN] {res['error'].get('message')}")
            continue
        for pg in res.get("data", []):
            ig = pg.get("instagram_business_account")
            if ig and ig.get("id") and ig["id"] not in seen and allowed_ig(ig.get("username"), pg.get("name")):
                seen.add(ig["id"])
                accs.append({"name": pg.get("name", "ARC"), "uid": ig["id"], "user": ig.get("username", ""), "tok": tok})
    log(f"[FLEET] {len(accs)} active accounts: {[a['user'] or a['name'] for a in accs]}")
    return accs

def probe_dur(p):
    try: return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", p], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15).stdout.decode().strip())
    except Exception: return 0.0

def probe_aud(p):
    try: return bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", p], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15).stdout.decode().strip())
    except Exception: return False

def detect_shots(src, thresh=0.32):
    tot = probe_dur(src)
    if tot <= 1.2: return []
    cuts = [0.0]
    try:
        r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", src, "-vf", f"select='gt(scene,{thresh})',showinfo", "-f", "null", "-"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
        for m in re.finditer(r"pts_time:([0-9]+\.?[0-9]*)", r.stderr.decode(errors="ignore")):
            t = float(m.group(1))
            if 0.5 <= t <= tot - 0.5 and (t - cuts[-1]) >= 0.55: cuts.append(t)
    except Exception: pass
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
            if seg >= 0.8: shots.append((src, round(pos, 2), seg))
            pos += seg
    return shots

def collect_clips(hist, target=14):
    """Returns list of (filepath, clip_id, is_temp) and shot_bank."""
    os.makedirs("assets", exist_ok=True)
    clips, seen_ids, cfile = [], set(), None
    gcounts = hist.get("global_counts", {})

    if IG_COOKIES_TXT:
        cfile = f"assets/igc_{random.randint(1000,9999)}.txt"
        open(cfile, "w", encoding="utf-8").write(IG_COOKIES_TXT + "\n")

    try:
        if os.path.isdir("reels"):
            for fn in os.listdir("reels"):
                fp = os.path.join("reels", fn)
                if fn.lower().endswith((".mp4", ".mov", ".webm")) and probe_dur(fp) >= 3.0:
                    cid = f"local:{fn}"
                    clips.append((fp, cid, False))
                    seen_ids.add(cid)

        # Phase 1: flat scan all 5 target IG accounts to collect a randomized pool of Reel URLs
        candidates = []
        handles = random.sample(IG_SOURCES, len(IG_SOURCES))
        for h in handles:
            scan_opts = {
                "quiet": True, "no_warnings": True, "logger": Silent(),
                "socket_timeout": 25, "extract_flat": "in_playlist",
                "playlistend": 30, "sleep_interval_requests": 2,
            }
            if cfile: scan_opts["cookiefile"] = cfile
            try:
                with yt_dlp.YoutubeDL(scan_opts) as ydl:
                    info = ydl.extract_info(f"https://www.instagram.com/{h}/reels/", download=False)
                entries = (info or {}).get("entries") or []
                found_h = 0
                for e in entries:
                    if not e: continue
                    rid = e.get("id")
                    u = e.get("url") or e.get("webpage_url") or (f"https://www.instagram.com/reel/{rid}/" if rid else None)
                    if rid and u:
                        candidates.append((f"ig:{rid}", u, h))
                        found_h += 1
                log(f"[SCAN] @{h} -> {found_h} reels")
            except Exception as err:
                log(f"[SCAN WARN] @{h}: {str(err).splitlines()[0][:120]}")
            time.sleep(random.uniform(1.5, 3.0))

        # Prioritize fresh/least-used Reels while keeping random order within each usage tier
        random.shuffle(candidates)
        candidates.sort(key=lambda x: gcounts.get(x[0], 0))

        for cid, u, h in candidates:
            if len(clips) >= target: break
            if cid in seen_ids: continue
            raw_id = cid.split(":", 1)[1]
            base = os.path.join("assets", f"ig_{raw_id}")
            dl_opts = {
                "quiet": True, "no_warnings": True, "logger": Silent(),
                "socket_timeout": 30, "noplaylist": True,
                "merge_output_format": "mp4",
                "format": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
                "outtmpl": base + ".%(ext)s",
                "sleep_interval_requests": 2,
            }
            if cfile: dl_opts["cookiefile"] = cfile
            try:
                with yt_dlp.YoutubeDL(dl_opts) as ydl:
                    ydl.extract_info(u, download=True)
            except Exception as err:
                log(f"[DL WARN] {u}: {str(err).splitlines()[0][:120]}")
            found = [p for p in glob.glob(base + ".*") if not p.endswith((".part", ".ytdl", ".temp"))]
            picked = found[0] if found else None
            if picked and os.path.getsize(picked) > 150000 and probe_dur(picked) >= 3.0:
                clips.append((picked, cid, True))
                seen_ids.add(cid)
                log(f"[IG PICKED {len(clips)}/{target}] @{h} ({raw_id})")
            else:
                for p in glob.glob(base + ".*"):
                    try: os.remove(p)
                    except Exception: pass
            time.sleep(random.uniform(2.0, 4.0))

        # Phase 2 fallback: direct randomized download per profile if flat scan returned 0
        if len(clips) < target:
            per_acc = max(3, (target - len(clips)) // max(1, len(handles)) + 1)
            for h in handles:
                if len(clips) >= target: break
                dl_opts = {
                    "quiet": True, "no_warnings": True, "logger": Silent(),
                    "socket_timeout": 30, "playlistend": 25, "playlistrandom": True,
                    "max_downloads": per_acc, "merge_output_format": "mp4",
                    "format": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
                    "outtmpl": os.path.join("assets", f"igfb_{h}_%(id)s.%(ext)s"),
                    "noplaylist": False, "sleep_interval_requests": 2,
                }
                if cfile: dl_opts["cookiefile"] = cfile
                try:
                    with yt_dlp.YoutubeDL(dl_opts) as ydl:
                        ydl.extract_info(f"https://www.instagram.com/{h}/reels/", download=True)
                except yt_dlp.utils.MaxDownloadsReached:
                    pass
                except Exception as err:
                    log(f"[FB WARN] @{h}: {str(err).splitlines()[0][:120]}")
                for p in glob.glob(os.path.join("assets", f"igfb_{h}_*")):
                    if p.endswith((".part", ".ytdl", ".temp")): continue
                    rid = os.path.splitext(os.path.basename(p))[0].split(f"igfb_{h}_", 1)[-1]
                    cid = f"ig:{rid}"
                    if cid not in seen_ids and os.path.getsize(p) > 150000 and probe_dur(p) >= 3.0:
                        clips.append((p, cid, True))
                        seen_ids.add(cid)
                        log(f"[IG FB PICKED] @{h} ({rid})")
                time.sleep(random.uniform(2.0, 4.0))
    finally:
        if cfile and os.path.exists(cfile):
            try: os.remove(cfile)
            except Exception: pass

    random.shuffle(clips)
    bank = {fp: detect_shots(fp) for fp, _, _ in clips}
    log(f"[POOL] {len(clips)} unique reels | {sum(len(v) for v in bank.values())} scene shots ready")
    return clips, bank

def pick_unique_clip(clips, hist, acc_key, wave_used):
    """Picks a completely random clip never posted by acc_key and unused by other accounts in this wave."""
    posted = set(hist.get("accounts", {}).get(acc_key, []))
    gcounts = hist.get("global_counts", {})
    fresh_wave = [c for c in clips if c[1] not in posted and c[1] not in wave_used]
    if fresh_wave:
        random.shuffle(fresh_wave)
        fresh_wave.sort(key=lambda c: gcounts.get(c[1], 0))
        min_use = gcounts.get(fresh_wave[0][1], 0)
        tier = [c for c in fresh_wave if gcounts.get(c[1], 0) == min_use]
        return random.choice(tier)
    fresh_acc = [c for c in clips if c[1] not in posted]
    if fresh_acc:
        return random.choice(fresh_acc)
    return None

def get_font():
    if os.path.exists(FONT) and os.path.getsize(FONT) > 15000: return FONT
    for u in ["https://github.com/google/fonts/raw/main/ofl/cinzel/static/Cinzel-Bold.ttf", "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf"]:
        try:
            r = requests.get(u, timeout=15)
            if r.status_code == 200 and len(r.content) > 15000:
                open(FONT, "wb").write(r.content)
                return FONT
        except Exception: pass
    return "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

def build_seq(primary_fp, clips, bank, target_main):
    """Keeps primary_fp's 1st clip intact, slices & shuffles remaining clips, inserts 2x 0.5s ARC logo flashes."""
    f_shots = bank.get(primary_fp) or []
    first_st, first_d = (f_shots[0][1], f_shots[0][2]) if f_shots else (0.0, min(2.2, max(1.2, probe_dur(primary_fp) * 0.3)))

    # Mix remaining shots from primary clip + up to 2 other random clips so every account gets a unique shuffle
    other_fps = [c[0] for c in clips if c[0] != primary_fp]
    mix_fps = [primary_fp] + random.sample(other_fps, min(len(other_fps), 2))
    rem = [s for p in mix_fps for s in (bank.get(p) or []) if not (p == primary_fp and s[1] < first_st + first_d)]
    if not rem: rem = [(p, 0.1, 1.3) for p in mix_fps]
    random.shuffle(rem)

    budget = max(2.5, round(target_main - first_d - 1.0, 2))
    cuts, acc = [], 0.0
    while acc < budget and len(cuts) < 8:
        for s in rem:
            if acc >= budget or len(cuts) >= 8: break
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

def render(primary_fp, clips, bank, out_mp4, font, tag):
    cta, vo = random.choice(ONE_LINERS), f"vo_{tag}_{random.randint(100,999)}.mp3"
    v = random.choice(["en-US-AndrewMultilingualNeural", "en-US-BrianMultilingualNeural", "en-US-ChristopherNeural"])
    subprocess.run(["edge-tts", "--voice", v, "--rate=-2%", "--pitch=-4Hz", "--text", cta, "--write-media", vo], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=True)
    end_d = round(max(2.0, min(3.8, probe_dur(vo) + 0.35)), 2)
    items, first_src, first_st = build_seq(primary_fp, clips, bank, round(max(7.5, random.uniform(10.5, 12.8) - end_d), 2))
    main_d = round(sum(it[3] for it in items), 2)
    tot_d = round(main_d + end_d, 2)
    logo_ok = os.path.exists(LOGO) and os.path.getsize(LOGO) > 500
    bed_ok = os.path.exists(EXTRA_BED) and os.path.getsize(EXTRA_BED) > 5000

    ow, oh, pw, ph, mpx, bpx, fpx, tpx, cpx, epx, lxy, ty, edy, cy, eay, ecy, crf, pre, lvl, dx, dy = (
        (2160, 3840, 2224, 3954, 78, 660, 520, 54, 86, 210, "54:90", "98", "-230", "(h/2)+250", "(h/2)-250", "(h/2)+110", "17", "veryfast", "5.1", 28, 48)
        if ENABLE_4K else
        (1080, 1920, 1112, 1977, 39, 330, 260, 27, 44, 110, "27:45", "49", "-115", "(h/2)+125", "(h/2)-125", "(h/2)+55", "18", "faster", "4.2", 14, 24)
    )
    con, sat, gam = round(random.uniform(1.03, 1.07), 3), round(random.uniform(1.03, 1.08), 3), round(random.uniform(0.96, 1.02), 3)
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
        if it[0] == "clip": counts[s2i[it[1]]] = counts.get(s2i[it[1]], 0) + 1
    for i, c in counts.items():
        if c > 1: splits.append(f"[{i}:v]split={c}" + "".join(f"[s{i}_{j}]" for j in range(c)) + ";")
    n_flashes = sum(1 for it in items if it[0] == "logo")
    if logo_ok:
        splits.append(f"[{logo_i}:v]split={2 + n_flashes}[l1][l2]" + "".join(f"[lf{j}]" for j in range(n_flashes)) + ";")

    for k, (kind, src, st, dur) in enumerate(items):
        if kind == "logo" and logo_ok:
            segs.append(f"color=c=0x080808:s={ow}x{oh}:d={dur}:r=30[lb{k}];[lf{lcnt}]scale={fpx}:{fpx}:force_original_aspect_ratio=decrease:flags=lanczos,format=rgba[lg{k}];[lb{k}][lg{k}]overlay=(W-w)/2:(H-h)/2:eof_action=repeat,fps=30,setsar=1,format=yuv420p[v{k}];")
            lcnt += 1
        elif kind == "logo":
            segs.append(f"color=c=0x080808:s={ow}x{oh}:d={dur}:r=30,drawtext=fontfile='{font}':text='A R C':fontcolor=0xFFD700:fontsize={epx}:x=(w-text_w)/2:y=(h-text_h)/2,fps=30,setsar=1,format=yuv420p[v{k}];")
        else:
            idx = s2i[src]
            u = used.get(idx, 0)
            used[idx] = u + 1
            pin = f"[s{idx}_{u}]" if counts[idx] > 1 else f"[{idx}:v]"
            if k == 0:
                crop = f"crop={ow}:{oh}:{(pw-ow)//2}:{(ph-oh)//2}"
            else:
                x0, y0 = random.randint(0, max(1, pw - ow - dx)), random.randint(0, max(1, ph - oh - dy))
                vx, vy = random.choice([-1, 1]) * round(random.uniform(0.8, 2.0), 2), random.choice([-1, 1]) * round(random.uniform(1.0, 3.0), 2)
                crop = f"crop={ow}:{oh}:x='clip({x0}+{vx}*t,0,iw-{ow})':y='clip({y0}+{vy}*t,0,ih-{oh})':exact=1"
            segs.append(f"{pin}trim=start={st}:duration={dur},setpts=PTS-STARTPTS,scale={pw}:{ph}:force_original_aspect_ratio=increase:flags=lanczos,{crop},unsharp=5:5:0.35:3:3:0.0,eq=contrast={con}:saturation={sat}:gamma={gam}:brightness=0.004,noise=alls=2:allf=t+u,fps=30,setsar=1,format=yuv420p[v{k}];")

    cat = "".join(f"[v{k}]" for k in range(len(items)))
    csafe, ts = cta.replace("'", "").replace(":", " -"), time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(time.time()) - random.randint(600, 86400)))
    if logo_ok:
        vf = "".join(splits + segs) + f"{cat}concat=n={len(items)}:v=1:a=0[mb];[l1]scale={mpx}:{mpx}:force_original_aspect_ratio=decrease:flags=lanczos,format=rgba,colorchannelmixer=aa=0.45[ml];[l2]scale={bpx}:{bpx}:force_original_aspect_ratio=decrease:flags=lanczos,format=rgba[bl];[mb][ml]overlay={lxy}:eof_action=repeat[mlo];[mlo]drawtext=fontfile='{font}':text='ARC':fontcolor=white@0.22:fontsize={tpx}:x=(w-text_w)/2:y={ty},format=yuv420p[mv];color=c=0x080808:s={ow}x{oh}:d={end_d}:r=30[eb];[eb][bl]overlay=(W-w)/2:(H-h)/2{edy}:eof_action=repeat[elo];[elo]drawtext=fontfile='{font}':text='{csafe}':fontcolor=0xFFD700:fontsize={cpx}:x=(w-text_w)/2:y={cy}:shadowcolor=black:shadowx=2:shadowy=2,fps=30,setsar=1,format=yuv420p[ev];[mv][ev]concat=n=2:v=1:a=0[vout];"
    else:
        vf = "".join(splits + segs) + f"{cat}concat=n={len(items)}:v=1:a=0,drawtext=fontfile='{font}':text='ARC':fontcolor=white@0.22:fontsize={tpx}:x=(w-text_w)/2:y={ty},format=yuv420p[mv];color=c=0x080808:s={ow}x{oh}:d={end_d}:r=30,drawtext=fontfile='{font}':text='A R C':fontcolor=0xFFD700:fontsize={epx}:x=(w-text_w)/2:y={eay},drawtext=fontfile='{font}':text='{csafe}':fontcolor=white@0.95:fontsize={cpx}:x=(w-text_w)/2:y={ecy},fps=30,setsar=1,format=yuv420p[ev];[mv][ev]concat=n=2:v=1:a=0[vout];"

    aud_i = next((i for i, s in enumerate(usrcs) if probe_aud(s)), -1)
    ast = first_st if aud_i == 0 else 0.0
    oa = f"[{aud_i}:a]atrim=start={ast}:duration={tot_d},asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume='if(lt(t,{main_d}),0.95,0.22)':eval=frame,apad=whole_dur={tot_d},atrim=0:{tot_d}[oa];" if aud_i >= 0 else f"aevalsrc=0.04*sin(2*PI*55*t)+0.02*sin(2*PI*82.4*t):s=48000:d={tot_d},aformat=sample_fmts=fltp:channel_layouts=stereo[oa];"
    if bed_ok:
        ea = f"[{bed_i}:a]atrim=start=0:duration={tot_d},asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={round(random.uniform(0.025,0.045),4)},apad=whole_dur={tot_d},atrim=0:{tot_d}[ea];"
    else:
        f1, f3 = round(random.uniform(44.0, 66.0), 1), round(random.uniform(118.0, 162.0), 1)
        f2, sv1, sv2, sv3 = round(f1 * 1.5, 1), round(random.uniform(0.010, 0.013), 4), round(random.uniform(0.006, 0.009), 4), round(random.uniform(0.004, 0.006), 4)
        ea = f"aevalsrc={sv1}*sin(2*PI*{f1}*t)+{sv2}*sin(2*PI*{f2}*t)+{sv3}*sin(2*PI*{f3}*t):s=48000:d={tot_d},aformat=sample_fmts=fltp:channel_layouts=stereo[ea];"
    af = oa + ea + f"[{vo_i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=1.65,adelay={int(main_d*1000)}|{int(main_d*1000)},apad=whole_dur={tot_d},atrim=0:{tot_d}[va];[oa][ea][va]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95,afade=t=out:st={round(tot_d-0.25,2)}:d=0.25[aout]"

    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y"] + inputs + ["-filter_complex", vf + af, "-map", "[vout]", "-map", "[aout]", "-t", str(tot_d), "-c:v", "libx264", "-profile:v", "high", "-level:v", lvl, "-crf", crf, "-maxrate", "22M", "-bufsize", "44M", "-preset", pre, "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-map_metadata", "-1", "-metadata", f"creation_time={ts}", out_mp4]
    try:
        res = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if res.returncode != 0 or not os.path.exists(out_mp4): raise Exception(res.stderr.decode(errors="ignore"))
        log(f"[RENDER] {ow}x{oh} | {tot_d}s | 1st intact + {len(items)-3} shuffled + 2x0.5s ARC | '{cta}'")
    finally:
        if os.path.exists(vo): os.remove(vo)

def relay(fp):
    for u, d in [("https://catbox.moe/user/api.php", {"reqtype": "fileupload"}), ("https://litterbox.catbox.moe/resources/internals/api.php", {"reqtype": "fileupload", "time": "1h"})]:
        try:
            with open(fp, "rb") as f: r = requests.post(u, data=d, files={"fileToUpload": f}, headers={"User-Agent": "Mozilla/5.0"}, timeout=(15, 120))
            if r.status_code == 200 and r.text.strip().startswith("https://"): return r.text.strip()
        except Exception: pass
    raise Exception("Relay failed")

def post_ig(uid, vurl, cap, tok):
    r = requests.post(f"https://graph.facebook.com/{API}/{uid}/media", data={"media_type": "REELS", "video_url": vurl, "caption": cap, "share_to_feed": "true", "access_token": tok}, timeout=(10, 30)).json()
    if "id" not in r: raise Exception(f"Container failed: {r}")
    cid = r["id"]
    time.sleep(20)
    for _ in range(18):
        st = requests.get(f"https://graph.facebook.com/{API}/{cid}", params={"fields": "status_code", "access_token": tok}, timeout=15).json()
        if st.get("status_code") == "FINISHED": break
        if st.get("status_code") in ("ERROR", "EXPIRED"): raise Exception(f"Meta rejected: {st}")
        time.sleep(10)
    pub = requests.post(f"https://graph.facebook.com/{API}/{uid}/media_publish", data={"creation_id": cid, "access_token": tok}, timeout=(10, 30)).json()
    if "id" not in pub: raise Exception(f"Publish failed: {pub}")
    log(f"[IG OK] Media ID: {pub['id']}")

def post_yt(fp, title, desc, rtok):
    atok = requests.post("https://oauth2.googleapis.com/token", data={"client_id": YT_ID, "client_secret": YT_SEC, "refresh_token": rtok, "grant_type": "refresh_token"}, timeout=20).json().get("access_token")
    if not atok: raise Exception("YT OAuth failed")
    init = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status", headers={"Authorization": f"Bearer {atok}", "Content-Type": "application/json; charset=UTF-8"}, data=json.dumps({"snippet": {"title": title[:95], "description": desc, "categoryId": "22"}, "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}), timeout=30)
    up_url = init.headers.get("Location")
    if not up_url: raise Exception(f"YT init failed: {init.text}")
    with open(fp, "rb") as f: up = requests.put(up_url, headers={"Content-Type": "video/mp4"}, data=f, timeout=180)
    if up.status_code not in (200, 201): raise Exception(f"YT upload failed: {up.text}")
    log(f"[YT OK] Video ID: {up.json().get('id')}")

def main():
    log("=== ARC ENGINE STARTED ===")
    hist = load_history()
    accs = get_accounts()
    target_pool = max(14, len(accs) + len(YT_TOKS) + 3)
    font, (clips, bank) = get_font(), collect_clips(hist, target=target_pool)
    if not clips: return log("[ERROR] No clips found")
    wave_used = set()
    try:
        ig_ok, yt_ok = 0, 0
        random.shuffle(accs)
        for i, a in enumerate(accs):
            acc_key = f"ig:{a['uid']}"
            log(f"\n--- IG [{i+1}/{len(accs)}]: {a['user'] or a['name']} ---")
            chosen = pick_unique_clip(clips, hist, acc_key, wave_used)
            if not chosen:
                log("[IG SKIP] All available clips already posted by this account")
                continue
            fp, cid, _ = chosen
            wave_used.add(cid)
            log(f"[ASSIGNED] {cid}")
            out = f"arc_ig_{i}.mp4"
            try:
                render(fp, clips, bank, out, font, f"ig{i}")
                post_ig(a["uid"], relay(out), caption(i), a["tok"])
                record_post(hist, acc_key, cid)
                ig_ok += 1
            except Exception as e:
                log(f"[IG SKIP] {e}")
            finally:
                if os.path.exists(out): os.remove(out)
            if i < len(accs) - 1:
                wait_s = random.randint(45, 115)
                log(f"[WAIT] {wait_s}s before next account...")
                time.sleep(wait_s)

        if YT_ID and YT_SEC and YT_TOKS:
            for i, rt in enumerate(YT_TOKS):
                acc_key = f"yt:{i}"
                log(f"\n--- YT [{i+1}/{len(YT_TOKS)}] ---")
                chosen = pick_unique_clip(clips, hist, acc_key, wave_used)
                if not chosen:
                    log("[YT SKIP] All available clips already posted by this channel")
                    continue
                fp, cid, _ = chosen
                wave_used.add(cid)
                out = f"arc_yt_{i}.mp4"
                try:
                    render(fp, clips, bank, out, font, f"yt{i}")
                    post_yt(out, random.choice(TITLES), caption(i), rt)
                    record_post(hist, acc_key, cid)
                    yt_ok += 1
                except Exception as e:
                    log(f"[YT SKIP] {e}")
                finally:
                    if os.path.exists(out): os.remove(out)
                if i < len(YT_TOKS) - 1:
                    time.sleep(random.randint(25, 60))

        log(f"\n=== WAVE DONE: {ig_ok}/{len(accs)} IG | {yt_ok}/{len(YT_TOKS)} YT ===")
    finally:
        for fp, _, tmp in clips:
            if tmp and os.path.exists(fp):
                try: os.remove(fp)
                except Exception: pass

if __name__ == "__main__":
    main()
# END_ARC_ENGINE
