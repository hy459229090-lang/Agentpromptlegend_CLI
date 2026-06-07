# Changelog

All notable player-facing and release-facing changes for Ouro Agent: Prompt Legend.

## 0.1.0 - 2026-06-01

### Added

- Installable `ouro` CLI package with `pip`, editable installs, and `pipx` Git installs.
- Deterministic mock provider that works without network access or API keys.
- One-hero AI roguelike loop: quick battle, full dungeon run, route choices, rewards, shops, rests, boss fights, Codex, replay, run archive, compact run report, and death history.
- `ouro demo` guided first-player smoke that shows menu status, hero card, deterministic mock battle, and Codex readback without network, trace, or interaction.
- ASCII-safe default TUI with optional Unicode canvas rendering, duel layout, battle sprites, action lane, model intent/risk/alignment, resource deltas, climax banners, and fixed-width snapshot coverage.
- Provider configuration for `mock`, `openai`, `anthropic`, and `openai-compatible`, storing only environment variable names for API keys.
- Offline `ouro config preflight` for provider/model/base URL/env readiness without showing key values or making network calls.
- Optional `scripts/provider_smoke.py` real-provider smoke helper with offline preflight, redacted env reporting, and explicit `--live` mode that fails if battle execution falls back to mock.
- `scripts/acceptance_check.py` one-command mock-first user acceptance runner that reports guided demo, fixed-seed full run, and completion audit status without writing sign-off markers.
- Bundled structured content installed under `share/ouro-agent/content`, so `ouro doctor`, `ouro play --mock`, and `ouro run --mock` work outside the source checkout.
- Local evidence commands for QA: content validation, fixed-seed mock play, Codex/run-history readback, replay, batch balance reports, and install smoke tests.
- Repo-root release gate runner at `scripts/release_check.py` for pytest, content validation, isolated doctor, version consistency, whitespace diff checks, and privacy scan.

### Changed

- `ouro run` treats player death as a completed play session by default and reserves nonzero outcome exits for `--strict-result-exit-code`.
- Interactive Ctrl-C/EOF returns code `130` through `main()` instead of raising an uncaught `SystemExit` inside callers.
- `--content-dir` help text now describes the installed bundled-content fallback rather than implying source checkout only.
- `ouro status` provides a returning-player overview of provider/profile state, Codex progress, run/death totals, the latest run, a next-run plan, and next commands.
- `ouro run-report` turns the latest saved run, or a selected `.run.json`, into a short outcome/build/route/Codex/next-run report.
- The implementation roadmap now reflects the v0.4 release-candidate state: S6-S9 are done, with remaining work tracked as external sign-offs.
- `scripts/release_scope.py` audits dirty-tree paths against the release-candidate boundary, prints a read-only `--stage-plan`, and is included in the release gate as `scope-boundary`.
- `scripts/completion_audit.py` summarizes release gates, scope, and external sign-offs so the broader goal is not marked complete while sign-offs remain pending.
- `docs/engineering/LICENSE_DECISION_20260601.md` gives the project owner a pending License/private-policy decision template without selecting a License automatically.
- `ouro list-heroes` now uses each hero's own ASCII/Unicode low-pixel silhouette and expands the weapon gallery into 3-line weapon card art; `ouro list-heroes --unicode` previews the block-art roster before opening a hero card.
- README and README.zh now open like a game storefront: bilingual switch, strong playable hook, hero capsule art, 30-second mock CTA, Build/Fight/Learn media gallery with weapon gallery art, visual combat language, and engineering/provider details moved behind the player-facing pitch.
- README and README.zh now add a Steam-style screenshot wall that shows main menu, encounter briefing, battle canvas, and after-action report before the engineering notes.
- README and README.zh now add a Game Capsule section and "watch the run first" intro so GitHub opens more like a player-facing game page than a project index.
- README and README.zh now add a Steam-style front-page switch with Chinese/English player paths, mock demo CTAs, media-first positioning, and README media updated to show the current `DECISION FOCUS` battle HUD.
- README and README.zh now push the storefront visual into the first hero section, put the 30-second mock CTA before the screenshot wall, and fold the Steam-page rationale so the default read feels like a game intro instead of a project index.
- README and README.zh now sharpen the player-storefront first screen with visible Gameplay Screens / Play Now navigation, a larger Build/Fight/Learn screenshot wall, and README media that mirrors the current `VOX [INTERRUPT]` / `ENM [HIT]` battle cue tags.
- README and README.zh now expose a fixed language switch, current-language state, UTF-8/ASCII language note, store-page capsule copy, and media-first Play Now proof directly in the first screen and README SVG hero art.
- Canvas battle sprites now render distinct block-art variants for shadow, fire, poison, holy, physical, observe, and cast poses; center effect lanes use stronger low-pixel tracks, and README battle media reflects the new visual grammar.
- Encounter briefing now opens with a mini-stage: left hero silhouette, right enemy silhouette, threat rail, window rail, director line, and the original brief fields kept for readability.
- Battle frames now include a `DECISION FOCUS` HUD that gathers action, plan, risk, prompt/build alignment, next step, and counter window status before the detailed action lens.
- `CINEMATIC BEAT` now starts with a fixed `THREAT -> SELECT -> IMPACT -> JUDGE -> MEANING` turn script chain in English and Chinese, so each battle frame reads as one tactical cause/effect beat instead of scattered fields.
- `CINEMATIC BEAT` VOX/ENM lines now carry situational cue tags such as `[INTERRUPT]`, `[HIT]`, `[打断]`, and `[受击]`, while the top battle canvas keeps its short bark bubbles.
- Unicode battle Canvas now shows a `WINDOW PRESSURE` / `窗口压力` HUD rail for chant/counter timing, covering ready, cooldown, MP-blocked, answered, stable, and cleared states without changing combat rules.
- Unicode battle Canvas now shows a readable `SCENE` / `场景` layer for candle/ash/arch, gate/shield, mire/fog, archive/pages, and grave/engine stage textures without changing combat rules.
- Battle reports now open with an after-action stage: hero silhouette, fallen-enemy silhouette, result rail, damage rail, next lens, and bilingual director readout before the detailed result board.
- Battle report result, turn-map, and play-next sections now render as pixel HUD panels while preserving the same tactical readout and rematch commands.
- `ouro weapons` adds a standalone weapon gallery with ASCII-safe and Unicode card walls, weapon silhouettes, Build tags, AI behavior, and next-step hero-card/run commands.
- `ouro menu` now opens as a framed main menu console with a recommended next command, status HUD, player journey board, and grouped entry commands instead of a plain text index.

### Validation

- `venv312/bin/python -m pytest` -> `397 passed`
- `venv312/bin/ouro validate-content` -> content OK
- `git diff --check` -> no whitespace errors
- `venv312/bin/python scripts/release_check.py --evidence-only` -> `Evidence counts OK: 397 tests collected; 247 release-bound text files.`
- `venv312/bin/python scripts/release_check.py --privacy-scan-only` -> no likely plaintext secrets
- Clean venv install smoke: `/private/tmp/ouro_install_smoke_20260601/bin/python -m pip install .`
- Installed CLI smoke from `/private/tmp`: `ouro --version`, `ouro doctor`, `ouro demo --seed 1`, `ouro play --mock --seed 1 --no-animation --no-trace`, `ouro codex`, `ouro runs --limit 1`, `ouro run-report`, `ouro history --limit 1`, and `ouro status`

### Notes

- API keys are never stored in config, examples, traces, Codex, run archives, or death history.
- Mock mode remains the supported offline demo path for GitHub release review.
