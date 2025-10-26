import os
import json
import base64
import dspy
from dspy import Image


# API 키 불러오기
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = json.load(f)
api_key = cfg["OPENAI_API_KEY"]

# LM 설정
lm = dspy.LM(model="gpt-4o", api_key=api_key, temperature=0.0)
dspy.settings.configure(lm=lm)

# 이미지 경로를 base64로 변환
def image_to_dspy_image(image_path: str) -> Image:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return Image(url=f"data:image/jpeg;base64,{b64}")


def analyze_disease(image_path):
    img = image_to_dspy_image(image_path)

    # 컴파일된 프로그램 로드 및 실행
    compiled_program = dspy.load("./compiled_leaf_disease")
    result = compiled_program(image=img)

    # 결과 출력
    return result.answer