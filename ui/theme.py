# ─── Palette ──────────────────────────────────────────────────────────────────
BG       = "#08080c"
BG2      = "#0f0f14"
BG3      = "#16161e"
CARD     = "#13131a"
BORDER   = "#1f1f2e"
BORDER2  = "#2a2a3a"
ACCENT   = "#e8365d"
ACCENT_D = "#c02244"
TEXT     = "#f0eeff"
TEXT2    = "#8888aa"
TEXT3    = "#44445a"
SUCCESS  = "#22d3a0"

# ─── Stem metadata ────────────────────────────────────────────────────────────
STEM_COLORS = {
    "vocals": "#e8365d",
    "drums":  "#f59e0b",
    "bass":   "#3b82f6",
    "other":  "#a855f7",
}
STEM_ICONS = {
    "vocals": "🎤",
    "drums":  "🥁",
    "bass":   "🎸",
    "other":  "🎹",
}
STEM_LABELS = {
    "vocals": "VOCALS",
    "drums":  "DRUMS",
    "bass":   "BASS",
    "other":  "OTHER",
}

# ─── Fonts ────────────────────────────────────────────────────────────────────
FONT_LABEL = ("Segoe UI", 8, "bold")
FONT_SMALL = ("Segoe UI", 8)
FONT_MONO  = ("Consolas", 8)
FONT_TIME  = ("Consolas", 9)

# ─── Helpers ──────────────────────────────────────────────────────────────────
def hex_to_rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)