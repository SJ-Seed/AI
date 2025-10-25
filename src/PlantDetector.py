""" 단순 GPT4o 식물인지 아닌지 True/False 반환 """

""" PlantDetector.py
GPT-4o 멀티모달 모델을 이용해
사진에 식물(잎/줄기)이 있는지(True) 없는지(False) 판별합니다.
"""

import os
import json
import base64
from openai import OpenAI
from PIL import Image

# API 키 불러오기
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = json.load(f)
api_key = cfg["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

# 단일 이미지 판별 함수
def analyze_image(image_path):
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")
    prompt = (
        "식물(잎)이 중심인 사진이면 'True', 다른 객체 중심인 사진이면 'False'라고 답하세요"
        "설명은 덧붙이지 마세요."
    )

    response = client.chat.completions.create(
        model='gpt-4o',
        messages=[
            {"role": "system", "content": "You are a plant detector."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]}
        ],
        temperature=0.0
    )

    return response.choices[0].message.content

# 폴더 전체 테스트 함수
def test_dataset(base_dir: str):
    yes_dir = os.path.join(base_dir, "Yes_tomato")
    no_dir = os.path.join(base_dir, "No_tomato")

    total, correct = 0, 0

    print("데이터셋 테스트 시작...\n")

    for label, folder in [("True", yes_dir), ("False", no_dir)]:
        if not os.path.exists(folder):
            print(f"폴더 없음: {folder}")
            continue

        for file in os.listdir(folder):
            if not file.lower().endswith((".jpg", ".jpeg", ".png")):
                continue

            img_path = os.path.join(folder, file)
            result = analyze_image(img_path)

            is_correct = (result.lower() == label.lower())
            status = "정답" if is_correct else "오답"

            print(f"[{status}] {file} → 모델: {result}, 정답: {label}")
            total += 1
            correct += int(is_correct)

    if total > 0:
        accuracy = (correct / total) * 100
        print(f"\n정확도: {accuracy:.2f}% ({correct}/{total})")
    else:
        print("이미지가 없습니다.")

# 메인 실행
if __name__ == "__main__":
    DATA_ROOT = os.path.join(os.path.dirname(__file__), "../data")
    test_dataset(DATA_ROOT)
