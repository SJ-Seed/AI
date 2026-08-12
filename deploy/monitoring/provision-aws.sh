#!/usr/bin/env bash
# AWS 쪽 모니터링 리소스와 장애 이메일 알림을 자동으로 구성하는 스크립트
set -euo pipefail

# Prevent Git Bash/MSYS from converting AWS resource names such as
# /sjseed/ai/docker into Windows filesystem paths.
case "${MSYSTEM:-}" in
  MINGW*|MSYS*)
    export MSYS2_ARG_CONV_EXCL='*'
    ;;
esac

AWS_REGION="${AWS_REGION:-ap-northeast-2}"
INSTANCE_ID="${INSTANCE_ID:-}"
ALERT_EMAIL="${ALERT_EMAIL:-}"
TOPIC_NAME="${TOPIC_NAME:-sjseed-ai-operations}"
ALARM_PREFIX="${ALARM_PREFIX:-sjseed-ai}"
LOG_GROUP_NAME="/sjseed/ai/docker"
AGENT_POLICY_ARN="arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"

usage() {
  echo "Usage: $0 --instance-id INSTANCE_ID --email ALERT_EMAIL [--region REGION] [--topic-name NAME]" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --instance-id)
      INSTANCE_ID="${2:-}"
      shift 2
      ;;
    --email)
      ALERT_EMAIL="${2:-}"
      shift 2
      ;;
    --region)
      AWS_REGION="${2:-}"
      shift 2
      ;;
    --topic-name)
      TOPIC_NAME="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if [[ -z "${INSTANCE_ID}" || -z "${ALERT_EMAIL}" ]]; then
  usage
  exit 2
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "Required command is not installed: aws" >&2
  exit 1
fi

aws_region() {
  aws --region "${AWS_REGION}" "$@"
}

aws sts get-caller-identity --output json >/dev/null

FOUND_INSTANCE_ID="$(
  aws_region ec2 describe-instances \
    --instance-ids "${INSTANCE_ID}" \
    --query 'Reservations[0].Instances[0].InstanceId' \
    --output text
)"
if [[ "${FOUND_INSTANCE_ID}" != "${INSTANCE_ID}" ]]; then
  echo "The target EC2 instance was not found in the selected region." >&2
  exit 1
fi

PROFILE_ARN="$(
  aws_region ec2 describe-instances \
    --instance-ids "${INSTANCE_ID}" \
    --query 'Reservations[0].Instances[0].IamInstanceProfile.Arn' \
    --output text
)"

if [[ -n "${PROFILE_ARN}" && "${PROFILE_ARN}" != "None" ]]; then
  PROFILE_NAME="${PROFILE_ARN##*/}"
  ROLE_NAME="$(
    aws iam get-instance-profile \
      --instance-profile-name "${PROFILE_NAME}" \
      --query 'InstanceProfile.Roles[0].RoleName' \
      --output text
  )"
  if [[ -z "${ROLE_NAME}" || "${ROLE_NAME}" == "None" ]]; then
    echo "The existing EC2 instance profile has no role." >&2
    exit 1
  fi
else
  ROLE_NAME="sjseed-ai-cloudwatch-agent"
  PROFILE_NAME="sjseed-ai-cloudwatch-agent"
  TRUST_POLICY='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

  if ! aws iam get-role --role-name "${ROLE_NAME}" >/dev/null 2>&1; then
    aws iam create-role \
      --role-name "${ROLE_NAME}" \
      --assume-role-policy-document "${TRUST_POLICY}" \
      >/dev/null
    aws iam wait role-exists --role-name "${ROLE_NAME}"
  fi

  if ! aws iam get-instance-profile --instance-profile-name "${PROFILE_NAME}" >/dev/null 2>&1; then
    aws iam create-instance-profile \
      --instance-profile-name "${PROFILE_NAME}" \
      >/dev/null
  fi

  PROFILE_ROLE="$(
    aws iam get-instance-profile \
      --instance-profile-name "${PROFILE_NAME}" \
      --query 'InstanceProfile.Roles[0].RoleName' \
      --output text
  )"
  if [[ -z "${PROFILE_ROLE}" || "${PROFILE_ROLE}" == "None" ]]; then
    aws iam add-role-to-instance-profile \
      --instance-profile-name "${PROFILE_NAME}" \
      --role-name "${ROLE_NAME}"
  elif [[ "${PROFILE_ROLE}" != "${ROLE_NAME}" ]]; then
    echo "The monitoring instance profile contains an unexpected role." >&2
    exit 1
  fi

  for attempt in {1..12}; do
    if aws_region ec2 associate-iam-instance-profile \
      --instance-id "${INSTANCE_ID}" \
      --iam-instance-profile "Name=${PROFILE_NAME}" \
      >/dev/null 2>&1; then
      break
    fi
    if [[ "${attempt}" -eq 12 ]]; then
      echo "The instance profile could not be associated with EC2." >&2
      exit 1
    fi
    sleep 5
  done
fi

aws iam attach-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-arn "${AGENT_POLICY_ARN}"

TOPIC_ARN="$(
  aws_region sns create-topic \
    --name "${TOPIC_NAME}" \
    --query 'TopicArn' \
    --output text
)"

SUBSCRIPTION_ARN="$(
  aws_region sns list-subscriptions-by-topic \
    --topic-arn "${TOPIC_ARN}" \
    --query "Subscriptions[?Protocol=='email' && Endpoint=='${ALERT_EMAIL}'].SubscriptionArn | [0]" \
    --output text
)"
if [[ -z "${SUBSCRIPTION_ARN}" || "${SUBSCRIPTION_ARN}" == "None" ]]; then
  aws_region sns subscribe \
    --topic-arn "${TOPIC_ARN}" \
    --protocol email \
    --notification-endpoint "${ALERT_EMAIL}" \
    >/dev/null
fi

if ! aws_region logs describe-log-groups \
  --log-group-name-prefix "${LOG_GROUP_NAME}" \
  --query "logGroups[?logGroupName=='${LOG_GROUP_NAME}'].logGroupName | [0]" \
  --output text | grep -Fxq "${LOG_GROUP_NAME}"; then
  aws_region logs create-log-group --log-group-name "${LOG_GROUP_NAME}"
fi
aws_region logs put-retention-policy \
  --log-group-name "${LOG_GROUP_NAME}" \
  --retention-in-days 30

put_alarm() {
  local alarm_name="$1"
  local namespace="$2"
  local metric_name="$3"
  local statistic="$4"
  local period="$5"
  local evaluation_periods="$6"
  local datapoints_to_alarm="$7"
  local threshold="$8"
  local comparison_operator="$9"
  local missing_data="${10}"
  local description="${11}"

  aws_region cloudwatch put-metric-alarm \
    --alarm-name "${ALARM_PREFIX}-${INSTANCE_ID}-${alarm_name}" \
    --alarm-description "${description}" \
    --namespace "${namespace}" \
    --metric-name "${metric_name}" \
    --dimensions "Name=InstanceId,Value=${INSTANCE_ID}" \
    --statistic "${statistic}" \
    --period "${period}" \
    --evaluation-periods "${evaluation_periods}" \
    --datapoints-to-alarm "${datapoints_to_alarm}" \
    --threshold "${threshold}" \
    --comparison-operator "${comparison_operator}" \
    --treat-missing-data "${missing_data}" \
    --alarm-actions "${TOPIC_ARN}" \
    --ok-actions "${TOPIC_ARN}"
}

put_alarm "cpu-high" "AWS/EC2" "CPUUtilization" "Average" 300 1 1 80 \
  "GreaterThanOrEqualToThreshold" "breaching" "EC2 CPU usage is at least 80 percent for five minutes."
put_alarm "memory-high" "SJSeed/AI" "mem_used_percent" "Average" 300 1 1 80 \
  "GreaterThanOrEqualToThreshold" "breaching" "EC2 memory usage is at least 80 percent for five minutes."
put_alarm "disk-high" "SJSeed/AI" "disk_used_percent" "Average" 300 1 1 80 \
  "GreaterThanOrEqualToThreshold" "breaching" "EC2 root disk usage is at least 80 percent for five minutes."
put_alarm "status-instance-failed" "AWS/EC2" "StatusCheckFailed_Instance" "Maximum" 60 2 2 1 \
  "GreaterThanOrEqualToThreshold" "missing" "The EC2 instance status check failed twice in succession."
put_alarm "status-system-failed" "AWS/EC2" "StatusCheckFailed_System" "Maximum" 60 2 2 1 \
  "GreaterThanOrEqualToThreshold" "missing" "The EC2 system status check failed twice in succession."
put_alarm "health-api-down" "SJSeed/AI" "HealthApi" "Minimum" 60 2 2 0 \
  "LessThanOrEqualToThreshold" "breaching" "The local API health probe failed twice in succession."
put_alarm "health-postgresql-down" "SJSeed/AI" "HealthPostgresql" "Minimum" 60 2 2 0 \
  "LessThanOrEqualToThreshold" "notBreaching" "PostgreSQL readiness failed twice in succession."
put_alarm "health-redis-down" "SJSeed/AI" "HealthRedis" "Minimum" 60 2 2 0 \
  "LessThanOrEqualToThreshold" "notBreaching" "Redis readiness failed twice in succession."

echo "AWS monitoring resources are configured. Confirm the pending SNS email subscription."
echo "SNS topic: ${TOPIC_ARN}"
