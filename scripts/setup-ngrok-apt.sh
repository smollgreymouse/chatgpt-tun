#!/usr/bin/env bash
# Configure ngrok's official APT repository, without editing any existing
# CTUN/ngrok user configuration or installing/running the agent.
set -euo pipefail
if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run with sudo: sudo bash scripts/setup-ngrok-apt.sh" >&2
  exit 1
fi
command -v curl >/dev/null || { echo "curl required" >&2; exit 1; }
install -d -m 0755 /etc/apt/keyrings
curl --fail --silent --show-error --location \
  https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
  -o /etc/apt/keyrings/ngrok.asc
chmod 0644 /etc/apt/keyrings/ngrok.asc
printf '%s\n' 'deb [signed-by=/etc/apt/keyrings/ngrok.asc] https://ngrok-agent.s3.amazonaws.com bookworm main' \
  > /etc/apt/sources.list.d/ngrok.list
apt-get update
echo "ngrok APT repository configured. Install CTUN with: sudo apt install ./chatgpt-tun_VERSION_amd64.deb"
