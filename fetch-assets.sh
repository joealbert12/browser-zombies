#!/usr/bin/env sh
# Pull the models, animations and textures from the live site.
#
# They are not in this repository on purpose: most are CC-BY and could be,
# but six are not redistributable and the Mixamo character is not either.
# Rather than ship a partial set that leaves the game broken, the whole lot
# lives on the server and is fetched on demand. See ATTRIBUTION.md.
set -eu

BASE="${BASE:-https://browserzombies.fun}"
cd "$(dirname "$0")"

fetch() {
    dir="$1"; remote="$2"; shift 2
    mkdir -p "$dir"
    for f in "$@"; do
        [ -f "$dir/$f" ] && continue
        printf '  %s/%s\n' "$dir" "$f"
        curl -fsS -o "$dir/$f" "$BASE/$remote/$f"
    done
}

echo "fetching from $BASE"
fetch models zmodels \
    bricks.glb broken_pillar.glb chair.glb cinderblock.glb cobweb.glb \
    cornice.glb debris_wood.glb dog.glb kino.glb mp40.glb mysterybox.glb \
    perks.glb pistol.glb pistol2.glb plank.glb powerswitch.glb projector.glb \
    railing.glb rubble.glb seat.glb stage.glb stairs.glb stg44.glb table.glb \
    teleporter.glb theatre.glb window.glb zombie.glb
fetch fbx zfbx anim_attack.fbx anim_die.fbx anim_scream.fbx anim_walk.fbx zombie.fbx
# tex/ is committed (CC0), so nothing to fetch there.

echo "done -- open index.html over http, not file://"
