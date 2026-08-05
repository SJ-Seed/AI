"""
OpenAI Vision 모델을 이용하여 이미지가 식물인지 판별하는 구현체이다.
"""

import base64
import os

"""
PlantDetector 인터페이스의 OpenAI 구현체
"""
class OpenAIPlantDetector:
    def __init__(self, client) -> None:
        self.client = client

    """
    이미지를 분석하여 식물 여부를 반환한다.
    """
    def analyze_image(self, image_path):
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        prompt = (
            "식물(잎)이 중심인 사진이면 'True', 다른 객체 중심인 사진이면 'False'라고 답하세요"
            "설명은 덧붙이지 마세요."
        )

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a plant detector."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
                ]},
            ],
            temperature=0.0,
        )
        return response.choices[0].message.content

    """
    테스트 데이터셋에 대해 식물 판별 정확도를 측정한다.
    """
    def test_dataset(self, base_dir: str):
        yes_dir = os.path.join(base_dir, "Yes_tomato")
        no_dir = os.path.join(base_dir, "No_tomato")
        total, correct = 0, 0
        print("데이터셋 테스트 시작...\n")

        # True/False 데이터셋을 순회하며 모델의 예측 결과를 검증한다.
        for label, folder in [("True", yes_dir), ("False", no_dir)]:
            if not os.path.exists(folder):
                print(f"폴더 없음: {folder}")
                continue
            for file in os.listdir(folder):
                if not file.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue
                img_path = os.path.join(folder, file)
                result = self.analyze_image(img_path)
                is_correct = result.lower() == label.lower()
                status = "정답" if is_correct else "오답"
                print(f"[{status}] {file} → 모델: {result}, 정답: {label}")
                total += 1
                correct += int(is_correct)
        if total > 0:
            accuracy = (correct / total) * 100
            print(f"\n정확도: {accuracy:.2f}% ({correct}/{total})")
        else:
            print("이미지가 없습니다.")
