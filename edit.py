"""Монтаж TikTok-відео: вирізає паузи, покращує картинку/звук, хук + субтитри (ASS).
Запуск: python3 edit.py  (читає in.mp4 і words.json з цієї ж папки, пише out.mp4)"""
import json, os, re, subprocess

D = os.path.dirname(os.path.abspath(__file__))
SRC, OUT, ASS = f"{D}/in.mp4", f"{D}/out.mp4", f"{D}/subs.ass"
W, H = 1080, 1920

# ---------- 1. паузи ----------
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                     "-of", "csv=p=0", SRC]).decode())
log = subprocess.run(["ffmpeg", "-i", SRC, "-af", "silencedetect=n=-35dB:d=0.35", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
keep, cur = [], 0.0
for a, b in zip(starts, ends):
    ca = 0.0 if a < 0.05 else a + 0.12      # лишаємо хвостик звуку
    cb = dur if b > dur - 0.05 else b - 0.08
    if cb - ca < 0.15:
        continue
    if ca - cur > 0.1:
        keep.append((cur, ca))
    cur = cb
if dur - cur > 0.1:
    keep.append((cur, dur))
offs, acc = [], 0.0
for a, b in keep:
    offs.append(acc); acc += b - a
NEW_DUR = acc


def remap(t, prefer_next):
    """Час оригіналу -> час змонтованого відео (якщо t у вирізаному — до найближчої межі)."""
    for (a, b), o in zip(keep, offs):
        if a <= t <= b:
            return o + t - a
        if t < a:
            return o if prefer_next else o - 0.001
    return NEW_DUR


# ---------- 2. текст ----------
segs = json.load(open(f"{D}/words.json"))
words = [w for s in segs for w in s["words"]]
FIX = {28: "стають", 38: "малютки", 46: "Тредсі", 53: "надзвичайно", 63: "компліментів",
       71: "Від них справді", 73: "шлейф"}
for i, t in FIX.items():
    words[i]["w"] = t + re.search(r"[.,!?…]*$", words[i]["w"].strip()).group()  # зберігаємо пунктуацію
for w in words:
    w["t"] = w["w"].strip()
    w["ns"], w["ne"] = remap(w["s"], True), remap(w["e"], False)
    w["ne"] = max(w["ne"], w["ns"] + 0.08)

HOOK_N = 9                                   # «Парфуми, до яких я буду повертатися знову і знову»
KEY = {12, 53, 63, 66, 77, 94}               # улюблена, надзвичайно, компліментів, фаворит, надовго, особливий
WHITE, GOLD, HOOK_Y = "&HFFFFFF&", "&H4AC9FF&", "&H00D4FF&"


def ts(t):
    t = max(0, t); cs = round(t * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def clean(t):
    return re.sub(r"[.,!?…]+$", "", t)


ev = []
# хук: 3 рядки по 3 слова, 1-2 білі, 3-тє жовте
hook_end = words[HOOK_N]["ns"] - 0.02
for li, g in enumerate([words[0:3], words[3:6], words[6:9]]):
    txt = " ".join(f"{{\\c{HOOK_Y if k == 2 else WHITE}}}{clean(w['t']).upper()}" for k, w in enumerate(g))
    fs = (106, 86, 124)[li]                   # «Я БУДУ ПОВЕРТАТИСЯ» довгий — менший кегль
    anim = (f"{{\\q2\\an5\\pos(540,{(330, 470, 615)[li]})\\fs{fs}\\fscx30\\fscy30\\alpha&HFF&"
            f"\\t(0,140,\\fscx115\\fscy115\\alpha&H00&)\\t(140,260,\\fscx100\\fscy100)\\fad(0,180)}}")
    ev.append(("Hook", g[0]["ns"], hook_end, anim + txt))

# звичайні субтитри: групи до 3 слів, активне слово — золоте
groups, g = [], []
for i in range(HOOK_N, len(words)):
    if g and sum(len(words[j]["t"]) + 1 for j in g) + len(words[i]["t"]) > 16:  # не ширше одного рядка
        groups.append(g); g = []
    g.append(i)
    t = words[i]["t"]
    if len(g) == 3 or re.search(r"[.,!?]$", t) or sum(len(words[j]["t"]) for j in g) > 15 or " " in t:
        groups.append(g); g = []
if g:
    groups.append(g)
for gi, g in enumerate(groups):
    g_end = words[g[-1]]["ne"] + 0.25
    if gi + 1 < len(groups):
        g_end = min(g_end, words[groups[gi + 1][0]]["ns"])
    for k, i in enumerate(g):
        st = words[i]["ns"]
        en = words[g[k + 1]]["ns"] if k + 1 < len(g) else g_end
        parts = []
        for j in g:
            t = clean(words[j]["t"])
            if j == i and j in KEY:
                parts.append(f"{{\\c{GOLD}\\fscx100\\fscy100\\t(0,90,\\fscx122\\fscy122)\\t(90,200,\\fscx114\\fscy114)}}{t}{{\\c{WHITE}\\fscx100\\fscy100}}")
            elif j == i:
                parts.append(f"{{\\c{GOLD}}}{t}{{\\c{WHITE}}}")
            else:
                parts.append(t)
        pop = "{\\fscx88\\fscy88\\t(0,110,\\fscx100\\fscy100)}" if k == 0 else ""
        ev.append(("Sub", st, en, pop + " ".join(parts)))

with open(ASS, "w") as f:
    f.write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,Unbounded ExtraBold,92,&H00FFFFFF,&H00FFFFFF,&H00101010,&H70000000,0,0,0,0,100,100,1,0,1,9,7,5,40,40,0,1
Style: Sub,Alethia Next,122,&H00FFFFFF,&H00FFFFFF,&H00140C0A,&H80000000,0,0,0,0,100,100,1,0,1,8,5,2,80,80,430,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""")
    for st, a, b, txt in ev:
        f.write(f"Dialogue: 0,{ts(a)},{ts(b)},{st},,0,0,0,,{txt}\n")

# ---------- 3. відео ----------
fav = remap(words[65]["s"], True)            # «мій фаворит» — ключовий момент
fc = [f"[0:v]hqdn3d=1.5:1.5:6:6,scale={W}:{H}:flags=lanczos,eq=contrast=1.06:saturation=1.12:brightness=0.01,"
      f"unsharp=5:5:0.7:5:5:0,split={len(keep)}" + "".join(f"[v{i}]" for i in range(len(keep))),
      f"[0:a]highpass=f=80,afftdn=nf=-25,asplit={len(keep)}" + "".join(f"[a{i}]" for i in range(len(keep)))]
for i, ((a, b), o) in enumerate(zip(keep, offs)):
    d = b - a
    if i == 0:     # хук: плавний наїзд камери
        z = f"scale=w='trunc({W}*(1+0.10*t/{d:.3f})/2)*2':h=-2:eval=frame:flags=bicubic"
    else:          # чергуємо план, щоб приховати склейки; на «фаворит» — сильний наїзд
        k = 1.16 if o <= fav < o + d else (1.08 if i % 2 else 1.0)
        z = f"scale={round(W * k / 2) * 2}:-2:flags=bicubic"
    fc.append(f"[v{i}]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS,{z},crop={W}:{H},setsar=1[V{i}]")
    fc.append(f"[a{i}]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.015,"
              f"afade=t=out:st={max(0, d - 0.02):.3f}:d=0.02[A{i}]")
fc.append("".join(f"[V{i}][A{i}]" for i in range(len(keep))) + f"concat=n={len(keep)}:v=1:a=1[cv][ca]")
fc.append(f"[cv]ass={ASS}:fontsdir=/root/.fonts,format=yuv420p[ov]")
fc.append("[ca]acompressor=threshold=-20dB:ratio=3:attack=5:release=120,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[oa]")

subprocess.run(["ffmpeg", "-v", "error", "-stats", "-y", "-i", SRC, "-filter_complex", ";".join(fc),
                "-map", "[ov]", "-map", "[oa]", "-r", "30", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                "-profile:v", "high", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", OUT], check=True)
print(f"keep={len(keep)} segs, {dur:.2f}s -> {NEW_DUR:.2f}s")
