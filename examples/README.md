# examples

Safe examples for players and implementers.

- `config/`: provider configuration examples with no real API keys.
- `traces/`: synthetic battle traces for replay and tests.
- `ouro-*.svg`: README media captures for the storefront showcase, storefront
  hero, screenshot wall, weapon gallery, battle canvas, animation filmstrip,
  motion evidence wall, decision focus HUD, and after-action report. They stay storefront-friendly
  while being derived from mock CLI output, and the showcase/storefront/
  screenshot wall mirrors current battle cue tags such as `VOX [INTERRUPT]`,
  `ENM [HIT]`, `WINDOW PRESSURE`, language switching, and the mock `Play Now`
  command. `ouro-battle-canvas.svg` mirrors the current impact-stage battle
  grammar with `SCENE`, `HIT FLASH`, `PULSE`, `CAMERA`, `WINDOW PRESSURE`, and
  `TTY PARTIAL REFRESH` anchors. `ouro-animation-filmstrip.svg` is an animated SVG preview of
  `MODE SELECT`, `ROUTE LOCK`, `REWARD LOCK`, `SHOP LOCK`, `REST LOCK`,
  `EVENT LOCK`, Motion Director `FLOW/FOCUS/RISK/NEXT`, and battle phase
  motion. `ouro-motion-evidence.svg` is a fixed-seed evidence wall covering
  mode select, route focus, reward focus, battle hit, and death pause.
