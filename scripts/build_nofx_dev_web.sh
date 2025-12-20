#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTERNAL_DIR="${ROOT_DIR}/external/nofx-dev"
REPO_URL="${NOFX_REPO_URL:-https://github.com/NoFxAiOS/nofx.git}"
BRANCH="${NOFX_REPO_BRANCH:-dev}"
DIST_OUT="${ROOT_DIR}/web/nofx_dist"

mkdir -p "${ROOT_DIR}/external"

if [[ ! -d "${EXTERNAL_DIR}/.git" ]]; then
  echo "[NOFX] Cloning ${REPO_URL} (${BRANCH}) -> ${EXTERNAL_DIR}"
  git clone --depth 1 --branch "${BRANCH}" "${REPO_URL}" "${EXTERNAL_DIR}"
else
  echo "[NOFX] Updating ${EXTERNAL_DIR} -> origin/${BRANCH}"
  git -C "${EXTERNAL_DIR}" fetch origin "${BRANCH}" --depth 1
  git -C "${EXTERNAL_DIR}" checkout "${BRANCH}"
  git -C "${EXTERNAL_DIR}" reset --hard "origin/${BRANCH}"
fi

MAIN_TSX="${EXTERNAL_DIR}/web/src/main.tsx"
if [[ -f "${MAIN_TSX}" ]] && ! grep -q 'basename={import.meta.env.BASE_URL}' "${MAIN_TSX}"; then
  echo "[NOFX] Patching React Router basename for /nofx"
  sed -i.bak 's/<BrowserRouter>/<BrowserRouter basename={import.meta.env.BASE_URL}>/g' "${MAIN_TSX}"
  rm -f "${MAIN_TSX}.bak"
fi

pushd "${EXTERNAL_DIR}/web" >/dev/null
echo "[NOFX] Installing frontend dependencies (npm ci)"
npm ci
echo "[NOFX] Building frontend (base=/nofx/)"
npm run build -- --base=/nofx/
popd >/dev/null

rm -rf "${DIST_OUT}"
mkdir -p "${DIST_OUT}"
cp -R "${EXTERNAL_DIR}/web/dist/." "${DIST_OUT}/"

echo "[NOFX] Done. Output: ${DIST_OUT}"

