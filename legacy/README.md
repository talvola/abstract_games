# Legacy prototypes (archived)

These are the **original standalone React prototypes** of Oust and Yodd — the
single-file games this repository started as, before it became a generic
abstract-games platform. They are kept for reference only and are **not part of
the live application**.

Both games now run as proper engine modules on the platform:

- Oust → `engine/games/oust/`
- Yodd → `engine/games/yodd/`

with the shared backend (`server/`), frontend (`web/`), and SDK (`engine/agp/`).

## What's here

A self-contained multi-page Vite app:

- `oust.jsx`, `yodd.jsx` — the game components (UI + rules baked together).
- `index.html` — landing page linking to the two games.
- `oust/index.html`, `yodd/index.html`, `src/` — per-game entry points.
- `vite.config.js`, `package.json`, `package-lock.json` — its own build.

## Running it (if ever needed)

```bash
cd legacy
npm install
npm run dev      # serves the landing page + both games
```

Paths inside are relative to this folder, so it builds in place.
