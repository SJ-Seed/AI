"""
FastAPI 앱 생성 및 서버 초기화

- 애플리케이션 생성
- 라우터 등록
- 서비스 및 AI 모델 초기화
- 애플리케이션 생명주기 관리
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.analysis import router as analysis_router
from app.core.config import load_settings

"""
애플리케이션 시작 시 필요한 리소스 초기화
"""
@asynccontextmanager
async def lifespan(app: FastAPI):
    
    import dspy
    from openai import OpenAI

    from app.application.services.diagnosis_service import DiagnosisService
    from app.infrastructure.ai.disease_explainer import DspyDiseaseExplainer, GenerateAnswer
    from app.infrastructure.ai.dspy_classifier import DspyDiseaseClassifier
    from app.infrastructure.ai.openai_detector import OpenAIPlantDetector
    from app.infrastructure.image.image_downloader import ImageDownloader

    settings = load_settings()

    # OpenAI API 클라이언트 생성
    openai_client = OpenAI(api_key=settings.openai_api_key)

    # 질병 분류에 사용할 DSPy 언어 모델 생성 (결과 일관성을 위해 temperature=0.0)
    classifier_lm = dspy.LM(
        model="gpt-4o",
        api_key=settings.openai_api_key,
        temperature=0.0,
    )

    # 질병 설명 생성에 사용할 DSPy 언어 모델 생성 (자연스러운 설명 생성을 위해 temperature=0.5)
    explainer_lm = dspy.LM(
        model="gpt-4o",
        api_key=settings.openai_api_key,
        temperature=0.5,
    )

    # 학습된 DSPy 프로그램 로드
    compiled_program = dspy.load(str(settings.model_path))

    # 애플리케이션 전역에서 사용할 서비스 생성
    app.state.diagnosis_service = DiagnosisService(
        detector=OpenAIPlantDetector(openai_client),
        classifier=DspyDiseaseClassifier(compiled_program, classifier_lm),
        explainer=DspyDiseaseExplainer(GenerateAnswer(), explainer_lm),
    )

    # 이미지 다운로드 유틸리티 등록
    app.state.image_downloader = ImageDownloader()
    yield

"""
FaskAPI 애플리케이션을 생성하고 라우터 등록
"""
def create_app() -> FastAPI:
    application = FastAPI(lifespan=lifespan)
    # 분석 API 등록
    application.include_router(analysis_router)
    return application

# 애플리케이션 생성
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
