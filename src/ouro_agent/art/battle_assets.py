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
    "C": {
        "idle": ["  [C]", " /|>|", " /|\\", " torn banner"],
        "attack": ["  [C]--", " /|>|", " /|\\", " banner hook"],
        "skill": [" = [C]", " /|>|", " /|\\", " hunger rite"],
        "hit": ["  [X]", " /|>!", " /|\\", " banner split"],
        "break": ["  [X]!", " /|>", " /|", " rite broken"],
        "low": ["  [C]", " /|>", " /", " banner low"],
        "death": ["  .", " /_\\", " torn cloth", ""],
    },
    "K": {
        "idle": [" ((K))", " /|w|\\", " / ^ \\", " rite ring"],
        "attack": [" ((K)--", " /|w|\\", " / ^ \\", " black lash"],
        "skill": ["((K*))", " /|w|\\", " / ^ \\", " wick rite"],
        "hit": [" ((K))", " /|w|!", " / ^", " ring bent"],
        "break": [" ((X))", " /|x|!", " /", " rite cut"],
        "low": [" ((K))", " /|w|", " /", " ring dim"],
        "death": ["  . .", "  /_\\", " ring ash", ""],
    },
    "B": {
        "idle": [" <BOSS>", " /|W|\\", " /###\\", " archive flame"],
        "attack": [" <BOSS--", " /|W|\\", " /###\\", " crozier smash"],
        "skill": [" <B*SS>", " /|W|\\", " /###\\", " archive chant"],
        "hit": [" <BOSS>", " /|W|!", " /##", " seal cracks"],
        "break": [" <BRK>", " /|x|!", " /#", " archive break"],
        "low": [" <BOSS>", " /|W|", " /#", " phase gutter"],
        "death": ["  .#.", " /___\\", " archive ash", ""],
    },
    "r": {
        "idle": ["  ,r,", " <\\_/", "  ^^", " mire teeth"],
        "attack": ["  ,r--", " <\\_/", "  ^^", " rat rush"],
        "skill": [" ~,r,~", " <\\_/", "  ^^", " poison spit"],
        "hit": ["  ,x,", " <\\_!", "  ^", " tail snap"],
        "break": ["  ,x!", " <\\_", "  ^", " spine break"],
        "low": ["  ,r", " <\\_", "  ^", " belly low"],
        "death": ["  ..", " _/ ", " mire still", ""],
    },
    "S": {
        "idle": ["  <S>", " /\\_/\\", "  /\\", " stinger high"],
        "attack": [" --<S>", " /\\_/\\", "  /\\", " claw snap"],
        "skill": [" ~<S>~", " /\\_/\\", "  /\\", " venom arc"],
        "hit": ["  <X>", " /\\_/!", "  /", " shell split"],
        "break": ["  <X!", " /\\_", "  /", " sting cut"],
        "low": ["  <S", " /\\_", "  /", " stinger low"],
        "death": ["  .", " /__\\", " venom dry", ""],
    },
    "w": {
        "idle": ["  {w}", " ~| |~", "  / \\", " ash drift"],
        "attack": ["  {w}--", " ~| |~", "  / \\", " ash claw"],
        "skill": [" ~{w}~", " ~| |~", "  / \\", " gray hex"],
        "hit": ["  {x}", " ~| !", "  /", " ash torn"],
        "break": ["  {x}!", " ~|", "  /", " veil broken"],
        "low": ["  {w}", " ~|", "  /", " smoke thin"],
        "death": ["  .", " ~ ~", " ash fall", ""],
    },
    "G": {
        "idle": [" [GOL]", " /[#]\\", " _/ \\_", " ash plates"],
        "attack": [" [GOL]--", " /[#]\\", " _/ \\_", " stone swing"],
        "skill": [" [G*L]", " /[#]\\", " _/ \\_", " ember core"],
        "hit": [" [GOL]", " /[#]!", " _/", " plate crack"],
        "break": [" [BRK]", " /[x]!", " _/", " core open"],
        "low": [" [GOL]", " /[#]", " _/", " plates low"],
        "death": [" [___]", "  /_\\", " ash rubble", ""],
    },
}


DEFAULT_HERO_SPRITE = ["  ???", " /|?|\\", "  / \\", " unknown"]
DEFAULT_ENEMY_SPRITE = ["  (?)", "  /|\\", "  / \\", " ???"]


def hero_sprite(hero_id: str, pose: str) -> list[str]:
    sprites = HERO_SPRITES.get(hero_id, HERO_SPRITES["hero_shadow_apprentice"])
    return sprites.get(pose) or sprites.get("skill") or sprites.get("idle") or DEFAULT_HERO_SPRITE


def enemy_sprite(glyph: str, pose: str) -> list[str]:
    sprites = ENEMY_SPRITES.get(glyph, ENEMY_SPRITES["c"])
    return sprites.get(pose) or sprites.get("skill") or sprites.get("idle") or DEFAULT_ENEMY_SPRITE
