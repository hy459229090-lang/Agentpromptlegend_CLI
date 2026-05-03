"""Validate the content directory and report a structured summary."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ouro_agent.content import load_content_bundle, ContentError
from ouro_agent.i18n import DEFAULT_LANGUAGE, label


@dataclass
class ValidationReport:
    ok: bool
    heroes: int
    skills: int
    enemies: int
    items: int = 0
    affixes: int = 0
    resonances: int = 0
    error: str | None = None

    def render(self, language: str = DEFAULT_LANGUAGE) -> str:
        lang = language
        lines = [label("content_validation_title", lang)]
        lines.append(f"  {label('content_heroes', lang)}     : {self.heroes}")
        lines.append(f"  {label('content_skills', lang)}     : {self.skills}")
        lines.append(f"  {label('content_enemies', lang)}    : {self.enemies}")
        lines.append(f"  {label('content_items', lang)}      : {self.items}")
        lines.append(f"  {label('content_affixes', lang)}    : {self.affixes}")
        lines.append(f"  {label('content_resonances', lang)} : {self.resonances}")
        if self.ok:
            lines.append(
                f"  {label('content_status', lang)}     : "
                f"{label('content_status_ok', lang)}"
            )
        else:
            lines.append(
                f"  {label('content_status', lang)}     : "
                f"{label('content_status_fail', lang)}"
            )
            if self.error:
                lines.append(f"  {label('content_error', lang)}      : {self.error}")
        return "\n".join(lines)


def validate_content_dir(content_root: Path) -> ValidationReport:
    try:
        bundle = load_content_bundle(content_root)
    except ContentError as err:
        return ValidationReport(
            ok=False, heroes=0, skills=0, enemies=0, error=str(err)
        )
    return ValidationReport(
        ok=True,
        heroes=len(bundle.heroes),
        skills=len(bundle.skills),
        enemies=len(bundle.enemies),
        items=len(bundle.items),
        affixes=len(bundle.affixes),
        resonances=len(bundle.resonances),
    )
