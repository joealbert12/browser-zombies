# Browser Zombies

Round-based zombie survival that runs in a browser tab. No install, no
launcher, no plugin — it loads and it plays, on a phone as well as a desktop.

**<https://browserzombies.fun>**

Three.js, one HTML file, and a Python leaderboard that fits in 150 lines.

---

## Running it

```sh
./fetch-assets.sh          # pulls the models and animations (see below)
python3 -m http.server 8777
open http://localhost:8777
```

It has to be served over http. Opening `index.html` as a `file://` URL fails:
the loaders fetch the models with XHR and the browser blocks that.

## The assets are not in this repository

Most of the models are CC-BY and could be. Six are not: two carry Sketchfab
Standard, which forbids redistribution outright; two are NonCommercial; two
lost their licence metadata somewhere in the pipeline and their provenance
could not be re-established. The character and its animations are Mixamo's,
which is free to use in a project but not to republish as files.

Shipping a partial set would leave a repository that cannot run, so none of
them are here and `fetch-assets.sh` pulls the lot from the live site.
Everyone's credit is in [ATTRIBUTION.md](ATTRIBUTION.md). The textures *are*
committed — ambientCG's maps are CC0.

## How it is put together

`index.html` is the whole game: renderer, collision, pathfinding, weapons, HUD
and every screen. It is one file because the thing it had to beat was a
loading screen, and a single document that references a handful of models
starts faster than a bundle.

A few decisions worth knowing before changing anything:

**Collision is a rasterised grid, not raycasts.** The map is 206,253
triangles, and a per-frame raycast against it cost 5–7 ms. Everything is
burned once into 0.4 m cells holding floor heights and merged wall spans, and
a lookup is a couple of array reads — about 0.0003 ms a frame. `buildColliders()`
does the burn; `mapGroundAt()` and `mapBlocked()` are the queries.

**Zombies navigate a distance field.** A BFS from the player's cell, rebuilt
every 0.35 s, and each zombie walks downhill. Steering them with direct
pursuit did not work: all eight got into the theatre and none of them ever
arrived.

**`MIN_CEIL = 1.05`.** Anything lower than that overhead is furniture, not a
ceiling. Without it the Quick Revive machine's own lid counted as headroom and
the machine was unreachable.

**Containment is a flood fill.** The play area is computed once from the
spawn, and `cgOutsideAt()` is a second guard. A balcony open to the sky used
to read as indoors, which let you walk out over the roof.

The model came out of SketchUp, which writes every face twice (132,007 of the
triangles are exact coincident duplicates) and exports edges as `LineSegments`
— the cause of a long-running "white lines around everything" bug. If the map
ever renders strangely, count the object types first:

```js
const t = {}; __z.scene.traverse(o => t[o.type] = (t[o.type] || 0) + 1);
```

## The leaderboard

`server/zscores.py` — `BaseHTTPRequestHandler` and sqlite, its own systemd
unit on `127.0.0.1:8951`, reverse-proxied at `/api/zscores`. It validates the
name against `^[A-Za-z0-9 _.\-]{1,16}$`, caps round, kills and points, and
rate-limits to one submission per IP per five seconds. There are no accounts,
so a determined person can still post a fake score; that is the honest trade
for a game you can play without signing up.

`server/caddy-browserzombies.conf` and `server/zscores.service` are the
deployment side.

## Licence

Code is [MIT](LICENSE). The models, animations and textures are not covered by
it — see [ATTRIBUTION.md](ATTRIBUTION.md).

"Kino der Toten" and Call of Duty are trademarks of Activision. This is a fan
project, unaffiliated with and unendorsed by Activision or Treyarch.
