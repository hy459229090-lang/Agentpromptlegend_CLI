from __future__ import annotations

import re
import sys

import pytest

import ouro_agent.cli.main as cli_main
from ouro_agent.cli.main import main
from ouro_agent.tui.graphics import (
    FALLBACK_CHAIN,
    render_graphics_doctor,
    select_graphics_backend,
)


class _FakeStdout:
    def __init__(self, *, tty: bool) -> None:
        self.tty = tty
        self.chunks: list[str] = []

    def isatty(self) -> bool:
        return self.tty

    def write(self, text: str) -> int:
        self.chunks.append(text)
        return len(text)

    def flush(self) -> None:
        return None

    @property
    def text(self) -> str:
        return "".join(self.chunks)


def test_graphics_capability_selects_iterm2_when_term_program_matches():
    capability = select_graphics_backend(
        requested_mode="auto",
        env={"TERM": "xterm-256color", "TERM_PROGRAM": "iTerm.app"},
        stdout_is_tty=True,
    )

    assert capability.selected_backend == "iterm2"
    assert capability.supports_iterm2 is True
    assert capability.fallback_chain == FALLBACK_CHAIN
    assert "auto selected iterm2 bitmap graphics." in capability.reasons


def test_graphics_capability_selects_kitty_for_ghostty():
    capability = select_graphics_backend(
        requested_mode="auto",
        env={
            "TERM": "xterm-ghostty",
            "TERM_PROGRAM": "ghostty",
            "COLORTERM": "truecolor",
        },
        stdout_is_tty=True,
    )

    assert capability.selected_backend == "kitty"
    assert capability.supports_kitty is True
    assert capability.term == "xterm-ghostty"
    assert capability.term_program == "ghostty"
    assert "auto selected kitty bitmap graphics." in capability.reasons


def test_graphics_capability_selects_sixel_when_requested_by_terminal():
    capability = select_graphics_backend(
        requested_mode="auto",
        env={"TERM": "xterm-256color", "OURO_GRAPHICS_SIXEL": "1"},
        stdout_is_tty=True,
    )

    assert capability.selected_backend == "sixel"
    assert capability.supports_sixel is True
    assert "auto selected sixel bitmap graphics." in capability.reasons


def test_graphics_capability_falls_back_under_ci_or_pipe():
    capability = select_graphics_backend(
        requested_mode="auto",
        env={"CI": "true", "TERM_PROGRAM": "iTerm.app", "TERM": "xterm-kitty"},
        stdout_is_tty=True,
    )

    assert capability.selected_backend == "ascii"
    assert capability.supports_iterm2 is True
    assert capability.supports_kitty is True
    assert "CI environment detected; deterministic fallback is preferred." in capability.reasons

    pipe_capability = select_graphics_backend(
        requested_mode="bitmap",
        env={"TERM_PROGRAM": "iTerm.app"},
        stdout_is_tty=False,
    )

    assert pipe_capability.selected_backend == "ascii"
    assert "stdout is not a TTY; terminal graphics escape output is unsafe." in pipe_capability.reasons


def test_graphics_capability_keeps_tmux_auto_conservative_but_allows_forced_bitmap():
    env = {"TERM": "xterm-kitty", "KITTY_WINDOW_ID": "7", "TMUX": "/tmp/tmux"}

    auto_capability = select_graphics_backend(
        requested_mode="auto",
        env=env,
        stdout_is_tty=True,
    )
    forced_capability = select_graphics_backend(
        requested_mode="bitmap",
        env=env,
        stdout_is_tty=True,
    )

    assert auto_capability.selected_backend == "unicode"
    assert "tmux/screen detected; auto mode skips bitmap unless forced." in auto_capability.reasons
    assert forced_capability.selected_backend == "kitty"


def test_graphics_doctor_report_is_ascii_safe_and_explains_fallback():
    capability = select_graphics_backend(
        requested_mode="unicode",
        env={"NO_COLOR": "1", "TERM": "xterm-256color"},
        stdout_is_tty=True,
    )

    report = render_graphics_doctor(capability)

    assert report.isascii()
    assert "GRAPHICS PREFLIGHT" in report
    assert "requested    : unicode" in report
    assert "selected     : unicode" in report
    assert "fallback     : iterm2 -> kitty -> sixel -> unicode -> ascii" in report
    assert "NO_COLOR is set" in report
    assert "Runtime image generation: disabled" in report


def test_cli_doctor_graphics_reports_deterministic_pipe_fallback(isolated_home, capsys):
    rc = main(["--lang", "en", "doctor", "graphics"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "GRAPHICS PREFLIGHT" in out
    assert "requested    : auto" in out
    assert "selected     : ascii" in out
    assert "pipe         : yes" in out
    assert "stdout is not a TTY" in out
    assert "Force with: --graphics auto | bitmap | unicode | ascii" in out


def test_cli_doctor_graphics_probe_image_uses_runtime_png(
    isolated_home,
    content_root,
    monkeypatch,
):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.setenv("TERM", "xterm-ghostty")
    monkeypatch.setenv("TERM_PROGRAM", "ghostty")
    monkeypatch.setenv("COLORTERM", "truecolor")
    fake_stdout = _FakeStdout(tty=True)
    monkeypatch.setattr(sys, "stdout", fake_stdout)

    rc = main(
        [
            "--lang",
            "en",
            "doctor",
            "graphics",
            "--graphics",
            "bitmap",
            "--probe-image",
            "--content-dir",
            str(content_root),
        ]
    )

    out = fake_stdout.text
    assert rc == 0
    assert "selected     : kitty" in out
    assert "IMAGE PROBE" in out
    assert "asset        : hero_shadow_apprentice_battle_sheet/idle" in out
    assert "\x1b_Ga=T,f=100,t=d,c=24,r=14,q=2" in out
    assert "IMAGE PROBE END" in out


def test_cli_play_graphics_unicode_enables_unicode_canvas(
    isolated_home,
    content_root,
    capsys,
):
    rc = main(
        [
            "--lang",
            "en",
            "play",
            "--mock",
            "--seed",
            "2",
            "--graphics",
            "unicode",
            "--no-animation",
            "--no-trace",
            "--content-dir",
            str(content_root),
        ]
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "STAGE [ALTAR]" in out
    assert "Result : victory" in out


def test_cli_play_graphics_ascii_overrides_unicode_flag(
    isolated_home,
    content_root,
    capsys,
):
    rc = main(
        [
            "--lang",
            "en",
            "play",
            "--mock",
            "--seed",
            "2",
            "--unicode",
            "--graphics",
            "ascii",
            "--no-animation",
            "--no-trace",
            "--content-dir",
            str(content_root),
        ]
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "STAGE [ALTAR]" not in out
    assert "Result : victory" in out


def test_cli_play_live_graphics_uses_sprite_stage_timeline(
    isolated_home,
    content_root,
    monkeypatch,
):
    monkeypatch.setattr(cli_main.time, "sleep", lambda _seconds: None)

    hero_skills = {
        "hero_shadow_apprentice": {
            "skill_shadow_sting",
            "skill_hex_seal",
            "skill_corrupted_focus",
        },
        "hero_ash_guardian": {
            "skill_tower_brace",
            "skill_ember_punish",
            "skill_ash_glare",
        },
        "hero_broken_string_hunter": {
            "skill_pierce_string",
            "skill_hook_break",
            "skill_eclipse_step",
        },
        "hero_mire_oracle": {
            "skill_mire_needle",
            "skill_omen_vial",
            "skill_sinking_veil",
        },
        "hero_gravewright": {
            "skill_grave_nail",
            "skill_crank_charge",
            "skill_burial_engine",
        },
        "hero_echo_exile": {
            "skill_bell_echo",
            "skill_silent_hymn",
            "skill_returning_chime",
        },
    }

    stages_by_hero: dict[str, set[str]] = {}
    for hero_id, skill_ids in hero_skills.items():
        fake_stdout = _FakeStdout(tty=True)
        monkeypatch.setattr(sys, "stdout", fake_stdout)

        rc = main(
            [
                "--lang",
                "en",
                "play",
                "--mock",
                "--seed",
                "2",
                "--hero",
                hero_id,
                "--graphics",
                "unicode",
                "--delay",
                "0",
                "--no-trace",
                "--content-dir",
                str(content_root),
            ]
        )

        out = fake_stdout.text
        stages = set(re.findall(r"OURO STAGE (battle\.skill_[^\s:]+)", out))
        stages_by_hero[hero_id] = stages
        assert rc == 0
        assert stages, hero_id
        assert any(
            stage.startswith(f"battle.{skill_id}.")
            for stage in stages
            for skill_id in skill_ids
        ), (hero_id, stages)
        assert "hit_stop" in out
        assert "LOG   action resolved by local judge; sprite stage is display-only" in out
        assert "Result : victory" in out

    assert (
        "battle.skill_hex_seal.enemy_hungry_cultist"
        in stages_by_hero["hero_shadow_apprentice"]
    )

    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setenv("TERM_PROGRAM", "iTerm.app")
    bitmap_stdout = _FakeStdout(tty=True)
    monkeypatch.setattr(sys, "stdout", bitmap_stdout)

    rc = main(
        [
            "--lang",
            "en",
            "play",
            "--mock",
            "--seed",
            "2",
            "--hero",
            "astia",
            "--graphics",
            "bitmap",
            "--delay",
            "0",
            "--no-trace",
            "--content-dir",
            str(content_root),
        ]
    )

    bitmap_out = bitmap_stdout.text
    assert rc == 0
    assert "OURO BITMAP STAGE battle.skill_hex_seal.enemy_hungry_cultist" in bitmap_out
    assert "\x1b]1337;File=" in bitmap_out
    assert "LOG   bitmap sprite stage is display-only; judge facts are local" in bitmap_out
    assert "Result : victory" in bitmap_out

    monkeypatch.delenv("TERM_PROGRAM", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setenv("OURO_GRAPHICS_SIXEL", "1")
    sixel_stdout = _FakeStdout(tty=True)
    monkeypatch.setattr(sys, "stdout", sixel_stdout)

    sixel_rc = main(
        [
            "--lang",
            "en",
            "play",
            "--mock",
            "--seed",
            "2",
            "--hero",
            "astia",
            "--graphics",
            "bitmap",
            "--delay",
            "0",
            "--no-trace",
            "--content-dir",
            str(content_root),
        ]
    )

    sixel_out = sixel_stdout.text
    assert sixel_rc == 0
    assert "OURO BITMAP STAGE battle.skill_hex_seal.enemy_hungry_cultist" in sixel_out
    assert "\x1bPq" in sixel_out
    assert "LOG   bitmap sprite stage is display-only; judge facts are local" in sixel_out
    assert "Result : victory" in sixel_out

    zh_stdout = _FakeStdout(tty=True)
    monkeypatch.setattr(sys, "stdout", zh_stdout)

    zh_rc = main(
        [
            "--lang",
            "zh",
            "play",
            "--mock",
            "--seed",
            "2",
            "--hero",
            "astia",
            "--graphics",
            "unicode",
            "--delay",
            "0",
            "--no-trace",
            "--content-dir",
            str(content_root),
        ]
    )

    zh_out = zh_stdout.text
    assert zh_rc == 0
    assert "OURO 舞台 battle.skill_hex_seal.enemy_hungry_cultist" in zh_out
    assert "效果轨" in zh_out
    assert "日志 行动已由本地裁判结算；sprite 舞台只负责展示" in zh_out
    assert "LOG   action resolved by local judge" not in zh_out


def test_cli_run_live_graphics_uses_sprite_stage_timeline(
    isolated_home,
    content_root,
    monkeypatch,
):
    monkeypatch.setattr(cli_main.time, "sleep", lambda _seconds: None)
    fake_stdout = _FakeStdout(tty=True)
    monkeypatch.setattr(sys, "stdout", fake_stdout)

    rc = main(
        [
            "--lang",
            "en",
            "run",
            "--mock",
            "--seed",
            "7",
            "--hero",
            "astia",
            "--graphics",
            "unicode",
            "--delay",
            "0",
            "--auto",
            "--no-trace",
            "--content-dir",
            str(content_root),
        ]
    )

    out = fake_stdout.text
    assert rc == 0
    assert "OURO STAGE battle.skill_" in out
    assert "hit_stop" in out
    assert "LOG   action resolved by local judge; sprite stage is display-only" in out
    assert "Run Archive:" in out


def test_cli_rejects_invalid_graphics_mode(isolated_home):
    with pytest.raises(SystemExit) as err:
        main(["play", "--graphics", "hologram"])

    assert err.value.code == 2
