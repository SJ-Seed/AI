""" API 연결 테스트 전용 파일 """
import json
import openai

# config.json에서 API 키 불러오기
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

api_key = config["OPENAI_API_KEY"]
client = openai.OpenAI(api_key=api_key)

# 연결 테스트
try:
    response = client.responses.create(
        model="gpt-4o-mini",
        input="API 연결 테스트 중이에요. 연결이 된다면 '네'로 응답하세요."
    )
    print("연결 성공")
    print("모델 응답:", response.output[0].content[0].text)

except Exception as e:
    print("연결 실패!")
    print("에러 내용:", e)