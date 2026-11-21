#!/usr/bin/env python3
"""Render the front page for Friday 20 November 2026 as one 1024x1024 PNG.

v12 renderer, written fresh in this session. Deterministic: fixed seed,
no clock, no network. Run twice and the bytes are identical.

Design: broadsheet front page. Giant dated masthead, six-number stat
strip, seven-region bar, a UTC timeline of the day, three illustrated
leads with big banner headlines painted ON the art, ten illustrated
feature tiles, a numbered world map, 23 more dated briefs, a DATE CHECK
box that keeps Thursday's news out, and a source footer.
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
MARGIN = 22
CONTENT = W - 2 * MARGIN  # 980

# ---------------------------------------------------------------- palette
PAPER = (246, 239, 220)
PAPER_DK = (238, 229, 203)
INK = (23, 19, 14)
INK_SOFT = (74, 66, 55)
RED = (176, 30, 40)
RED_DK = (138, 20, 30)
NAVY = (16, 28, 51)
NAVY2 = (28, 48, 84)
TEAL = (14, 95, 107)
TEAL_DK = (9, 62, 70)
GREEN = (31, 110, 62)
GOLD = (201, 148, 32)
CREAM = (250, 246, 232)
WHITE = (255, 255, 255)
GREY = (120, 112, 98)
RULE = (23, 19, 14)
SKY = (146, 190, 220)
SEA = (64, 128, 158)

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


SERIF_B = lambda s: font("DejaVuSerif-Bold.ttf", s)
SERIF_I = lambda s: ImageFont.truetype(
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf", s)
SERIF = lambda s: font("DejaVuSerif.ttf", s)
SANS_B = lambda s: font("DejaVuSans-Bold.ttf", s)
SANS = lambda s: font("DejaVuSans.ttf", s)
MONO_B = lambda s: font("DejaVuSansMono-Bold.ttf", s)

RNG = random.Random(20261120)


# ---------------------------------------------------------------- helpers
def text_w(draw, text, fnt):
    return draw.textlength(text, font=fnt)


def wrap(draw, text, fnt, max_w):
    """Greedy word wrap; returns list of lines that fit max_w."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=fnt) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def para(draw, x, y, text, fnt, color, max_w, leading, max_lines=None):
    """Draw wrapped paragraph; return y just below the last line."""
    lines = wrap(draw, text, fnt, max_w)
    if max_lines is not None:
        lines = lines[:max_lines]
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=color)
        y += leading
    return y


def hline(draw, x0, x1, y, color=INK, width=1):
    draw.line([(x0, y), (x1, y)], fill=color, width=width)


def vgrad(draw, box, top, bottom):
    """Vertical gradient fill inside box (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = box
    span = max(1, y1 - y0)
    for yy in range(y0, y1):
        t = (yy - y0) / span
        col = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        draw.line([(x0, yy), (x1, yy)], fill=col)


def speckle(draw, box, n, color, rmax=2):
    x0, y0, x1, y1 = box
    for _ in range(n):
        x = RNG.randint(x0, x1)
        y = RNG.randint(y0, y1)
        r = RNG.randint(1, rmax)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def banner(draw, box, text, fnt, bg=RED, fg=WHITE, pad=8, max_size=None):
    """Solid banner band across the top of an art box with big text.

    The text is shrunk until it fits the box width, so a long banner
    never clips at the edge.
    """
    x0, y0, x1, y1 = box
    size = fnt.size if max_size is None else max_size
    while size > 11:
        trial = SANS_B(size)
        if draw.textlength(text, font=trial) <= (x1 - x0) - 2 * pad:
            break
        size -= 1
    fnt = SANS_B(size)
    bh = fnt.size + 2 * pad
    draw.rectangle([x0, y0, x1, y0 + bh], fill=bg)
    draw.text((x0 + pad, y0 + pad - 1), text, font=fnt, fill=fg)
    return y0 + bh


def chip(draw, x, y, text, fnt, bg=INK, fg=WHITE):
    """Small filled source chip; returns width used."""
    w = int(draw.textlength(text, font=fnt)) + 12
    h = fnt.size + 8
    draw.rectangle([x, y, x + w, y + h], fill=bg)
    draw.text((x + 6, y + 4), text, font=fnt, fill=fg)
    return w


def kicker_line(draw, x, y, num, place, beat, src, max_w):
    """'01 · KYIV, UKRAINE — WAR' left, source right, red bold."""
    left = "%s · %s — %s" % (num, place, beat)
    draw.text((x, y), left, font=SANS_B(11), fill=RED)
    sw = draw.textlength(src, font=SANS_B(10))
    draw.text((x + max_w - sw, y + 1), src, font=SANS_B(10), fill=INK_SOFT)


# ---------------------------------------------------------------- the day
STATS = [
    ("3", "bridges damaged in Kyiv"),
    ("370,000", "evacuated ahead of Akvan"),
    ("\u22126.2%", "Taiwan Taiex, Friday close"),
    ("100,000", "UK\u2013EU youth visas a year"),
    ("2.3%", "Japan Oct CPI; BoJ hike eyed"),
    ("118", "Phillips runs vs India"),
]

REGIONS = [
    ("EUROPE", 8, (38, 74, 130)),
    ("ASIA-PACIFIC", 8, (176, 84, 32)),
    ("MIDDLE EAST", 4, (14, 110, 110)),
    ("AFRICA", 3, (110, 110, 40)),
    ("AMERICAS", 7, (150, 40, 48)),
    ("OCEANIA", 4, (40, 120, 130)),
    ("GLOBAL", 2, (110, 110, 110)),
]

UTC_STRIP = [
    ("OVERNIGHT", "Missiles hit Kyiv; Akvan nears India"),
    ("MORNING", "Akvan landfall 8 am"),
    ("MIDDAY", "EU\u2013UK summit \u00b7 COP31 final day"),
    ("AFTERNOON", "Asian close: Taiex \u22126.2%"),
    ("EVENING", "BepiColombo nears Mercury"),
]

LEADS = [
    {
        "num": "01", "place": "KYIV, UKRAINE", "beat": "WAR", "src": "REUTERS",
        "banner": "KYIV \u2014 3 BRIDGES HIT",
        "head": "Russian barrage hits three Kyiv bridges",
        "body": ("Overnight ballistic-missile barrage kills 3, damages three "
                 "bridges across the Dnipro and sets fires in three districts; "
                 "110+ missiles fired."),
        "scene": "kyiv",
    },
    {
        "num": "02", "place": "ODISHA, INDIA", "beat": "STORM", "src": "IMD",
        "banner": "CYCLONE AKVAN \u2014 LANDFALL",
        "head": "Cyclone Akvan makes landfall in eastern India",
        "body": ("Severe storm crosses near Gopalpur Friday morning; 370,000 "
                 "evacuated, 9,341 shelters, 423 teams; winds 70\u201380, "
                 "gusting 90 km/h; no deaths."),
        "scene": "akvan",
    },
    {
        "num": "03", "place": "SEOUL \u00b7 TOKYO", "beat": "MARKETS", "src": "REUTERS",
        "banner": "AI SELL-OFF \u2014 WORST SINCE 1991",
        "head": "AI sell-off sinks Asia to worst week since 1991",
        "body": ("Nikkei \u22125.1%, Kospi \u22125.2%, Taiex \u22126.2%, SoftBank "
                 "\u221214.5% on the week, worst since 1991."),
        "scene": "markets",
    },
]

MIDS = [
    {"num": "04", "place": "ANTALYA", "beat": "CLIMATE", "src": "REUTERS",
     "banner": "COP31: NO DEAL", "fact": "DEADLOCK",
     "head": "COP31 reaches final day deadlocked",
     "body": "Draft omits fossil-fuel phase-out and $120bn adaptation target.",
     "scene": "cop"},
    {"num": "05", "place": "MERCURY", "beat": "SPACE", "src": "ESA \u00b7 BBC",
     "banner": "BEPICOLOMBO", "fact": "6BN MILES",
     "head": "BepiColombo reaches Mercury after 8 years",
     "body": "ESA/JAXA probe ends 6bn-mile trip; orbit insertion Saturday.",
     "scene": "mercury"},
    {"num": "06", "place": "BRUSSELS", "beat": "EUROPE", "src": "AP",
     "banner": "RESET TALKS", "fact": "100,000 VISAS",
     "head": "Burnham holds second EU\u2013UK reset summit",
     "body": "Deals on food, emissions trading, youth mobility for 100,000.",
     "scene": "brussels"},
    {"num": "07", "place": "TOKYO", "beat": "ECONOMY", "src": "STATISTICS BUREAU",
     "banner": "JAPAN: +2.3%", "fact": "2.3% CPI",
     "head": "Japan inflation hits 2.3%; BoJ hike eyed",
     "body": "Oct CPI 2.3%, up from 2.1%; core 2.2%.",
     "scene": "tokyo"},
    {"num": "08", "place": "BEIJING", "beat": "RATES", "src": "PBoC \u00b7 REUTERS",
     "banner": "RATES HELD", "fact": "3.00% \u00b7 3.50%",
     "head": "China holds lending rates for 18th month",
     "body": "1-yr LPR 3.00%, 5-yr 3.50% as expected.",
     "scene": "beijing"},
    {"num": "09", "place": "WELLINGTON", "beat": "CRICKET", "src": "ICC",
     "banner": "PHILLIPS: 118", "fact": "118 RUNS",
     "head": "Phillips makes history with 118 vs India",
     "body": "Centuries vs India in all 3 formats in one year; NZ 368.",
     "scene": "cricket"},
    {"num": "10", "place": "ROME", "beat": "LABOUR", "src": "ANSA",
     "banner": "ITALY: STRIKE", "fact": "100 SQUARES",
     "head": "Italy\u2019s CGIL holds 24-hr general strike",
     "body": "Unions rally across ~100 squares against the 2027 budget.",
     "scene": "rome"},
    {"num": "11", "place": "MATO GROSSO", "beat": "LAND", "src": "ONE TURN",
     "banner": "ANCESTRAL LANDS", "fact": "KAPOT NHINORE",
     "head": "Lula visits ailing Chief Raoni, 94",
     "body": "Kayapo and Yudja lands recognised (Kapot Nhinore).",
     "scene": "raoni"},
    {"num": "12", "place": "BARCELONA", "beat": "HEALTH", "src": "EORTC",
     "banner": "TUMOURS \u221260.7%", "fact": "60.7% RESPONSE",
     "head": "Daraxonrasib + chemo shrinks tumours in 60.7%",
     "body": "Early trial, 61 patients, presented Friday at ENA.",
     "scene": "health"},
    {"num": "13", "place": "TURIN", "beat": "TENNIS", "src": "ATP",
     "banner": "ATP FINALS", "fact": "SEMIS SATURDAY",
     "head": "Alcaraz\u2013Cobolli & Medvedev\u2013Tiafoe close groups",
     "body": "Group stage ends Friday; semi-finals Saturday.",
     "scene": "tennis"},
]

BRIEFS = [
    ("14", "FLORIDA", "St Johns River hits record 18.3 ft.", "AP"),
    ("15", "DOHA", "Australia stuns Argentina 2\u20130 at U17 World Cup.", "FIFA"),
    ("16", "SEOUL", "Move to impeach Chief Justice Cho Hee-dae.", "SBS"),
    ("17", "BOUGAINVILLE", "Rio Tinto pledges $370m Panguna repair.", "ABC"),
    ("18", "CANBERRA", "CBO: AUKUS sales may shrink US fleet.", "Reuters"),
    ("19", "IOWA", "Army to detonate 68 unstable explosive barrels.", "AP"),
    ("20", "TONGA", "El Ni\u00f1o drought bites.", "RNZ"),
    ("21", "COPENHAGEN", "Greenland defence bill approved.", "AFP"),
    ("22", "GLOBAL", "UN marks World Children\u2019s Day.", "UN News"),
    ("23", "DAKAR", "President Faye enacts budget by decree.", "AFP"),
    ("24", "HORMUZ", "Attacks on vessels in 96 hours.", "UKMTO"),
    ("25", "NEW DELHI", "Pakistan minister to lead SCO team.", "The Hindu"),
    ("26", "HONG KONG", "Badminton Open semifinals decided.", "BWF"),
    ("27", "TAIPEI", "Short-sell curbs in; bombers tracked.", "Reuters"),
    ("28", "EUROPE", "Youth strike in 25+ countries.", "One Turn"),
    ("29", "WASHINGTON", "Trump: open to NATO-like Ukraine deal.", "WTD"),
    ("30", "BOGOT\u00c1", "Protests over tax plans amid US row.", "WTD"),
    ("31", "LILONGWE", "Malawi fuel crisis sparks chaos nationwide.", "WTD"),
    ("32", "GAZA", "Civil Defence struggles as vehicles fail.", "WTD"),
    ("33", "BRAZIL", "Violent deaths at series low, \u221212.2%.", "1stHeadlines"),
    ("34", "ALGIERS", "World Bank: Algeria growth at 3.7%.", "1stHeadlines"),
    ("35", "SANTIAGO", "Fuel relief bill may cost $813m.", "1stHeadlines"),
    ("36", "BRUSSELS", "EU adopts \u20ac1bn military aid for Ukraine.", "Council of the EU"),
]

DATE_CHECK = (
    "First reported Thursday 19 Nov, so NOT shown as Friday\u2019s news: "
    "Trump\u2013Xi\u2013Putin Shenzhen talks + \u2018peace declaration\u2019 \u00b7 "
    "ICJ Myanmar Rohingya genocide verdict (9\u20136) \u00b7 GTA VI midnight "
    "launch / $190.4m Van Gogh sale \u00b7 Voyager 1 one-light-day "
    "confirmation \u00b7 Senate 48\u201351 Iran war-powers vote."
)

FOOTER = ("Every story here happened, or was first reported, on Friday 20 "
          "November 2026. Officials\u2019 counts are attributed. Sources "
          "named per story \u00b7 Full list in SOURCES.md \u00b7 Original drawings.")

# ---------------------------------------------------------------- scenes
# Each painter fills the area below its banner with a dark, saturated,
# high-contrast scene: big shapes, few details, readable at 300 px.

def scene_kyiv(draw, box):
    x0, y0, x1, y1 = box
    vgrad(draw, box, (24, 30, 66), (10, 14, 34))
    speckle(draw, box, 26, (255, 240, 180), 1)
    # skyline silhouettes (heights clamped to the scene box)
    bh = y1 - y0
    base = y1 - 22
    bx = x0 + 4
    for wdt, hgt in [(34, 30), (26, 22), (40, 36), (30, 26), (36, 33), (28, 24), (34, 28)]:
        hgt = min(hgt, bh - 26)
        draw.rectangle([bx, base - hgt, bx + wdt, base], fill=(8, 10, 22))
        for wy in range(base - hgt + 6, base - 6, 9):
            for wx in range(bx + 5, bx + wdt - 5, 9):
                if RNG.random() < 0.45:
                    draw.rectangle([wx, wy, wx + 3, wy + 4], fill=(255, 214, 110))
        bx += wdt + 5
        if bx > x1 - 30:
            break
    # river + three arched bridges
    draw.rectangle([x0, base, x1, y1], fill=(30, 74, 120))
    draw.rectangle([x0, base, x1, base + 3], fill=(90, 150, 200))
    for cx in (x0 + 52, x0 + 150, x0 + 248):
        draw.arc([cx - 34, base - 16, cx + 34, base + 16], 180, 360,
                 fill=(235, 240, 245), width=4)
        draw.line([(cx - 34, base - 2), (cx + 34, base - 2)],
                  fill=(235, 240, 245), width=3)
    # explosion bursts over the river
    for cx, cy, r in [(x0 + 96, base - 22, 11), (x0 + 205, base - 28, 13),
                      (x0 + 268, base - 18, 9)]:
        for k in range(8):
            ang = k * math.pi / 4
            draw.line([(cx, cy), (cx + int(r * math.cos(ang)),
                                   cy + int(r * math.sin(ang)))],
                      fill=(255, 176, 40), width=3)
        draw.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=(255, 220, 120))
    # missile trails: dashed arcs
    for sx, sy, ex, ey in [(x0 + 30, y0 + 6, x0 + 96, base - 22),
                           (x0 + 120, y0 + 4, x0 + 205, base - 28)]:
        for t in range(0, 11):
            tt = t / 10.0
            px = int(sx + (ex - sx) * tt)
            py = int(sy + (ey - sy) * tt - 26 * math.sin(tt * math.pi))
            if t % 2 == 0:
                draw.ellipse([px - 2, py - 2, px + 2, py + 2],
                             fill=(255, 255, 255))


def scene_akvan(draw, box):
    x0, y0, x1, y1 = box
    vgrad(draw, box, (16, 110, 128), (10, 66, 84))
    # coastline: pale land on the left
    draw.polygon([(x0, y0), (x0 + 74, y0), (x0 + 52, y1),
                  (x0, y1)], fill=(214, 196, 150))
    draw.polygon([(x0, y0), (x0 + 74, y0), (x0 + 52, y1),
                  (x0, y1)], outline=(120, 100, 70))
    draw.text((x0 + 8, y0 + 6), "GOPALPUR", font=SANS_B(11), fill=(90, 60, 30))
    # spiral: concentric rings around the eye (clamped to the scene box)
    bh = y1 - y0
    cx, cy = x0 + 190, y0 + bh // 2 + 6
    for r in (38, 28, 18, 9):
        r = min(r, bh // 2 - 2)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     outline=(255, 255, 255), width=3)
    draw.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=(176, 30, 40))
    draw.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], outline=(255, 255, 255))
    # rain slashes
    for i in range(26):
        rx = RNG.randint(x0 + 80, x1 - 8)
        ry = RNG.randint(y0 + 4, y1 - 8)
        draw.line([(rx, ry), (rx - 7, ry + 12)], fill=(200, 225, 235), width=2)
    # red landfall marker + label
    draw.ellipse([cx - 52, cy - 52, cx - 44, cy - 44], fill=(176, 30, 40))
    draw.ellipse([cx - 52, cy - 52, cx - 44, cy - 44],
                 outline=(255, 255, 255), width=2)


def scene_markets(draw, box):
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill=(22, 8, 10))
    # grid
    for gy in range(y0 + 12, y1 - 4, 16):
        draw.line([(x0 + 6, gy), (x1 - 6, gy)], fill=(70, 34, 38))
    # falling candlesticks (clamped to the scene box)
    bh = y1 - y0
    n = 7
    step = (x1 - x0 - 24) // n
    tops = [12, 18, 28, 32, 40, 44, 48]
    tops = [min(t, bh - 22) for t in tops]
    for i, tp in enumerate(tops):
        cx = x0 + 16 + i * step
        top = y0 + tp
        bot = top + 12
        col = (214, 48, 48) if i % 2 == 0 else (120, 200, 110)
        draw.line([(cx + 6, y0 + tp - 8), (cx + 6, bot + 8)], fill=col, width=2)
        draw.rectangle([cx, top, cx + 12, bot], fill=col)
    # red down arrow
    pts = [(x0 + 14, y0 + 16), (x0 + 110, y0 + 44),
           (x0 + 200, y0 + 62), (x1 - 14, y1 - 12)]
    draw.line(pts, fill=(255, 80, 70), width=4)
    draw.polygon([(x1 - 14, y1 - 12), (x1 - 30, y1 - 16), (x1 - 18, y1 - 2)],
                 fill=(255, 80, 70))


def scene_cop(draw, box):
    x0, y0, x1, y1 = box
    bh = y1 - y0
    vgrad(draw, box, (232, 196, 120), (196, 140, 60))
    # globe (radius clamped to the scene box)
    cx, cy, r = x0 + 48, y0 + bh // 2, min(30, bh // 2 - 2)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(52, 110, 160))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255), width=2)
    draw.ellipse([cx - r + 4, cy - r + 4, cx - 2, cy - 2], fill=(64, 160, 90))
    draw.ellipse([cx + 2, cy + 2, cx + r - 3, cy + r - 3], fill=(64, 160, 90))
    # thermometer
    tx = x0 + 108
    draw.rectangle([tx, y0 + 4, tx + 12, y1 - 8], fill=(255, 255, 255))
    draw.rectangle([tx, y0 + 4, tx + 12, y0 + 10], fill=(176, 30, 40))
    draw.ellipse([tx - 4, y1 - 14, tx + 16, y1 - 2], fill=(176, 30, 40))
    draw.ellipse([tx - 4, y1 - 14, tx + 16, y1 - 2], outline=(255, 255, 255), width=2)
    # clock: no deal yet
    ccx, ccy, cr = x1 - 28, y0 + bh // 2, min(17, bh // 2 - 2)
    draw.ellipse([ccx - cr, ccy - cr, ccx + cr, ccy + cr], fill=(255, 255, 255))
    draw.ellipse([ccx - cr, ccy - cr, ccx + cr, ccy + cr], outline=INK, width=2)
    draw.line([(ccx, ccy), (ccx, ccy - 15)], fill=INK, width=3)
    draw.line([(ccx, ccy), (ccx + 11, ccy + 4)], fill=INK, width=3)


def scene_mercury(draw, box):
    x0, y0, x1, y1 = box
    bh = y1 - y0
    draw.rectangle(box, fill=(8, 8, 16))
    speckle(draw, box, 30, (255, 255, 255), 1)
    cx, cy, r = x0 + 48, y0 + bh // 2, min(17, bh // 2 - 2)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(168, 158, 142))
    for ox, oy, orr in [(-8, -5, 4), (6, 4, 5), (1, -10, 3), (-3, 9, 3)]:
        draw.ellipse([cx + ox - orr, cy + oy - orr, cx + ox + orr, cy + oy + orr],
                     fill=(128, 118, 104))
    # probe with panels on an approach path
    px, py = x1 - 52, y0 + 10
    draw.line([(x0 + 84, y1 - 8), (px, py)], fill=(255, 214, 110), width=2)
    draw.rectangle([px - 16, py - 5, px + 16, py + 5], fill=(220, 220, 220))
    draw.rectangle([px - 30, py - 3, px - 16, py + 3], fill=(52, 110, 200))
    draw.rectangle([px + 16, py - 3, px + 30, py + 3], fill=(52, 110, 200))
    draw.polygon([(px + 16, py - 5), (px + 26, py), (px + 16, py + 5)],
                 fill=(255, 214, 110))


def scene_brussels(draw, box):
    x0, y0, x1, y1 = box
    bh = y1 - y0
    vgrad(draw, box, (36, 66, 140), (20, 40, 96))
    # circle of EU stars (radius clamped to the scene box)
    cx, cy, r = x0 + 46, y0 + bh // 2, min(26, bh // 2 - 2)
    for k in range(12):
        ang = k * math.pi / 6
        sx = cx + int(r * math.cos(ang))
        sy = cy + int(r * math.sin(ang))
        draw.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], fill=(255, 214, 80))
    draw.rectangle([cx - 8, cy - 10, cx + 8, cy + 10], fill=(255, 214, 80))
    # Union Jack corner block
    jx, jy, jw, jh = x1 - 52, y0 + 4, 44, 20
    draw.rectangle([jx, jy, jx + jw, jy + jh], fill=(20, 40, 96))
    draw.rectangle([jx, jy, jx + jw, jy + jh], outline=(255, 255, 255), width=2)
    draw.line([(jx, jy), (jx + jw, jy + jh)], fill=(255, 255, 255), width=3)
    draw.line([(jx + jw, jy), (jx, jy + jh)], fill=(255, 255, 255), width=3)
    draw.line([(jx + jw // 2, jy), (jx + jw // 2, jy + jh)], fill=(200, 30, 40), width=5)
    draw.line([(jx, jy + jh // 2), (jx + jw, jy + jh // 2)], fill=(200, 30, 40), width=5)
    # summit table + two flags
    draw.rectangle([x0 + 10, y1 - 12, x1 - 10, y1 - 5], fill=(120, 84, 48))
    draw.line([(x0 + 100, y1 - 12), (x0 + 100, y1 - 26)], fill=(255, 255, 255), width=2)
    draw.rectangle([x0 + 100, y1 - 26, x0 + 118, y1 - 16], fill=(52, 110, 200))
    draw.line([(x0 + 128, y1 - 12), (x0 + 128, y1 - 26)], fill=(255, 255, 255), width=2)
    draw.rectangle([x0 + 128, y1 - 26, x0 + 146, y1 - 16], fill=(200, 30, 40))


def scene_tokyo(draw, box):
    x0, y0, x1, y1 = box
    bh = y1 - y0
    draw.rectangle(box, fill=(250, 246, 232))
    # rising CPI bars, last one red (heights clamped to the scene box)
    base = y1 - 8
    vals = [7, 10, 14, 13, 18]
    vals = [min(v, bh - 12) for v in vals]
    bw = 22
    for i, v in enumerate(vals):
        bx = x0 + 14 + i * (bw + 8)
        col = (176, 30, 40) if i == len(vals) - 1 else (52, 90, 150)
        draw.rectangle([bx, base - v, bx + bw, base], fill=col)
    draw.line([(x0 + 8, y0 + 2), (x1 - 8, y0 + 2)], fill=(176, 30, 40), width=2)
    # big yen disc
    cx, cy, r = x1 - 30, y0 + 12, 11
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(176, 30, 40))
    draw.text((cx - 11, cy - 13), "\u00a5", font=SANS_B(22), fill=WHITE)


def scene_beijing(draw, box):
    x0, y0, x1, y1 = box
    bh = y1 - y0
    vgrad(draw, box, (150, 24, 32), (110, 14, 22))
    # bank: pediment + columns
    bx0, bx1 = x0 + 26, x1 - 26
    draw.polygon([(bx0, y0 + 10), ((bx0 + bx1) // 2, y0 + 2), (bx1, y0 + 10)],
                 fill=(212, 164, 60))
    draw.rectangle([bx0, y0 + 10, bx1, y0 + 13], fill=(212, 164, 60))
    for i in range(4):
        cx = bx0 + 14 + i * ((bx1 - bx0 - 28) // 3)
        draw.rectangle([cx - 5, y0 + 14, cx + 5, y1 - 8], fill=(240, 220, 170))
    draw.rectangle([bx0, y1 - 8, bx1, y1 - 4], fill=(212, 164, 60))
    # gold coins
    for i, (ox, oy) in enumerate([(x0 + 12, y1 - 16), (x0 + 24, y1 - 18)]):
        draw.ellipse([ox, oy, ox + 11, oy + 11], fill=(255, 214, 80),
                     outline=(160, 110, 20), width=2)


def scene_cricket(draw, box):
    x0, y0, x1, y1 = box
    bh = y1 - y0
    vgrad(draw, box, (46, 140, 74), (24, 96, 50))
    # pitch strip
    draw.rectangle([x0 + 52, y0 + 4, x0 + 132, y1 - 4], fill=(214, 190, 140))
    # stumps
    for sx in (x0 + 62, x0 + 68, x0 + 74):
        draw.line([(sx, y0 + 8), (sx, y0 + 18)], fill=(255, 240, 180), width=3)
    draw.line([(x0 + 62, y0 + 7), (x0 + 74, y0 + 7)], fill=(255, 240, 180), width=2)
    # bat + red ball
    draw.polygon([(x0 + 96, y0 + 22), (x0 + 114, y0 + 8), (x0 + 119, y0 + 13),
                  (x0 + 101, y0 + 27)], fill=(232, 200, 140))
    draw.line([(x0 + 114, y0 + 8), (x0 + 124, y0 + 2)], fill=(160, 110, 60), width=4)
    draw.ellipse([x1 - 30, y1 - 18, x1 - 18, y1 - 6], fill=(176, 30, 40))
    draw.ellipse([x1 - 30, y1 - 18, x1 - 18, y1 - 6], outline=WHITE, width=2)
    # scoreboard
    draw.rectangle([x0 + 8, y1 - 14, x0 + 58, y1 - 3], fill=(16, 24, 16))
    draw.text((x0 + 12, y1 - 13), "NZ 368", font=SANS_B(10), fill=(255, 220, 90))


def scene_rome(draw, box):
    x0, y0, x1, y1 = box
    bh = y1 - y0
    vgrad(draw, box, (240, 214, 170), (214, 170, 120))
    # crowd silhouettes
    for i in range(9):
        cx = x0 + 14 + i * 18
        draw.ellipse([cx - 5, y1 - 18, cx + 5, y1 - 10], fill=(40, 30, 24))
        draw.polygon([(cx - 8, y1 - 4), (cx - 7, y1 - 11), (cx + 7, y1 - 11),
                      (cx + 8, y1 - 4)], fill=(40, 30, 24))
    # placards (kept inside the scene box)
    for px, lab in [(x0 + 34, "CGIL"), (x0 + 100, "24H")]:
        draw.line([(px, y0 + 14), (px, y1 - 16)], fill=(90, 60, 30), width=3)
        draw.rectangle([px - 15, y0 + 2, px + 15, y0 + 13], fill=(176, 30, 40))
        draw.text((px - 11, y0 + 3), lab, font=SANS_B(9), fill=WHITE)
    # sun
    draw.ellipse([x1 - 30, y0 + 4, x1 - 16, y0 + 18], fill=(255, 190, 60))


def scene_raoni(draw, box):
    x0, y0, x1, y1 = box
    bh = y1 - y0
    vgrad(draw, box, (120, 190, 120), (40, 110, 60))
    # trees (heights clamped to the scene box)
    for tx, th in [(x0 + 24, 16), (x0 + 58, 20), (x0 + 150, 18)]:
        th = min(th, bh - 12)
        draw.polygon([(tx - 13, y1 - 12), (tx, y1 - 12 - th), (tx + 13, y1 - 12)],
                     fill=(18, 80, 40))
        draw.rectangle([tx - 3, y1 - 12, tx + 3, y1 - 6], fill=(90, 60, 30))
    # hut
    hx = x0 + 96
    draw.polygon([(hx - 22, y1 - 14), (hx, y1 - 28), (hx + 22, y1 - 14)],
                 fill=(160, 110, 50))
    draw.rectangle([hx - 17, y1 - 14, hx + 17, y1 - 6], fill=(120, 80, 40))
    draw.rectangle([hx - 4, y1 - 12, hx + 4, y1 - 6], fill=(60, 40, 20))
    # sun + birds
    draw.ellipse([x1 - 28, y0 + 4, x1 - 14, y0 + 18], fill=(255, 220, 110))
    for bx, by in [(x0 + 120, y0 + 10), (x0 + 134, y0 + 15)]:
        draw.arc([bx - 5, by - 3, bx + 5, by + 3], 200, 340, fill=INK, width=2)


def scene_health(draw, box):
    x0, y0, x1, y1 = box
    bh = y1 - y0
    vgrad(draw, box, (210, 232, 244), (160, 200, 226))
    # test tubes
    for i, (tx, lvl, col) in enumerate([(x0 + 22, 10, (52, 140, 90)),
                                        (x0 + 58, 14, (176, 30, 40)),
                                        (x0 + 94, 7, (52, 90, 180))]):
        draw.rectangle([tx, y0 + 4, tx + 22, y1 - 4], outline=INK, width=2)
        draw.rectangle([tx + 2, y1 - 5 - lvl, tx + 20, y1 - 6], fill=col)
        draw.ellipse([tx + 4, y1 - 8 - lvl, tx + 18, y1 - 4 - lvl], fill=col)
    # cell / pill shapes
    draw.ellipse([x1 - 48, y0 + 4, x1 - 18, y0 + 24], fill=(255, 255, 255),
                 outline=(176, 30, 40), width=3)
    draw.ellipse([x1 - 41, y0 + 9, x1 - 25, y0 + 19], fill=(176, 30, 40))
    draw.line([(x1 - 48, y0 + 26), (x1 - 18, y0 + 28)], fill=(52, 90, 180), width=3)


def scene_tennis(draw, box):
    x0, y0, x1, y1 = box
    vgrad(draw, box, (66, 150, 90), (36, 110, 64))
    # court lines
    draw.rectangle([x0 + 8, y0 + 8, x1 - 8, y1 - 8], outline=WHITE, width=2)
    draw.line([(x0 + 8, (y0 + y1) // 2), (x1 - 8, (y0 + y1) // 2)],
              fill=WHITE, width=2)
    # net
    midx = (x0 + x1) // 2
    draw.rectangle([midx - 2, y0 + 8, midx + 2, y1 - 8], fill=(20, 30, 24))
    for ny in range(y0 + 12, y1 - 10, 8):
        draw.line([(midx - 2, ny), (midx + 2, ny)], fill=(200, 200, 200), width=1)
    # ball + racket
    draw.ellipse([x0 + 26, y0 + 10, x0 + 40, y0 + 24], fill=(214, 232, 60))
    draw.ellipse([x0 + 26, y0 + 10, x0 + 40, y0 + 24], outline=WHITE, width=2)
    rx, ry = x1 - 40, y1 - 12
    draw.ellipse([rx - 10, ry - 12, rx + 10, ry + 6], outline=(240, 220, 170), width=3)
    draw.line([(rx, ry + 6), (rx + 12, ry + 14)], fill=(160, 110, 60), width=4)


SCENES = {
    "kyiv": scene_kyiv, "akvan": scene_akvan, "markets": scene_markets,
    "cop": scene_cop, "mercury": scene_mercury, "brussels": scene_brussels,
    "tokyo": scene_tokyo, "beijing": scene_beijing, "cricket": scene_cricket,
    "rome": scene_rome, "raoni": scene_raoni, "health": scene_health,
    "tennis": scene_tennis,
}

# ---------------------------------------------------------------- layout

def draw_masthead(draw, y):
    draw.text((MARGIN, y), "THE WORLD IN ONE DAY",
              font=SANS_B(15), fill=RED)
    right = "36 STORIES \u00b7 7 REGIONS \u00b7 EVERY ONE DATED FRIDAY 20 NOVEMBER 2026"
    rw = draw.textlength(right, font=SANS_B(12))
    draw.text((W - MARGIN - rw, y + 2), right, font=SANS_B(12), fill=INK)
    y += 22
    draw.text((MARGIN, y), "Friday 20 November 2026",
              font=SERIF_B(54), fill=INK)
    y += 60
    sub = ("Cyclone Akvan strikes India \u2022 Ballistic missiles hit Kyiv "
           "\u2022 COP31 deadlocked on final day \u2022 Asian AI sell-off")
    draw.text((MARGIN, y), sub, font=SERIF_I(17), fill=INK_SOFT)
    y += 22
    hline(draw, MARGIN, W - MARGIN, y, INK, 3)
    return y + 6


def draw_stats(draw, y):
    cell = CONTENT // 6
    top = y
    for i, (num, cap) in enumerate(STATS):
        x = MARGIN + i * cell
        if i:
            draw.line([(x - 5, y + 2), (x - 5, y + 40)], fill=GREY, width=1)
        draw.text((x, y), num, font=SANS_B(26), fill=RED)
        para(draw, x, y + 28, cap, SANS(11), INK, cell - 14, 12, max_lines=2)
    return top + 50


def draw_regions(draw, y):
    x = MARGIN
    total = sum(n for _, n, _ in REGIONS)
    for name, n, col in REGIONS:
        w = int(CONTENT * n / total)
        draw.rectangle([x, y, x + w - 2, y + 18], fill=col)
        label = "%s %d" % (name, n)
        fnt = SANS_B(10)
        while draw.textlength(label, font=fnt) > w - 6 and fnt.size > 8:
            fnt = SANS_B(fnt.size - 1)
        lw = draw.textlength(label, font=fnt)
        lx = x + max(2, (w - 2 - lw) // 2)
        draw.text((lx, y + 4), label, font=fnt, fill=WHITE)
        x += w
    return y + 26


def draw_utc(draw, y):
    draw.text((MARGIN, y), "THE DAY IN UTC", font=SANS_B(11), fill=RED)
    draw.text((MARGIN + 110, y), "overnight \u2192 evening, Friday 20 November",
              font=SANS(11), fill=INK_SOFT)
    y += 15
    cell = CONTENT // 5
    for i, (when, what) in enumerate(UTC_STRIP):
        x = MARGIN + i * cell
        draw.rectangle([x, y, x + cell - 6, y + 30], fill=PAPER_DK)
        draw.rectangle([x, y, x + 4, y + 30], fill=RED)
        draw.text((x + 10, y + 3), when, font=SANS_B(10), fill=RED)
        para(draw, x + 10, y + 15, what, SANS(10), INK, cell - 18, 12,
             max_lines=1)
    return y + 38


def draw_lead(draw, x, y, w, story):
    art_h = 104
    box = (x, y, x + w, y + art_h)
    draw.rectangle(box, fill=NAVY)
    draw.rectangle(box, outline=INK, width=1)
    by = banner(draw, box, story["banner"], SANS_B(21), bg=RED)
    SCENES[story["scene"]](draw, (x, by, x + w, y + art_h))
    # source chip bottom-left of the art
    chip(draw, x + 6, y + art_h - 24, "SOURCE: " + story["src"], SANS_B(9))
    yy = y + art_h + 6
    kicker_line(draw, x, yy, story["num"], story["place"], story["beat"],
                story["src"], w)
    yy += 15
    yy = para(draw, x, yy, story["head"], SANS_B(18), INK, w, 20, max_lines=2)
    yy = para(draw, x, yy + 2, story["body"], SANS(12), INK, w, 13,
              max_lines=3)
    return yy


def draw_mid(draw, x, y, w, story):
    art_h = 54
    box = (x, y, x + w, y + art_h)
    draw.rectangle(box, fill=NAVY)
    draw.rectangle(box, outline=INK, width=1)
    by = banner(draw, box, story["banner"], SANS_B(14), bg=INK, pad=5)
    SCENES[story["scene"]](draw, (x, by, x + w, y + art_h))
    # red fact bar directly under the art; source rides at its right end
    fy = y + art_h
    draw.rectangle([x, fy, x + w, fy + 16], fill=RED)
    draw.text((x + 5, fy + 3), story["fact"], font=SANS_B(11), fill=WHITE)
    sw = draw.textlength(story["src"], font=SANS_B(9))
    draw.text((x + w - sw - 5, fy + 4), story["src"], font=SANS_B(9),
              fill=(255, 220, 220))
    yy = fy + 20
    draw.text((x, yy), "%s \u00b7 %s \u2014 %s" % (story["num"], story["place"],
              story["beat"]), font=SANS_B(11), fill=RED)
    yy += 14
    yy = para(draw, x, yy, story["head"], SANS_B(13), INK, w, 14, max_lines=2)
    yy = para(draw, x, yy + 1, story["body"], SANS(11), INK, w, 12,
              max_lines=2)
    return yy

# ---------------------------------------------------------------- bottom

CONTINENTS = [
    # North America
    [(10, 34), (66, 22), (96, 36), (82, 58), (58, 80), (30, 72), (12, 54)],
    # South America
    [(80, 84), (106, 80), (114, 104), (98, 130), (82, 110)],
    # Europe
    [(140, 18), (176, 16), (182, 36), (162, 44), (142, 36)],
    # Africa
    [(140, 58), (178, 56), (188, 82), (170, 108), (148, 94), (138, 72)],
    # Asia
    [(182, 20), (266, 16), (286, 44), (262, 70), (226, 80), (202, 62), (184, 42)],
    # Oceania
    [(256, 104), (286, 100), (290, 122), (264, 128)],
]

# (story number, x, y) inside the 300x150 map box
PINS = [
    (1, 172, 30), (2, 226, 76), (3, 254, 52), (4, 168, 58),
    (6, 136, 26), (7, 260, 50), (8, 240, 56), (9, 274, 126),
    (10, 144, 50), (11, 90, 92), (12, 128, 40), (13, 156, 32),
    (14, 62, 70), (15, 192, 70),
]


def draw_map(draw, x, y, w, h):
    draw.rectangle([x, y, x + w, y + h], fill=(188, 214, 224))
    draw.rectangle([x, y, x + w, y + h], outline=INK, width=1)
    for poly in CONTINENTS:
        pts = [(x + px, y + py) for px, py in poly]
        draw.polygon(pts, fill=(222, 206, 170), outline=(150, 138, 112))
    for num, px, py in PINS:
        cx, cy = x + px, y + py
        draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=RED)
        draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], outline=WHITE, width=1)
        lab = str(num)
        tw = draw.textlength(lab, font=SANS_B(9))
        draw.text((cx - tw / 2, cy - 6), lab, font=SANS_B(9), fill=WHITE)


def briefs_text(items):
    parts = []
    for num, place, text, src in items:
        parts.append("%s %s \u2014 %s (%s)" % (num, place, text, src))
    return "  ".join(parts)


def draw_bottom(draw, y):
    """Map + briefs + date check + footer. Returns final y."""
    draw.text((MARGIN, y), "WHERE IT HAPPENED", font=SANS_B(13), fill=INK)
    bx = MARGIN + 300
    draw.text((bx, y), "ALSO ON FRIDAY 20 NOVEMBER \u2014 23 MORE STORIES",
              font=SANS_B(13), fill=RED)
    y += 18
    map_h = 120
    draw_map(draw, MARGIN, y, 288, map_h)
    cap_y = y + map_h + 4
    draw.text((MARGIN, cap_y),
              "1\u20133 lead \u00b7 4\u201313 features \u00b7 5 Mercury: no pin.",
              font=SANS(10), fill=INK_SOFT)
    col_w = (CONTENT - 300 - 12) // 2
    left_items = BRIEFS[:12]
    right_items = BRIEFS[12:]
    para(draw, bx, y, briefs_text(left_items), SANS(10), INK, col_w, 12)
    para(draw, bx + col_w + 12, y, briefs_text(right_items), SANS(10), INK,
         col_w, 12)
    y = y + map_h + 24
    # DATE CHECK box
    draw.rectangle([MARGIN, y, W - MARGIN, y + 44], outline=RED, width=2)
    draw.rectangle([MARGIN, y, MARGIN + 92, y + 44], fill=RED)
    draw.text((MARGIN + 10, y + 6), "DATE", font=SANS_B(15), fill=WHITE)
    draw.text((MARGIN + 10, y + 23), "CHECK", font=SANS_B(15), fill=WHITE)
    para(draw, MARGIN + 102, y + 4, DATE_CHECK, SANS(11), INK,
         CONTENT - 112, 13, max_lines=3)
    y += 52
    fw = draw.textlength(FOOTER, font=SANS(10))
    draw.text(((W - fw) / 2, y), FOOTER, font=SANS(10), fill=INK_SOFT)
    return y + 14


# ---------------------------------------------------------------- compose

def build(out_path):
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)
    # paper grain
    speckle(draw, (0, 0, W, H), 900, (210, 198, 168), 1)
    y = 12
    y = draw_masthead(draw, y)
    y = draw_stats(draw, y)
    y = draw_regions(draw, y)
    y = draw_utc(draw, y)
    # three leads
    lead_w = (CONTENT - 2 * 13) // 3
    ends = []
    for i, story in enumerate(LEADS):
        ends.append(draw_lead(draw, MARGIN + i * (lead_w + 13), y, lead_w,
                              story))
    y = max(ends) + 10
    # ten mid tiles, two rows of five
    mid_w = (CONTENT - 4 * 10) // 5
    for row in range(2):
        ends = []
        for col in range(5):
            story = MIDS[row * 5 + col]
            ends.append(draw_mid(draw, MARGIN + col * (mid_w + 10), y,
                                 mid_w, story))
        y = max(ends) + 10
    y = draw_bottom(draw, y)
    print("final y:", y, "of", H)
    img.save(out_path, "PNG", optimize=True)
    return out_path


def main(argv):
    out = argv[1] if len(argv) > 1 else "entry.png"
    build(out)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv)
