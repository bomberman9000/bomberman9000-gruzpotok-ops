#!/usr/bin/env bash
# Сборка образов compose + теги для registry (аналог scripts/pack.ps1).
# IMAGE_TAG, REGISTRY, IMAGE_PREFIX — переменные окружения.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TAG="${IMAGE_TAG:-}"
if [[ -z "$TAG" ]]; then
  TAG="$(git -C "$ROOT" describe --tags --always 2>/dev/null || true)"
fi
TAG="${TAG:-local}"
PREFIX="${IMAGE_PREFIX:-gruzpotok}"
export COMPOSE_PROJECT_NAME=gruzpotok

echo "==> compose project: $COMPOSE_PROJECT_NAME, tag: $TAG"

NO_CACHE_FLAG=()
if [[ "${NO_CACHE:-}" == "1" ]]; then
  NO_CACHE_FLAG=(--no-cache)
fi

docker compose -f docker-compose.yml build "${NO_CACHE_FLAG[@]}" rag-api gruzpotok-backend postgres-backup

tag_one() {
  local service="$1"
  local short="$2"
  local src="gruzpotok-${service}:latest"
  local dst
  if [[ -n "${REGISTRY:-}" ]]; then
    dst="${REGISTRY}/${PREFIX}/${short}:${TAG}"
  else
    dst="${PREFIX}/${short}:${TAG}"
  fi
  docker tag "$src" "$dst"
  echo "  tagged $dst"
}

echo "==> registry tags:"
tag_one rag-api rag-api
tag_one gruzpotok-backend backend
tag_one postgres-backup postgres-backup

if [[ "${SLIM_RAG:-}" == "1" ]]; then
  SLIM_TAG="${TAG}-slim"
  if [[ -n "${REGISTRY:-}" ]]; then
    SLIM_FULL="${REGISTRY}/${PREFIX}/rag-api:${SLIM_TAG}"
  else
    SLIM_FULL="${PREFIX}/rag-api:${SLIM_TAG}"
  fi
  echo "==> slim rag-api -> $SLIM_FULL"
  docker build -f rag-service/Dockerfile.slim -t "$SLIM_FULL" rag-service
fi

if [[ "${FRONTEND:-}" == "1" ]]; then
  echo "==> frontend build"
  (cd frontend && (test -f package-lock.json && npm ci || npm install) && npm run build)
  echo "  artifact: frontend/dist"
fi

echo "==> done"
