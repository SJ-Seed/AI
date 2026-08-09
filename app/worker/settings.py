"""arq 분석 Worker 실행에 필요한 설정"""

from app.core.config import load_settings, require_redis_url
from app.infrastructure.queue.redis_settings import build_redis_settings
from arq import cron

from app.worker.tasks import process_analysis, reconcile_pending_analyses, shutdown, startup


# Worker 프로세스 시작 시 환경변수와 애플리케이션 설정 로드
_settings = load_settings()


class WorkerSettings:
    """arq CLI가 분석 Worker를 실행할 때 사용하는 설정"""

    # Queue에서 작업을 받으면 실행할 함수
    functions = [process_analysis]

    # Queue 등록이 확인되지 않은 오래된 PENDING 작업을 매분 복구
    cron_jobs = [cron(reconcile_pending_analyses, second=0)]

    # Worker 시작 시 DB, OpenAI 및 AI 모델 자원을 초기화하는 함수
    on_startup = startup

    # Worker 종료 시 DB와 OpenAI 자원을 정리하는 함수
    on_shutdown = shutdown

    # 환경변수의 REDIS_URL을 검증하고 arq Redis 설정으로 변환
    redis_settings = build_redis_settings(require_redis_url(_settings))

    # Worker가 작업을 가져올 Redis Queue 이름
    queue_name = _settings.analysis_queue_name

    # 한 Worker 프로세스가 동시에 처리할 수 있는 작업 수
    max_jobs = 1

    # 최초 실행을 포함한 최대 실행 횟수
    max_tries = _settings.max_retry_count + 1

    # 작업 실패 시 arq가 자동으로 다시 Queue에 넣지 않도록 설정
    retry_jobs = True
