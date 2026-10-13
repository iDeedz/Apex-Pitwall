# Contributing to Apex Pitwall

Thanks for helping out!

1. Fork the repo and create a branch: `git checkout -b feat/my-change`.
2. Keep it build-free: plain HTML, CSS and vanilla JS, with no frameworks or bundlers.
3. Every page shares the same chrome. Put page-specific markup inside `<main>` only, so in-app navigation keeps working.
4. Use `--ax-*-t` tokens for text colours. Text must stay at or above 4.5:1 contrast in both themes.
5. Bind events in `js/app.js` with the `on()` helper and make page init idempotent (`AX.initPage`).
6. If you change lap or sector data, run `python3 tools/derive.py` and `python3 qa/audit.py`.
7. Before opening a PR, run `node qa/check.js` and `node qa/spa.js` (see the README) and check 390/768/1280 in both themes.
8. Use clear commit messages and add a line to `CHANGELOG.md` under *Unreleased*.

For bugs, open an issue with the page, viewport, theme and a screenshot.
