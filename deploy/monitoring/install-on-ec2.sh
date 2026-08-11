#!/usr/bin/env bash
# EC2에 모니터링 시스템을 자동 설치하는 초기 설정 스크립트
set -euo pipefail

# 관리자 권한 확인
if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo." >&2
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
AGENT_CTL="/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl"
AGENT_CONFIG="/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"

# 서버 CPU 확인
case "$(uname -m)" in
  x86_64)
    PACKAGE_ARCH="amd64"
    ;;
  aarch64|arm64)
    PACKAGE_ARCH="arm64"
    ;;
  *)
    echo "Unsupported architecture." >&2
    exit 1
    ;;
esac

# CloudWatch Agent 설치
if [[ ! -x "${AGENT_CTL}" ]]; then
  PACKAGE_FILE="$(mktemp --suffix=.deb)"
  trap 'rm -f -- "${PACKAGE_FILE:-}"' EXIT
  PACKAGE_URL="https://amazoncloudwatch-agent.s3.amazonaws.com/ubuntu/${PACKAGE_ARCH}/latest/amazon-cloudwatch-agent.deb"

  curl --fail --silent --show-error --location "${PACKAGE_URL}" --output "${PACKAGE_FILE}"
  dpkg --install "${PACKAGE_FILE}"
fi


install -D -m 0644 \
  "${SCRIPT_DIR}/amazon-cloudwatch-agent.json" \
  "${AGENT_CONFIG}"
install -D -m 0755 \
  "${SCRIPT_DIR}/health_probe.py" \
  "/usr/local/lib/sjseed-monitoring/health_probe.py"
install -m 0755 \
  "${SCRIPT_DIR}/stream-docker-logs.sh" \
  "/usr/local/lib/sjseed-monitoring/stream-docker-logs.sh"
install -m 0644 \
  "${SCRIPT_DIR}/sjseed-health-probe.service" \
  "/etc/systemd/system/sjseed-health-probe.service"
install -m 0644 \
  "${SCRIPT_DIR}/sjseed-health-probe.timer" \
  "/etc/systemd/system/sjseed-health-probe.timer"
install -m 0644 \
  "${SCRIPT_DIR}/sjseed-docker-logs.service" \
  "/etc/systemd/system/sjseed-docker-logs.service"
install -m 0644 \
  "${SCRIPT_DIR}/sjseed-application.logrotate" \
  "/etc/logrotate.d/sjseed-application"

install -d -m 0750 /etc/sjseed-monitoring
printf 'SJSEED_PROJECT_DIR="%s"\n' "${PROJECT_DIR//\"/\\\"}" \
  > /etc/sjseed-monitoring/environment
chmod 0640 /etc/sjseed-monitoring/environment

install -d -o root -g adm -m 0750 /var/log/sjseed
touch /var/log/sjseed/application.log
chown root:adm /var/log/sjseed/application.log
chmod 0640 /var/log/sjseed/application.log

systemctl daemon-reload
systemctl enable --now sjseed-docker-logs.service
"${AGENT_CTL}" \
  -a fetch-config \
  -m ec2 \
  -c "file:${AGENT_CONFIG}" \
  -s
systemctl enable --now sjseed-health-probe.timer
systemctl start sjseed-health-probe.service

"${AGENT_CTL}" -a status
systemctl --no-pager status sjseed-health-probe.timer
