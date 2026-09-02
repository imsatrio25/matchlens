#!/usr/bin/env bash
set -euo pipefail
# ponytail: one script to deploy anywhere — local or VPS via SSH
# Usage: ./deploy.sh              # local docker compose up
#        ./deploy.sh user@1.2.3.4  # rsync + remote compose up

VPS="${1:-}"
if [ -z "$VPS" ]; then
  echo ">> Local deploy: docker compose up --build -d"
  docker compose up --build -d
  echo ">> Waiting 15s for seed..."
  sleep 15
  curl -s http://localhost:5181/api/health | cat
  curl -s http://localhost:5181/api/galaxy | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"galaxy {len(d['nodes'])} nodes\")"
  echo ">> Done: http://localhost:5180  +  http://localhost:5181/api/health"
  exit 0
fi

# Remote deploy
echo ">> Deploying to $VPS ..."
rsync -avz --exclude '.git' --exclude 'frontend/node_modules' --exclude 'frontend/.next' --exclude '__pycache__' --exclude '.env' ./ "$VPS:~/matchlens/"
ssh "$VPS" <<'EOSSH'
set -e
cd ~/matchlens
# install docker if missing
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker $USER
fi
# env
if [ ! -f .env ]; then
  echo "OPENROUTER_API_KEY=sk-or-v1-..." > .env
  echo "POSTGRES_PASSWORD=matchlens_secret" >> .env
  echo "NEXT_PUBLIC_API_URL=http://$(curl -s ifconfig.me):5181/api" >> .env
  echo ">> Created .env — EDIT IT: nano ~/matchlens/.env"
fi
docker compose up --build -d
sleep 15
curl -s http://localhost:5181/api/health || echo "backend not yet ready"
EOSSH
echo ">> Remote done. Edit $VPS:~/matchlens/.env then ssh $VPS 'cd ~/matchlens && docker compose up --build -d'"
