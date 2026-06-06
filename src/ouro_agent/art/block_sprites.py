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
    "C": {
        "idle": [" ▄▒█▄  ", "▐▒C▒█▌ ", " ▟▒▒▙  ", " ░▚▞░  "],
        "attack": [" ▄▒█▄  ", "▐▒C▒██", " ▟▒▒▙  ", " ░▚▞░  "],
        "skill": ["░▄▒█▄░ ", "▐▒C▒█▓", " ▟▒▒▙░ ", "░▚▞░░ "],
        "hit": [" ▄▒█▄  ", "▐▒x▒█ ", " ▟▒▙   ", " ░▚░   "],
        "break": [" ▄▒█▄  ", "▐▒x▒! ", " ▟▒    ", " ░░    "],
        "low": [" ▄▒    ", "▐▒C▒  ", " ▟▒    ", " ░     "],
        "death": ["        ", " ░█░   ", " ░▒░   ", "        "],
    },
    "K": {
        "idle": [" ░▄█▄░ ", "▓▐▓K▓▌▓", " ░▟▓▙░ ", " ░▀█▀░ "],
        "attack": [" ░▄█▄░ ", "▓▐▓K▓██", " ░▟▓▙  ", " ░▀█▀░ "],
        "skill": ["▓▄███▄▓", "▓▐▓K▓▌▓", " ░▟▓▙░ ", " ▓▀▀▀▓ "],
        "hit": [" ░▄█▄░ ", "▓▐▓x▓  ", "  ▟▓▙░ ", " ░▀░   "],
        "break": [" ░▄█▄░ ", "▓▐▓x▓! ", "  ▟▒▙  ", " ░░    "],
        "low": [" ░▄▒▄░ ", " ▐▒K▒  ", "  ▟▒   ", " ░     "],
        "death": ["   ░   ", " ░▓░   ", " ░▒░   ", "        "],
    },
    "B": {
        "idle": [" ▄████▄ ", "▐▓B▓▓▌ ", "▐████▌ ", " ▀██▀  "],
        "attack": [" ▄████▄ ", "▐▓B▓███", "▐████▌ ", " ▀██▀  "],
        "skill": ["▓▄███▄▓", "▐▓B▓▓▌▓", "▐████▌ ", "▓▀██▀▓ "],
        "hit": [" ▄███▄ ", "▐▓x▓▓  ", "▐███▌  ", " ▀█    "],
        "break": [" ▄███▄ ", "▐▓x▓!  ", "▐█▒▌   ", " ░░    "],
        "low": [" ▄██▒  ", "▐▓B▓   ", "▐█▒    ", " ▀     "],
        "death": ["  ░█░  ", " ░▓▒░  ", " ░░    ", "        "],
    },
    "r": {
        "idle": ["  ▄▒   ", " ▐r▒▌  ", " ░▟▙░  ", "  ▝▘   "],
        "attack": ["  ▄▒   ", " ▐r▒██ ", " ░▟▙   ", "  ▝▘   "],
        "skill": [" ░▄▒░  ", " ▐r▒▓  ", " ░▟▙░  ", " ░▝▘░  "],
        "hit": ["  ▄▒   ", " ▐x▒   ", "  ▟    ", "  ▝    "],
        "break": ["  ▄▒   ", " ▐x!   ", "  ▟    ", "       "],
        "low": ["  ▄    ", " ▐r    ", "  ▟    ", "       "],
        "death": ["        ", "  ░░   ", " ░     ", "        "],
    },
    "S": {
        "idle": [" ▄▒▒▄  ", "▐S▒▒▌ ", " ▟▒▙> ", "  ▀░  "],
        "attack": [" ▄▒▒▄  ", "██▒S▌ ", " ▟▒▙> ", "  ▀░  "],
        "skill": ["░▄▒▒▄░ ", "▓▐S▒▌▓", " ▟▒▙> ", " ░▀░  "],
        "hit": [" ▄▒▒▄  ", "▐x▒▒  ", " ▟▒   ", "  ▀   "],
        "break": [" ▄▒▒▄  ", "▐x▒!  ", " ▟    ", " ░    "],
        "low": [" ▄▒    ", "▐S▒   ", " ▟    ", "      "],
        "death": ["        ", " ░▒░   ", "  ░    ", "        "],
    },
    "w": {
        "idle": [" ░▒▒░  ", " ▐w▌░  ", "░▟▙░   ", " ░░    "],
        "attack": [" ░▒▒░  ", " ▐w▌██ ", "░▟▙    ", " ░░    "],
        "skill": ["░▒▒▒░  ", "▓▐w▌▓ ", "░▟▙░   ", " ░░░   "],
        "hit": [" ░▒░   ", " ▐x    ", "░▟     ", " ░     "],
        "break": [" ░▒░   ", " ▐x!   ", " ░     ", "       "],
        "low": [" ░▒    ", " ▐w    ", " ░     ", "       "],
        "death": ["        ", " ░ ░   ", "  ░    ", "        "],
    },
    "G": {
        "idle": [" ▄████▄ ", "▐█G█▌  ", "▐████▌ ", " ▀▟▙▀  "],
        "attack": [" ▄████▄ ", "▐█G████", "▐████▌ ", " ▀▟▙▀  "],
        "skill": [" ▄████▄ ", "▐█G█▌▓ ", "▐████▌ ", " ▀██▀  "],
        "hit": [" ▄███▄ ", "▐█x█   ", "▐██▌   ", " ▀▟    "],
        "break": [" ▄███▄ ", "▐█x█!  ", "▐█▒    ", " ░     "],
        "low": [" ▄██   ", "▐█G    ", "▐█     ", " ▀     "],
        "death": [" ▄░░▄  ", " ░█░   ", " ░░    ", "        "],
    },
}


EFFECT_BLOCK_PATTERNS: dict[str, tuple[str, str, str]] = {
    "wait": ("░░░▒▒░░░", "waiting for first echo", "░░░▒▒░░░"),
    "strike": ("░░▓▓████>", "STRIKE", "░░░▓▓██>"),
    "seal": ("░▒▓▓██==>", "SEAL", "░░▓▓XX▓▓░"),
    "shadow": ("░░▒▓███▒>", "SHADOW", "▒▒▓▓░░▓▓▒"),
    "fire": ("░▓██████>", "FIRE", "▓▓██░██▓▓"),
    "poison": ("::::▒▒▓▓>", "VENOM", "▒░▒░▒░▒░"),
    "guard": ("<██████>", "GUARD ONLINE", "<██SHD██>"),
    "observe": ("░▒░▒░▒░▒", "SCAN FIELD", "▒░▒░▒░▒░"),
    "counter": ("▓▓>====<▓▓", "COUNTER CLOCK", "▓▓<====>▓▓"),
    "break": ("░░▓▓XX▓▓░", "CHANT BROKEN", "░░░BRK░░░"),
    "chant": ("<▓▓████░░", "CHANT RELEASE", "<░░████▓▓"),
    "enemy_strike": ("<████▓▓░░", "STRIKE", "<██▓▓░░░"),
    "climax": ("████▓▓████", "IMPACT", "▓▓██RUP██▓"),
    "skill": ("░░▓▓██▓▓>", "SKILL", "░░░▓▓██>"),
}

SPECIAL_HERO_POSES = {
    "skill_shadow",
    "skill_fire",
    "skill_physical",
    "skill_holy",
    "skill_poison",
    "observe",
    "cast",
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
    if pose in sprites:
        return sprites[pose]
    if pose in SPECIAL_HERO_POSES:
        return _special_hero_pose(sprites, pose)
    return sprites.get("skill") or sprites["idle"]


def enemy_block_sprite(glyph: str, pose: str) -> list[str]:
    sprites = ENEMY_BLOCK_SPRITES.get(glyph, ENEMY_BLOCK_SPRITES["c"])
    return sprites.get(pose) or sprites.get("skill") or sprites["idle"]


def _special_hero_pose(sprites: dict[str, list[str]], pose: str) -> list[str]:
    base_key = "idle" if pose == "observe" else "skill"
    base = sprites.get(base_key) or sprites.get("skill") or sprites["idle"]
    rows = [_eight(row) for row in base[:4]]
    while len(rows) < 4:
        rows.append("        ")
    if pose == "skill_shadow":
        return [_edge(rows[0], "░", "░"), _edge(rows[1], "▒", "▒"), _edge(rows[2], "▓", "▒"), " ░▒▓▒░ "]
    if pose == "skill_fire":
        return [_edge(rows[0], "▓", "▓"), _edge(rows[1], "█", "▓"), _edge(rows[2], "▓", "█"), " ▓██▓  "]
    if pose == "skill_physical":
        return [_edge(rows[0], "▓", ">"), _edge(rows[1], "█", ">"), _edge(rows[2], "▓", ">"), " ░██>> "]
    if pose == "skill_holy":
        return [_edge(rows[0], "▓", "░"), _edge(rows[1], "▓", "▓"), _edge(rows[2], "░", "▓"), " ▓░▓░▓ "]
    if pose == "skill_poison":
        return [_edge(rows[0], "▒", "▒"), _edge(rows[1], "░", "▒"), _edge(rows[2], "▒", "░"), " ▒░▒░▒ "]
    if pose == "observe":
        return [_edge(rows[0], "░", "░"), _edge(rows[1], "▒", "▒"), _edge(rows[2], "░", "▒"), " ░▒░▒░ "]
    return [_edge(rows[0], "░", "▓"), _edge(rows[1], "▓", "░"), _edge(rows[2], "░", "▓"), " ░▓░▓░ "]


def _eight(row: str) -> str:
    return (row + "        ")[:8]


def _edge(row: str, left: str, right: str) -> str:
    fixed = _eight(row)
    return f"{left}{fixed[1:7]}{right}"
