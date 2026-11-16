#!/usr/bin/env bash
# Push the current main branch to a Hugging Face Space.
#   usage: scripts/deploy-hf.sh <hf-username> [space-name]
# Log in first with:  hf auth login   (or: huggingface-cli login)
set -euo pipefail
USER_NAME="${1:?usage: scripts/deploy-hf.sh <hf-username> [space-name]}"
SPACE="${2:-snipex}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

git -C "$ROOT" worktree add --detach "$TMP/space" main >/dev/null
cd "$TMP/space"
# Spaces read their settings from a block at the top of README.md
{ printf -- '---\ntitle: Snipex\nemoji: 🌀\ncolorFrom: purple\ncolorTo: indigo\nsdk: docker\napp_port: 7860\npinned: false\n---\n\n'; cat README.md; } > README.tmp && mv README.tmp README.md
# Spaces reject big binary files over plain git, and the screenshots aren't needed there
git rm -rq --cached docs && rm -rf docs
git -c user.name="$(git -C "$ROOT" config user.name)" -c user.email="$(git -C "$ROOT" config user.email)" \
    commit -qam "deploy"
git push --force "https://huggingface.co/spaces/$USER_NAME/$SPACE" HEAD:main
cd "$ROOT" && git worktree remove --force "$TMP/space"
echo "Deployed: https://huggingface.co/spaces/$USER_NAME/$SPACE"
