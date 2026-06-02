"""Block-art battle sprites and effects for the graphical TUI canvas."""
from __future__ import annotations


HERO_BLOCK_SPRITES: dict[str, dict[str, list[str]]] = {
    "hero_shadow_apprentice": {
        "idle": ["  ▄██▄  ", " ▐▓c▓▌ ", "  ▟██▙  ", "  ░▀▀░  "],
        "attack": ["  ▄██▄  ", " ▐▓c▓██", "  ▟██▙ ", "  ░▀▀░ "],
        "skill": [" ░▄██▄░ ", " ▐▓c▓██", "  ▟██▙ ", " ░▀▀▀░ "],
        "defend": ["  ▄██▄  ", " ▐▓c▓▌ ", " ▐████▌ ", "  ░▀▀░  "],
        "hit": ["  ▄██▄  ", " ▐▓x▓  ", "  ▟█▙   ", "  ░▀░   "],
        "low": ["  ▄██▄  ", " ▐▒c▒▌ ", "  ▟▙   ", "  ░░   "],
        "victory": [" ▄██▄░  ", " ▐▓c▓▌█", "  ▟██▙ ", " ░▀▀▀░ "],
        "defeat": ["  ▄▒▒▄  ", " ▐▒x   ", "  ▟▙   ", "  ░    "],
    },
    "hero_ash_guardian": {
        "idle": ["  ▄██▄  ", " ▐████▌ ", " ▐████▌ ", "  ▀  ▀  "],
        "attack": ["  ▄██▄  ", " ▐██████", " ▐████▌ ", "  ▀  ▀  "],
        "skill": [" ▄████▄ ", " ▐████▌ ", " ▐████▌ ", "  ▀██▀  "],
        "defend": [" ▄████▄ ", " ██████ ", " ▐████▌ ", "  ▀  ▀  "],
        "hit": ["  ▄██▄  ", " ▐██▒▌ ", " ▐█▒█▌ ", "  ▀  ▀  "],
        "low": ["  ▄▒▒▄  ", " ▐███▌ ", " ▐█▒█▌ ", "  ▀  ▀  "],
        "victory": [" ▄████▄ ", " ██████ ", " ▐████▌ ", "  ▀██▀  "],
        "defeat": ["  ▄▒▒   ", " ▐██   ", " ▐▒    ", "  ▀    "],
    },
    "hero_broken_string_hunter": {
        "idle": ["  ▄██   ", " ▐▓▓▌  ", "  ▟▙━━ ", "  ▀ ▀  "],
        "attack": ["  ▄██   ", " ▐▓▓▌━━", "  ▟▙━━ ", "  ▀ ▀  "],
        "skill": [" ░▄██░  ", " ▐▓▓▌━━", "  ▟▙▓▓ ", "  ▀ ▀  "],
        "defend": ["  ▄██   ", " ▐▓▓▌  ", "  ▟▙   ", " ░▀ ▀░ "],
        "hit": ["  ▄▒▒   ", " ▐▓x   ", "  ▟▙   ", "  ▀    "],
        "low": ["  ▄██   ", " ▐▒▒   ", "  ▟▙━  ", "  ▀    "],
        "victory": ["  ▄██░  ", " ▐▓▓▌━━", "  ▟▙━━ ", " ░▀ ▀  "],
        "defeat": ["  ▄▒    ", " ▐x    ", "  ▟    ", "  ▀    "],
    },
    "hero_mire_oracle": {
        "idle": ["  ▄██▄  ", " ▐▒v▒▌ ", " ░▟▓▙░ ", "  ░▀░  "],
        "attack": ["  ▄██▄  ", " ▐▒v▒██", " ░▟▓▙  ", "  ░▀░  "],
        "skill": [" ░▄██▄░ ", " ▐▒v▒▓▓", " ░▟▓▙░ ", " ░░▀░░ "],
        "defend": ["  ▄██▄  ", " ▐▒v▒▌ ", " ░▓▓▓░ ", " ░▀▀▀░ "],
        "hit": ["  ▄▒▒▄  ", " ▐▒x▒  ", "  ▟▓   ", "  ░▀   "],
        "low": ["  ▄██▄  ", " ▐▒v▒  ", " ░▟▒   ", " ░░    "],
        "victory": [" ░▄██▄░ ", " ▐▒v▒▓ ", " ░▟▓▙░ ", " ░▀▀▀░ "],
        "defeat": ["  ▄▒▒   ", " ▐▒x   ", "  ▟    ", " ░     "],
    },
    "hero_gravewright": {
        "idle": [" ▄████▄ ", " ▐▓n▓▌ ", " ▐███▌ ", "  ▀ ▀  "],
        "attack": [" ▄████▄ ", " ▐▓n▓██", " ▐███▌ ", "  ▀ ▀  "],
        "skill": [" ▄████▄ ", " ▐▓n▓▓▓", " ▐███▌ ", " ░▀ ▀░ "],
        "defend": [" ▄████▄ ", " █▓n▓█ ", " ▐███▌ ", "  ▀ ▀  "],
        "hit": [" ▄██▒▄ ", " ▐▓x▓  ", " ▐█▒▌  ", "  ▀    "],
        "low": [" ▄██▒▄ ", " ▐▓n   ", " ▐█▒   ", "  ▀    "],
        "victory": [" ▄████▄ ", " ▐▓n▓▌█", " ▐███▌ ", " ░▀▀▀░ "],
        "defeat": [" ▄▒▒▒   ", " ▐▓x   ", " ▐▒    ", "  ▀    "],
    },
    "hero_echo_exile": {
        "idle": ["  ▄██▄  ", " ▐▓o▓▌ ", "  ▟██▙ ", "  ▀  ▀ "],
        "attack": ["  ▄██▄▓ ", " ▐▓o▓██", "  ▟██▙ ", "  ▀  ▀ "],
        "skill": [" ░▄██▄░ ", "▓▐▓o▓▌▓", "  ▟██▙ ", " ░▀  ▀░"],
        "defend": ["  ▄██▄  ", "▓▐▓o▓▌▓", "  ▟██▙ ", "  ▀  ▀ "],
        "hit": ["  ▄▒▒▄  ", " ▐▓x   ", "  ▟█▙  ", "  ▀    "],
        "low": ["  ▄██▄  ", " ▐▒o   ", "  ▟▙   ", "  ▀    "],
        "victory": [" ░▄██▄░ ", "▓▐▓o▓▌▓", "  ▟██▙ ", " ░▀▀▀░ "],
        "defeat": ["  ▄▒▒   ", " ▐▒x   ", "  ▟    ", "  ▀    "],
    },
}


ENEMY_BLOCK_SPRITES: dict[str, dict[str, list[str]]] = {
    "c": {
        "idle": ["  ▄▒▄   ", " ▐▒c▒▌ ", "  ▟▒▙  ", "  ░▀░  "],
        "attack": ["  ▄▒▄   ", " ▐▒c▒██", "  ▟▒▙  ", "  ░▀░  "],
        "skill": [" ░▄▒▄░  ", " ▐▒c▒▓ ", "  ▟▒▙  ", " ░░▀░░ "],
        "hit": ["  ▄▒▄   ", " ▐▒x▒  ", "  ▟▒   ", "  ░▀   "],
        "break": ["  ▄▒▄   ", " ▐▒x▒! ", "  ▟▒   ", " ░░    "],
        "low": ["  ▄▒    ", " ▐▒c   ", "  ▟    ", "  ░    "],
        "death": ["        ", "  ░░░   ", " ░▒░    ", "        "],
    },
    "k": {
        "idle": [" ░▄▓▄░  ", " ▐▓k▓▌ ", " ░▟▓▙░ ", "  ░▀░  "],
        "attack": [" ░▄▓▄░  ", " ▐▓k▓██", " ░▟▓▙  ", "  ░▀░  "],
        "skill": [" ░▄█▄░  ", "▓▐▓k▓▌▓", " ░▟▓▙░ ", " ░▀▀▀░ "],
        "hit": [" ░▄▓▄░  ", " ▐▓x▓  ", "  ▟▓▙  ", "  ░▀   "],
        "break": [" ░▄▓▄░  ", "▓▐▓x▓  ", "  ▟▒▙  ", " ░░    "],
        "low": [" ░▄▒▄░  ", " ▐▒k▒  ", "  ▟▒   ", "  ░    "],
        "death": ["   ░    ", "  ░▒░   ", " ░░     ", "        "],
    },
}

ENEMY_BLOCK_SPRITES.update(
    {
        "C": ENEMY_BLOCK_SPRITES["c"],
        "K": ENEMY_BLOCK_SPRITES["k"],
        "B": ENEMY_BLOCK_SPRITES["k"],
        "r": ENEMY_BLOCK_SPRITES["c"],
        "S": ENEMY_BLOCK_SPRITES["c"],
        "w": ENEMY_BLOCK_SPRITES["k"],
        "G": ENEMY_BLOCK_SPRITES["k"],
    }
)


EFFECT_BLOCK_PATTERNS: dict[str, tuple[str, str, str]] = {
    "wait": ("░░░", "waiting for first echo", "░░░"),
    "strike": ("░░▓▓██>", "STRIKE", "░░▓▓██>"),
    "seal": ("░▒▓▓██>", "SEAL", "▓▓ SLN ▓▓"),
    "shadow": ("░░▓███>", "SHADOW", "▒▒ CRP ▒▒"),
    "fire": ("░▓████>", "FIRE", "██ BURN ██"),
    "poison": ("::::▒▒>", "VENOM", "▒▒ POISON ▒▒"),
    "guard": ("<████>", "GUARD ONLINE", "<████>"),
    "observe": ("░░▒▒░░", "SCAN FIELD", "░░▒▒░░"),
    "counter": ("▓▓ WINDOW ▓▓", "COUNTER CLOCK", "▓▓ ANSWER ▓▓"),
    "break": ("░░▓▓░░", "CHANT BROKEN", "▓▓ BRK ▓▓"),
    "chant": ("<████▓▓░", "CHANT RELEASE", "<████▓▓░"),
    "enemy_strike": ("<██▓▓░", "STRIKE", "<██▓▓░"),
    "climax": ("████ CLIMAX ████", "IMPACT", "████ RUPTURE ████"),
    "skill": ("░░▓▓██>", "SKILL", "░░▓▓██>"),
}


def block_effect_rows(effect_key: str, label: str, width: int) -> list[str]:
    """Return a centered 3-line block projectile with a text payload."""
    top, fallback_label, bottom = EFFECT_BLOCK_PATTERNS.get(
        effect_key,
        EFFECT_BLOCK_PATTERNS["skill"],
    )
    payload = label or fallback_label
    inner_width = max(12, width)
    return [
        _center_block(top, inner_width),
        _center_block(payload, inner_width),
        _center_block(bottom, inner_width),
    ]


def _center_block(text: str, width: int) -> str:
    if len(text) >= width:
        return text[:width]
    left = (width - len(text)) // 2
    return " " * left + text


def hero_block_sprite(hero_id: str, pose: str) -> list[str]:
    sprites = HERO_BLOCK_SPRITES.get(hero_id, HERO_BLOCK_SPRITES["hero_shadow_apprentice"])
    return sprites.get(pose) or sprites.get("skill") or sprites["idle"]


def enemy_block_sprite(glyph: str, pose: str) -> list[str]:
    sprites = ENEMY_BLOCK_SPRITES.get(glyph, ENEMY_BLOCK_SPRITES["c"])
    return sprites.get(pose) or sprites.get("skill") or sprites["idle"]
