import dspy
import os
import json

""" #0. DSPy 초기 설정 """
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = json.load(f)
api_key = cfg["OPENAI_API_KEY"]
model = dspy.LM(model="gpt-4o", api_key=api_key, temperature=0.5)
dspy.settings.configure(lm=model)


""" #1. 입출력 정의(Signature) """
class ExplainSignature(dspy.Signature):

    # 주어진 사진과 질병 정보를 보고 최종 질병 라벨 반환
    disease: str = dspy.InputField(desc="토마토 질병 이름")
    temperature: str = dspy.InputField(desc="해당 토마토의 일주일 간 온도 변화")
    humidity: str = dspy.InputField(desc="해당 토마토의 일주일 간 습도 변화")
    disease_info: str = dspy.InputField(desc="토마토 각 질병 별 설명")
    explain: str = dspy.OutputField(desc="어린이가 이해하기 쉬운 형태로 질병에 대한 설명")
    cause: str = dspy.OutputField(desc="어린이가 이해하기 쉬운 형태로 질병의 원인을 작성 (온습도 변화와 관련이 있다면 언급)")
    cure: str = dspy.OutputField(desc="어린이가 이해하기 쉬운 형태로 질병의 치료 방법을 작성")


""" #2. 응답 생성을 위한 과정 및 방법 정의(Module) """
class GenerateAnswer(dspy.Module):
    def __init__(self):
        super().__init__()
        self.answerer = dspy.Predict(ExplainSignature)
    
    def forward(self, disease, temperature, humidity):
        disease_info = """
            토마토 질병에 대한 설명을 보고, 주어진 토마토 질병 이름과 일치하는 설명, 원인, 치료 방법을 파악하세요.
            
            - Bacterial_spot: 습한 환경에서 병원균에 의해 발병, 재배 환경을 청결하게 관리하고 습하지 않도록 통풍과 환기를 잘 시켜야 함
            - Early_blight: 세균, 바이러스, 곰팡이에 감염된 경우 발병, 감염된 잎 제거, 같은 토양에서 다양한 작물 재배, 잎에 물이 닿지 않도록 해야 함
            - Late_blight: 물을 너무 많이 주거나 양분이 부족한 경우, 곰팡이성 병원균에 감염된 경우 발병, 습도를 낮추고 감염된 잎은 즉시 제거해야 함
            - Leaf_mold: 습하고 비가 많이 오는 환경에서 주로 발병, 곰팡이 핀 잎은 즉시 제거, 환기를 통해 습기를 제거해야 함
            - Mosiac_virus: 진딧물 등 해충이나 오염된 토양 등에서 전염된 경우 발병, 병든 잎 제거, 기구, 토양 및 옷 소독, 건강한 토양을 선택해야 함
            - Septoria_leaf_spot: 잎에 수분이 오래 묻은 경우 발병, 잎이 젖어있는 시간 최소화, 고추와 인접 재배하면 안됨
            - Spider_mites_two_spotted_spider_mite: 점박이응애로 인한 피해, 점박이응애가 잎의 즙을 빨아 먹었을 때 발생, 물, 진공청소기 등으로 제거, 습도를 높여 번식을 억제해야 함
            - Yellowleaf_curl_virus: 바이러스를 가지고 있는 담배가루이가 토마토에 접촉한 경우 발병, 방충망 등을 이용해 해충의 침입을 막아야 함
        """
        prediction = self.answerer(image=disease, 
                                   temperature=temperature, 
                                   humidity=humidity, 
                                   disease_info=disease_info)
        return dspy.Prediction(explain=prediction.explain, cause=prediction.cause, cure=prediction.cure)
    
predictor = GenerateAnswer()


""" 예시 테스트 """
if __name__ == "__main__":
    disease = "Leaf_mold"
    temperature = "최근 1주일 평균 28도, 최고 32도, 최저 25도"
    humidity = "최근 1주일 평균 습도 85% 이상"

    # Predictor 실행
    result = predictor(
        disease=disease,
        temperature=temperature,
        humidity=humidity
    )

    # 결과 출력
    print("설명:", result.explain)
    print("원인:", result.cause)
    print("치료:", result.cure)
