"""Design tokens for the ARIA Dev Console."""
from __future__ import annotations

TOKENS: dict[str, str] = {
    "bg_primary":    "#0f1117",
    "bg_surface":    "#1a1d27",
    "bg_code":       "#12151f",
    "accent_blue":   "#4f8ef7",
    "accent_green":  "#22c55e",
    "accent_amber":  "#f59e0b",
    "accent_red":    "#ef4444",
    "accent_purple": "#a855f7",
    "text_primary":  "#e2e8f0",
    "text_muted":    "#64748b",
    "font_mono":     "JetBrains Mono, Fira Code, monospace",
    "font_sans":     "Inter, system-ui, sans-serif",
}

STATUS_COLORS: dict[str, str] = {
    "planning":   TOKENS["accent_blue"],
    "building":   TOKENS["accent_blue"],
    "testing":    TOKENS["accent_amber"],
    "fixing":     TOKENS["accent_amber"],
    "done":       TOKENS["accent_green"],
    "failed":     TOKENS["accent_red"],
    "replanning": TOKENS["accent_purple"],
}
