"""Battle sprite and effect assets for ASCII-safe TUI rendering."""
from __future__ import annotations


HERO_SPRITES: dict[str, dict[str, list[str]]] = {
    "hero_shadow_apprentice": {
        "idle": ["  .^.", " /|c|\\", "  / \\", " candle low"],
        "attack": ["  .^.", " /|c|-->", "  / \\", " candle thrust"],
        "skill_shadow": ["  .^.", " /|c|==*", "  / \\", " shadow burst"],
        "skill_fire": ["  .^.", " /|c|=#*", "  / \\", " flame erupt"],
        "skill_physical": ["  .^.", " /|c|-->", "  / \\", " quick strike"],
        "skill_holy": ["  .^.", " /|c|=+*", "  / \\", " light burst"],
        "skill_poison": ["  .^.", " /|c|=~*", "  / \\", " venom spray"],
        "skill": ["  .^.", " /|c|==*", "  / \\", " candle raised"],
        "defend": ["  .^.", " /|c|\\", "  / \\", " candle guard"],
        "observe": ["  .^.", " /|c|\\", "  / \\", " scanning..."],
        "hit": ["  .x.", " /|c", "  /\\", " flame bends"],
        "low": ["  .^.", " /|c|\\", "  / \\", " candle guttering"],
        "victory": ["  .^.", " /|c|/*", "  / \\", " black flame steady"],
        "defeat": ["  ._.", " /|c", "  /_", " candle out"],
    },
    "hero_ash_guardian": {
        "idle": ["   O", "  /#\\", "  / \\", " shield set"],
        "attack": ["   O", "  /#\\->", "  / \\", " shield bash"],
        "skill_fire": ["   O", "  [#]*", "  / \\", " ember burst"],
        "skill_physical": ["   O", "  /#\\->", "  / \\", " heavy strike"],
        "skill": ["   O", "  [#]", "  / \\", " guard raised"],
        "defend": ["   O", "  [#]", "  / \\", " block stance"],
        "observe": ["   O", "  /#\\", "  / \\", " assessing..."],
        "hit": ["   o", "  /#\\!", "  / \\", " ash cracks"],
        "low": ["   o", "  [#]", "  / \\", " shield low"],
        "victory": ["   O", "  [#]^", "  / \\", " tower holds"],
        "defeat": ["   o", "  /#_", "  /_", " tower fallen"],
    },
    "hero_broken_string_hunter": {
        "idle": ["   o", "  /|\\", "  /->", " string drawn"],
        "attack": ["   o", "  /|\\", "  /==>", " bolt loosed"],
        "skill_physical": ["   o", "  /|\\", "  /==>", " pierce shot"],
        "skill_poison": ["   o", "  /|\\", "  /==>~", " poison bolt"],
        "skill": ["   o", "  /|\\", "  /==>", " bolt loosed"],
        "defend": ["   o", "  /|\\", "  /->", " dodge stance"],
        "observe": ["   o", "  /|\\", "  /->", " aiming..."],
        "hit": ["   x", "  /|", "  /\\", " string snaps"],
        "low": ["   o", "  /|", "  /->", " breathing hard"],
        "victory": ["   o", "  /|\\", "  /==>", " quarry marked"],
        "defeat": ["   x", "  /|_", "  /_", " string buried"],
    },
    "hero_mire_oracle": {
        "idle": ["  .-.", " (v v)", " /|~|\\", " vial low"],
        "attack": ["  .-.", " (v v)-->", " /| |\\", " vial strike"],
        "skill_poison": ["  .-.", " (v v)=~", " /| |\\", " poison cloud"],
        "skill": ["  .-.", " (v v)==", " /| |\\", " vial cracked"],
        "defend": ["  .-.", " (v v)", " /|~|\\", " mist shield"],
        "observe": ["  .-.", " (v v)", " /|~|\\", " scrying..."],
        "hit": ["  .x.", " (v v)", " /|", " veil torn"],
        "low": ["  .-.", " (v v)", " /|~", " mire rising"],
        "victory": ["  .-.", " (v v)", " /|~|*", " omen sealed"],
        "defeat": ["  ._.", " (v v", " /|_", " vial spilled"],
    },
    "hero_gravewright": {
        "idle": ["  [o]", " /|n|\\", "  / \\", " crate set"],
        "attack": ["  [o]", " /|n|-->", "  / \\", " crank strike"],
        "skill_fire": ["  [o]", " /|n|=*", "  / \\", " engine burst"],
        "skill_physical": ["  [o]", " /|n|-->", "  / \\", " nail strike"],
        "skill": ["  [o]", " /|n|==", "  / \\", " crank turns"],
        "defend": ["  [o]", " /|n|\\", "  / \\", " crate shield"],
        "observe": ["  [o]", " /|n|\\", "  / \\", " inspecting..."],
        "hit": ["  [x]", " /|n|!", "  / \\", " gears skip"],
        "low": ["  [o]", " /|n|", "  / \\", " crate smoking"],
        "victory": ["  [o]", " /|n|^", "  / \\", " engine purrs"],
        "defeat": ["  [x]", " /|n_", "  /_", " gears silent"],
    },
    "hero_echo_exile": {
        "idle": ["  o)o", " /| |\\", "  / \\", " bell quiet"],
        "attack": ["  o)o-->", " /| |\\", "  / \\", " bell strike"],
        "skill_holy": ["  o)o=+", " /| |\\", "  / \\", " holy ring"],
        "skill": ["  o)o==", " /| |\\", "  / \\", " bell rings"],
        "defend": ["  o)o", " /| |\\", "  / \\", " echo ward"],
        "observe": ["  o)o", " /| |\\", "  / \\", " listening..."],
        "hit": ["  x)o", " /| |", "  /\\", " echo cracks"],
        "low": ["  o)o", " /| |", "  / \\", " hymn thin"],
        "victory": ["  o)o", " /| |+", "  / \\", " bell returns"],
        "defeat": ["  x)o", " /| _", "  /_", " echo gone"],
    },
}


ENEMY_SPRITES: dict[str, dict[str, list[str]]] = {
    "c": {
        "idle": ["  (c)", "  /|>", "  / \\", " hooked blade"],
        "attack": ["  (c)-->", "  /|>", "  / \\", " blade lunge"],
        "skill": ["  (c)==", "  /|>", "  / \\", " ragged chant"],
        "hit": ["  (x)", "  /|>!", "  / \\", " staggered"],
        "break": ["  (x)", "  /|>!", "  / \\", " broken"],
        "low": ["  (c)", "  /|>", "  / \\", " blade low"],
        "death": ["   .", "  /_\\", "  ash", ""],
    },
    "k": {
        "idle": [" ~(k)~", " /|w|\\", "  / \\", " candle ring"],
        "attack": [" ~(k)--", " /|w|\\", "  / \\", " ritual strike"],
        "skill": [" ~(k*)~", " /|w|\\", "  / \\", " wick bright"],
        "hit": [" ~(k)~", " /|w|!", "  / \\", " chant bent"],
        "break": [" ~(k)~", " /|x|!", "  / \\", " chant broken"],
        "low": [" ~(k)~", " /|w|\\", "  / \\", " flame dim"],
        "death": ["   .", "  /_\\", " wick ash", ""],
    },
}

ENEMY_SPRITES.update(
    {
        "C": ENEMY_SPRITES["c"],
        "K": ENEMY_SPRITES["k"],
        "B": ENEMY_SPRITES["k"],
        "r": ENEMY_SPRITES["c"],
        "S": ENEMY_SPRITES["c"],
        "w": ENEMY_SPRITES["k"],
        "G": ENEMY_SPRITES["k"],
    }
)


DEFAULT_HERO_SPRITE = ["  ???", " /|?|\\", "  / \\", " unknown"]
DEFAULT_ENEMY_SPRITE = ["  (?)", "  /|\\", "  / \\", " ???"]


def hero_sprite(hero_id: str, pose: str) -> list[str]:
    sprites = HERO_SPRITES.get(hero_id, HERO_SPRITES["hero_shadow_apprentice"])
    return sprites.get(pose) or sprites.get("skill") or sprites.get("idle") or DEFAULT_HERO_SPRITE


def enemy_sprite(glyph: str, pose: str) -> list[str]:
    sprites = ENEMY_SPRITES.get(glyph, ENEMY_SPRITES["c"])
    return sprites.get(pose) or sprites.get("skill") or sprites.get("idle") or DEFAULT_ENEMY_SPRITE
