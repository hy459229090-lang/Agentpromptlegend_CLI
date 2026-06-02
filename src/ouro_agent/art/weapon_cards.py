"""Reusable weapon card art for hero and battle UI."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WeaponCardArt:
    icon: str
    badge: str
    ascii_art: tuple[str, ...]
    unicode_art: tuple[str, ...]
    build_shift: str
    ai_effect: str


HERO_WEAPON_CARDS: dict[str, tuple[str, str]] = {
    "hero_shadow_apprentice": ("[W:STF] c==*", "[ONLINE]"),
    "hero_ash_guardian": ("[W:SHD] [#]", "[PAIR]"),
    "hero_broken_string_hunter": ("[W:XBW] ==>", "[PAIR]"),
    "hero_mire_oracle": ("[W:VIL] (v)", "[SEED]"),
    "hero_gravewright": ("[W:GER] [o]", "[SEED]"),
    "hero_echo_exile": ("[W:BEL] )o(", "[SEED]"),
}

HERO_WEAPON_CARD_ART: dict[str, WeaponCardArt] = {
    "hero_shadow_apprentice": WeaponCardArt(
        icon="[W:STF] c==*",
        badge="[ONLINE]",
        ascii_art=("  c==*  ", " --###- ", "   ||   "),
        unicode_art=("  ▐==*  ", " ░▓███░ ", "   ▌▌   "),
        build_shift="[ONLINE] shadow/control",
        ai_effect="AI favors interrupts and tempo skills.",
    ),
    "hero_ash_guardian": WeaponCardArt(
        icon="[W:SHD] [#]",
        badge="[PAIR]",
        ascii_art=("  .###. ", "  [###] ", "   | |  "),
        unicode_art=("  ▄███▄ ", "  ████▌ ", "   ▀ ▀  "),
        build_shift="[PAIR] guard/shield",
        ai_effect="AI braces before enemy telegraphs.",
    ),
    "hero_broken_string_hunter": WeaponCardArt(
        icon="[W:XBW] ==>",
        badge="[PAIR]",
        ascii_art=("  ==\\   ", "=====>  ", "  ==/   "),
        unicode_art=("  ▄▄▸   ", "████▸  ", "  ▀▀▸   "),
        build_shift="[PAIR] bleed/execute",
        ai_effect="AI stacks bleed, then executes low HP targets.",
    ),
    "hero_mire_oracle": WeaponCardArt(
        icon="[W:VIL] (v)",
        badge="[SEED]",
        ascii_art=("  .-.   ", " (~~~)  ", "  \\_/   "),
        unicode_art=("  ▄█▄   ", " ▐▒▒▒▌  ", "  ▀▄▀   "),
        build_shift="[SEED] poison/omen",
        ai_effect="AI opens attrition with poison and silence.",
    ),
    "hero_gravewright": WeaponCardArt(
        icon="[W:GER] [o]",
        badge="[SEED]",
        ascii_art=(" [o=o]  ", "  ###   ", " /___\\  "),
        unicode_art=(" ▐▓o▓▌  ", "  ███   ", " ▄███▄  "),
        build_shift="[SEED] gear/trap",
        ai_effect="AI marks targets before heavy engine bursts.",
    ),
    "hero_echo_exile": WeaponCardArt(
        icon="[W:BEL] )o(",
        badge="[SEED]",
        ascii_art=("  )o(   ", " --O--  ", "  / \\   "),
        unicode_art=("  ▐o▌   ", " ▓███▓  ", "  ▀ ▀   "),
        build_shift="[SEED] echo/cleanse",
        ai_effect="AI keeps echo wards for heavy turns.",
    ),
}


BATTLE_WEAPON_LINES: dict[str, tuple[str, str]] = {
    "[CNDL]": ("[W:STF] c==* Black Candle Staff", "[ONLINE] shadow 3/3 control 2/3"),
    "[SHLD]": ("[W:SHD] [#] Warden Aegis", "[PAIR] guard 2/3 shield 2/3"),
    "[XBOW]": ("[W:XBW] ==> Severed String", "[PAIR] bleed 2/3 execute 1/2"),
    "[VENM]": ("[W:VIL] (v) Omen Vial", "[SEED] poison 2/3 omen 1/2"),
    "[GEAR]": ("[W:GER] [o] Burial Crank", "[SEED] gear 2/3 trap 1/2"),
    "[ECHO]": ("[W:BEL] )o( Cracked Bell", "[SEED] echo 2/3 cleanse 1/2"),
}


def hero_weapon_card(hero_id: str) -> tuple[str, str]:
    return HERO_WEAPON_CARDS.get(hero_id, ("[W:???]", "[SEED]"))


def battle_weapon_line(short_tag: str) -> tuple[str, str]:
    return BATTLE_WEAPON_LINES.get(short_tag, ("[W:???] unknown", "[SEED] tags pending"))


def hero_weapon_card_art(hero_id: str) -> WeaponCardArt:
    return HERO_WEAPON_CARD_ART.get(
        hero_id,
        WeaponCardArt(
            icon="[W:???]",
            badge="[SEED]",
            ascii_art=("  ???  ", " ----- ", "  ???  "),
            unicode_art=("  ░░░  ", " ░▓▓▓░ ", "  ░░░  "),
            build_shift="[SEED] tags pending",
            ai_effect="AI behavior pending.",
        ),
    )
