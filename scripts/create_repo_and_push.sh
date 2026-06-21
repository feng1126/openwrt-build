#!/usr/bin/env bash
set -euo pipefail

# Create a GitHub repo, push this workflow, and trigger the build.
# Required:
#   export GITHUB_TOKEN=ghp_xxx
# Optional:
#   export GITHUB_OWNER=your_user_or_org
#   export REPO_NAME=openwrt-xg040gmd-build

REPO_NAME="${REPO_NAME:-openwrt-xg040gmd-build}"
GITHUB_API="${GITHUB_API:-https://api.github.com}"

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "ERROR: set GITHUB_TOKEN first. GitHub password is not supported." >&2
  exit 1
fi

if [ -z "${GITHUB_OWNER:-}" ]; then
  GITHUB_OWNER="$(
    curl -fsS \
      -H "Authorization: Bearer ${GITHUB_TOKEN}" \
      -H "Accept: application/vnd.github+json" \
      "${GITHUB_API}/user" | python3 -c 'import json,sys; print(json.load(sys.stdin)["login"])'
  )"
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

echo "Owner: ${GITHUB_OWNER}"
echo "Repo : ${REPO_NAME}"

if ! curl -fsS \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "${GITHUB_API}/repos/${GITHUB_OWNER}/${REPO_NAME}" >/dev/null; then
  echo "Creating repository..."
  curl -fsS -X POST \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "${GITHUB_API}/user/repos" \
    -d "{\"name\":\"${REPO_NAME}\",\"private\":true,\"auto_init\":false}" >/dev/null
fi

if [ ! -d .git ]; then
  git init
fi

git config user.name "${GIT_USER_NAME:-feng}"
git config user.email "${GIT_USER_EMAIL:-460708473@qq.com}"

git add README.md .github/workflows/build-xg040gmd.yml scripts/create_repo_and_push.sh
git commit -m "Add XG-040G-MD OpenWrt GitHub Actions build" || true
git branch -M main

REMOTE_URL="https://github.com/${GITHUB_OWNER}/${REPO_NAME}.git"
git remote remove origin 2>/dev/null || true
git remote add origin "${REMOTE_URL}"
GIT_AUTH_HEADER="$(
  printf 'x-access-token:%s' "${GITHUB_TOKEN}" | base64 | tr -d '\n'
)"
git -c "http.extraHeader=AUTHORIZATION: Basic ${GIT_AUTH_HEADER}" push -u origin main

echo "Triggering workflow..."
curl -fsS -X POST \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "${GITHUB_API}/repos/${GITHUB_OWNER}/${REPO_NAME}/actions/workflows/build-xg040gmd.yml/dispatches" \
  -d '{"ref":"main","inputs":{"pr_id":"23569","base_branch":"main"}}'

echo
echo "Triggered."
echo "Open: https://github.com/${GITHUB_OWNER}/${REPO_NAME}/actions"
