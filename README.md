# 🌱 쑥쑥 자라라 씨앗아, '쑥자씨' (SJ-Seed)

**중앙대학교 캡스톤디자인(1) 팀 프로젝트**

> **초등학생을 위한 IoT & AI 기반 스마트 반려 식물 교육 플랫폼**
> 아날로그 방식의 식물 키우기를 넘어, 데이터를 통해 식물과 교감하고 과학적 사고력을 기르는 에듀테크(Edu-Tech) 어플리케이션입니다.

|                                               OnBoarding                                                |                                                  Home                                                   |                                                Hospital                                                 |
| :-----------------------------------------------------------------------------------------------------: | :-----------------------------------------------------------------------------------------------------: | :-----------------------------------------------------------------------------------------------------: |
| <img src="https://github.com/user-attachments/assets/39460c1e-4f37-4cba-8d91-02e1254b2c0b" width="250"> | <img src="https://github.com/user-attachments/assets/2932cd53-de8b-4575-b1d6-645a203c0195" width="250"> | <img src="https://github.com/user-attachments/assets/f8706282-3d1e-49f9-a6e3-27d0b92a1a05" width="250"> |

<br/>

## 📖 프로젝트 개요 (Overview)

기존의 식물 키우기 활동은 초등학생들에게 자칫 지루하고 반복적인 과정으로 느껴질 수 있습니다.

**쑥자씨**는 이러한 아날로그 방식을 디지털로 전환하여, 아이들이 스스로 식물의 상태를 파악하고 과학적 원리를 체험하며 즐겁게 식물을 키울 수 있도록 돕습니다. 아두이노 센서 데이터와 AI 기술을 활용하여 식물의 생장 과정을 논리적으로 이해하고, 자연과학적 사고력을 함양하는 것을 목표로 합니다.

<br/>

## 💡 주요 기능 (Key Features)

### 1. 🌿 IoT 기반 실시간 상태 모니터링 & 눈높이 설명

아두이노 센서를 통해 식물의 **온도, 습도, 토양 수분 데이터**를 실시간으로 수집합니다.

- **눈높이 상태 알림:** 딱딱한 수치 대신 "목이 말라요", "너무 추워요" 등 초등학생이 직관적으로 이해할 수 있는 캐릭터(쑥자씨)의 대사로 변환하여 알려줍니다.
- **스마트 물주기 가이드:** 토양 수분 센서 데이터를 바탕으로 사용자가 식물에게 물을 올바르게 주고 있는지 파악하고 피드백을 제공합니다.

### 2. 🏥 AI 식물 병원 & 과학적 원인 분석

식물에 이상이 생겼을 때, 사진 한 장으로 질병을 진단하고 원인을 과학적으로 분석합니다.

- **AI 질병 진단:** 촬영된 식물 사진을 AI가 분석하여 질병명, 주요 증상, 예방법 및 맞춤형 치료법을 제시합니다.
- **데이터 기반 원인 규명:** 단순히 병명만 알려주는 것이 아니라, 지금까지 기록된 **온도/습도 데이터와 질병의 인과관계를 설명**해줌으로써 아이들이 환경과 식물 건강의 상관관계를 과학적으로 이해하도록 돕습니다.

### 3. 📖 게이미피케이션 & 식물 도감 (Reward System)

지속적인 학습과 관리에 대한 동기를 부여하기 위해 흥미로운 보상 시스템을 도입했습니다.

- **보상 시스템:** 앱 접속(출석), 올바른 물주기, 병든 식물 치료 등 긍정적인 행동을 할 때마다 코인을 획득합니다.
- **나만의 도감 채우기:** 획득한 코인으로 '식물 조각 뽑기'를 진행하여 다양한 식물 조각을 모으고, 나만의 도감을 완성하며 성취감을 느낄 수 있습니다.

<br/>

## 🛠 기술 스택 (Tech Stack)

### Backend

- Python 3.11
- FastAPI
- Pydantic
- SQLAlchemy 2.x (Async)
- Alembic

### Database & Queue

- PostgreSQL
- asyncpg
- Redis 7
- arq

### Infrastructure

- Docker / Docker Compose
- FastAPI API Container
- arq Worker Container
- Redis Queue
- AWS EC2
- Amazon S3
- GitHub Container Registry (GHCR)
- GitHub Actions

<br/>

## 🎯 기대 효과 (Expected Effect)

1.  **과학적 사고력 증진:** 데이터를 기반으로 식물의 상태 변화 원인을 추론하며 논리적 사고력을 기릅니다.
2.  **자기 주도적 학습:** AI의 가이드에 따라 스스로 식물을 관찰하고 돌보는 과정을 통해 문제 해결 능력을 키웁니다.
3.  **정서 함양:** 디지털 펫(캐릭터)과의 상호작용을 통해 생명에 대한 애정과 책임감을 배웁니다.

<br/>

## 🐳 Docker 실행 방법

### 사전 준비

- Docker Compose v2가 설치되어 있어야 합니다.
- 프로젝트 루트에 학습된 DSPy 모델 디렉터리인 `compiled_leaf_disease/`가 있어야 합니다.
- `.env.example`을 복사하여 `.env` 파일을 만들고 `OPENAI_API_KEY`, PostgreSQL, Redis 연결 정보를 설정합니다.

> `.env`에는 API 키와 같은 민감한 값이 포함되므로 Docker 이미지에 포함하거나 Git에 커밋하지 마세요.

### Docker Compose로 실행

이미지를 빌드하고 컨테이너를 백그라운드에서 실행합니다.

```bash
docker compose up --build -d
```

실행 후 [http://localhost:8000/docs](http://localhost:8000/docs)에서 API 문서를 확인할 수 있습니다.

로그 확인:

```bash
docker compose logs -f ai
```

컨테이너 중지 및 제거:

```bash
docker compose down
```

코드나 의존성이 변경된 경우 캐시 없이 다시 빌드할 수 있습니다.

```bash
docker compose build --no-cache
docker compose up -d
```

호스트의 8000 포트가 이미 사용 중이라면 `compose.yaml`의 `ports`에서 왼쪽 호스트 포트를 다른 값으로 변경하세요. 예를 들어 `8001:8000`으로 변경하면 `http://localhost:8001`로 접속할 수 있습니다.

### Docker 명령으로 직접 실행

Docker Compose 없이 실행하려면 다음 명령을 사용합니다.

이 경우 컨테이너에서 접근할 수 있는 PostgreSQL과 Redis가 별도로 실행 중이어야 합니다.

```bash
docker build -t sjseed-ai .
docker run --rm --env-file .env -p 8000:8000 sjseed-ai
```

<br/>

## ☁️ Cloud Infrastructure & Deployment

AWS와 GitHub Actions를 기반으로 Docker 이미지 빌드부터 EC2 배포까지 자동화된 배포 환경을 구성했습니다.

### Architecture

- **Amazon EC2**
  - Ubuntu 기반 애플리케이션 서버
  - Docker / Docker Compose를 이용한 컨테이너 실행
  - Elastic IP를 이용한 고정 IP 구성

- **Amazon S3**
  - 학습된 DSPy 모델(`compiled_leaf_disease`) 저장
  - Git에 포함하지 않는 모델 아티팩트 관리

- **AWS IAM**
  - GitHub Actions OIDC 인증을 통한 S3 접근 권한 관리
  - 장기 AWS Access Key 없이 모델 다운로드

- **GitHub Container Registry (GHCR)**
  - 빌드된 FastAPI Docker 이미지 저장
  - `latest` 및 Commit SHA 기반 이미지 태그 관리

- **GitHub Actions**
  - `main` 브랜치 반영 시 CD Workflow 실행
  - S3에서 모델 다운로드
  - Docker 이미지 빌드 및 GHCR Push
  - EC2에 배포 후 Health Check 수행

### Deployment Architecture

```text
                  Amazon S3
          compiled_leaf_disease
                       │
                       │ OIDC / IAM
                       ▼
                GitHub Actions
                       │
              Docker Image Build
                       │
                       ▼
                     GHCR
                       │
                 Docker Pull
                       │
                       ▼
+--------------------------------------------------+
|                  Amazon EC2                      |
|--------------------------------------------------|
| Ubuntu                                           |
| Docker / Docker Compose                          |
| FastAPI Container                                |
| arq Worker Container                             |
| PostgreSQL                                       |
| Redis Queue                                      |
+--------------------------------------------------+
                       │
                       ▼
                 GET /health
```

### Deployment Flow

`main` 브랜치에 변경사항이 반영되면 다음 과정으로 자동 배포됩니다.

```text
main Push / Merge
        ↓
S3 모델 다운로드
        ↓
Docker 이미지 빌드
        ↓
GHCR Push
        ↓
EC2 SSH 접속
        ↓
최신 이미지 Pull
        ↓
Docker Compose 재배포
        ↓
Health Check
```

배포된 애플리케이션의 상태는 `/health` 엔드포인트를 통해 확인합니다.

### 운영 상태 확인 및 CloudWatch 모니터링

#### 상태 확인 API

상태 확인 엔드포인트는 용도에 따라 다음과 같이 구분합니다.

| 엔드포인트 | 확인 범위 | 정상 응답 | 장애 응답 |
| --- | --- | --- | --- |
| `/health/live` | FastAPI 프로세스 | `200` | 프로세스가 응답하지 않음 |
| `/health`, `/health/ready` | API, PostgreSQL, Redis | 모두 정상이면 `200` | 의존 서비스 하나라도 비정상이면 `503` |

```bash
curl -i http://localhost:8000/health/live
curl -i http://localhost:8000/health
```

Readiness 응답은 서비스를 구분해 반환합니다.

```json
{
  "status": "healthy",
  "services": {
    "api": {"status": "up"},
    "postgresql": {"status": "up"},
    "redis": {"status": "up"}
  }
}
```

#### 최초 모니터링 구성

모니터링 구성은 `deploy/monitoring`에 있으며 다음 순서로 한 번 적용합니다. AWS 설정 스크립트를 다시 실행하면 기존 SNS topic, IAM role과 Alarm을 갱신해 재사용합니다.

사전 조건:

- 로컬 실행 환경에 AWS CLI v2가 설치되고 대상 계정으로 인증되어 있어야 합니다.
- 실행 주체에는 EC2 조회·instance profile 연결, IAM role/policy, CloudWatch, CloudWatch Logs, SNS 설정 권한이 필요합니다.
- 대상 EC2에 SSH와 `sudo`로 접근할 수 있어야 합니다.

먼저 AWS 리소스를 구성합니다. instance ID와 이메일은 예시 값으로 바꾸며 저장소 파일에 기록하지 않습니다.

```bash
AWS_REGION=ap-northeast-2 bash deploy/monitoring/provision-aws.sh \
  --instance-id i-0123456789abcdef0 \
  --email operator@example.com
```

스크립트는 기존 EC2 instance profile을 재사용하거나 전용 profile을 연결하고, CloudWatch Agent 권한, SNS topic, 30일 보존 로그 그룹과 Alarm을 구성합니다. 새 SNS 이메일 구독은 AWS가 보낸 메일의 **Confirm subscription** 링크를 눌러야 알림을 받을 수 있습니다.

그다음 EC2의 최신 저장소에서 Agent와 1분 주기 health probe를 설치합니다.

```bash
cd ~/opt/AI
sudo bash deploy/monitoring/install-on-ec2.sh
```

Agent 설정을 변경한 경우에도 같은 설치 명령을 다시 실행하면 새 설정이 반영됩니다.

#### 수집 지표와 Alarm

CloudWatch Agent 지표와 서비스 상태 지표는 `SJSeed/AI`, EC2 기본 지표는 `AWS/EC2` namespace에서 확인합니다.

| Alarm | 조건 | 누락 데이터 처리 |
| --- | --- | --- |
| CPU | 5분 평균 `CPUUtilization >= 80%` | 장애 |
| 메모리 | 5분 평균 `mem_used_percent >= 80%` | 장애 |
| 루트 디스크 | 5분 평균 `disk_used_percent >= 80%` | 장애 |
| EC2 instance/system 상태 검사 | 1분 간격 2회 연속 실패 | 유지 |
| API | `HealthApi == 0` 2회 연속 | 장애 |
| PostgreSQL | `HealthPostgresql == 0` 2회 연속 | 정상 |
| Redis | `HealthRedis == 0` 2회 연속 | 정상 |

API에 연결하지 못하면 PostgreSQL과 Redis 상태를 추측하지 않고 해당 지표를 생략합니다. 따라서 API Alarm이 probe나 Agent 자체의 데이터 누락까지 감지하고, 의존 서비스 Alarm은 `/health`가 명시적으로 `down`을 반환할 때만 발생합니다. 모든 Alarm은 ALARM과 OK 전환을 같은 SNS topic으로 알립니다.

#### 운영 확인

EC2에서 Agent와 timer 상태를 확인합니다.

```bash
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a status
systemctl status sjseed-health-probe.timer
systemctl list-timers sjseed-health-probe.timer
journalctl -u sjseed-health-probe.service --since "10 minutes ago"
```

API와 worker의 Docker 로그는 EC2의 `/var/log/sjseed/application.log`에 스트리밍된 뒤 `/sjseed/ai/docker` CloudWatch Logs group에 30일간 저장됩니다. 로그 스트리밍 서비스는 설치 이후 새로 발생한 항목만 전달하며, 호스트 파일은 매일 순환해 7개를 보관합니다. 분석 상태 로그는 CloudWatch Logs Insights에서 다음처럼 찾을 수 있습니다.

```text
fields @timestamp, @message
| filter @message like /analysis_status_changed/
| sort @timestamp desc
| limit 100
```

이 로그에는 `analysis_id`, `status`, `duration_ms`, `retry_count`, `failure_reason`이 포함되며 원본 예외, API key, DB/Redis 접속 URL은 기록하지 않습니다.

SNS 전달 경로는 서비스를 중단하지 않고 다음 명령으로 확인할 수 있습니다. Alarm 이름은 대상 instance ID에 맞게 변경합니다.

```bash
aws cloudwatch set-alarm-state \
  --region ap-northeast-2 \
  --alarm-name sjseed-ai-i-0123456789abcdef0-health-api-down \
  --state-value ALARM \
  --state-reason "monitoring verification"

aws cloudwatch set-alarm-state \
  --region ap-northeast-2 \
  --alarm-name sjseed-ai-i-0123456789abcdef0-health-api-down \
  --state-value OK \
  --state-reason "monitoring verification complete"
```

실제 의존 서비스 장애 검증은 운영 트래픽이 없는 점검 시간에만 수행합니다. Redis 또는 PostgreSQL 컨테이너를 하나씩 중단하고 `/health`의 `503` 및 해당 서비스 `down`, 2분 뒤 Alarm과 이메일을 확인한 다음 즉시 컨테이너를 복구하고 `/health`와 OK 알림을 다시 확인합니다. 두 의존 서비스를 동시에 중단하거나 데이터 volume을 삭제하지 않습니다.

<br/>

## ⚙️ 비동기 AI 분석 구조

AI 분석은 HTTP 요청에서 직접 실행하지 않고 Redis Queue와 별도 Worker를 통해 비동기로 처리합니다.

1. FastAPI가 분석 요청을 DB에 `PENDING` 상태로 저장합니다.
2. Redis Queue에 `analysis_id`를 등록합니다.
3. API는 분석 완료를 기다리지 않고 `202 Accepted`를 반환합니다.
4. Worker가 작업을 가져와 `PROCESSING` 상태로 변경합니다.
5. 이미지 다운로드와 AI 분석을 수행합니다.
6. 성공하면 `COMPLETED`, 재시도할 수 있는 오류가 발생하면 `PENDING` 상태로 되돌린 뒤 다시 처리합니다.
7. 재시도할 수 없는 오류가 발생하거나 최대 재시도 횟수를 모두 소진하면 `FAILED` 상태로 저장합니다.

```text
Client
  │ POST /analyze
  ▼
FastAPI ── 작업 생성 ──▶ PostgreSQL
  │
  ├── 202 Accepted ──▶ Client
  │
  └── analysis_id ──▶ Redis Queue
                           │
                           ▼
                       arq Worker
                           │
                이미지 다운로드·AI 분석
                           │
                           ▼
                       PostgreSQL
```
