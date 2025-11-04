""" 순수 GPT의 정확도를 테스트 """
import json
from openai import OpenAI
import base64
from src.make_dataset import build_datasets
import time

# config.json에서 API 키 불러오기
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

api_key = config["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

# 사진 입력 후 테스트
def test_gpt_with_image(image_path):
    question = """
            아래 중 주어진 이미지가 어떤 질병의 시각적 특징과 가장 유사한지 판단하세요.

            1. Bacterial_spot: 잎/줄기에 작고 어두운 반점이 여러 개 생김.
            2. Early_blight: 잎에 크고 어두운 원형의 고리무늬 반점 존재, 점 안에 동심원이 보임.
            3. Healthy: 병반이 없음, 녹색 균일.
            4. Late_blight: 잎이 어둡게 혹은 노랗게 시들거나 흰 곰팡이층이 생김, 시들어보임.
            5. Leaf_mold: 잎에 노란색/갈색 곰팡이층(여러 개의 반점).
            6. Mosaic_virus: 잎이 얼룩덜룩한(노랑/초록) 무늬, 색이 불균형, 쭈글쭈글.
            7. Septoria_leaf_spot: 중앙이 흰색인 가장자리 검은 점 여러 개, 점의 크기는 작은 편.
            8. Spider_mites_two_spotted_spider_mite: 매우 작고 미세한 하얀 점들 존재.
            9. Yellowleaf_curl_virus: 잎의 가장자리가 말리고 노랗게 변함.

            정답 레이블.
            Bacterial_spot, Early_blight, Healthy, Late_blight,
            Leaf_mold, Mosaic_virus, Septoria_leaf_spot,
            Spider_mites_two_spotted_spider_mite, Yellowleaf_curl_virus 
            중에 그대로 작성.
        """
    with open(image_path, "rb") as f:
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"}}
                    ]
                }
            ]
        )

    return response.choices[0].message.content

# 데이터셋 구축
dataset, _ = build_datasets(train_ratio=1)

total = 0
correct = 0

for data in dataset:
    total += 1
    image_path = data.image
    gt = data.answer
    pred = test_gpt_with_image(image_path)
    if gt.strip().lower() == pred.strip().lower():
        correct += 1
    time.sleep(1.5)

result = (correct / total) * 100
print(f"{result:.2f}%")