"""
DSPy를 이용하여 질병 설명, 원인, 치료 방법을 생성하는 구현체이다.
"""

import dspy


"""
질병 설명 생성을 위한 DSPy 입출력 스키마
"""
class ExplainSignature(dspy.Signature):
    disease: str = dspy.InputField(desc="토마토 질병 이름")
    temperature: str = dspy.InputField(desc="해당 토마토의 일주일 간 온도 변화")
    humidity: str = dspy.InputField(desc="해당 토마토의 일주일 간 습도 변화")
    disease_info: str = dspy.InputField(desc="토마토 각 질병 별 설명")
    explain: str = dspy.OutputField(desc="어린이가 이해하기 쉬운 형태로 질병에 대한 설명(병 이름은 제외)")
    cause: str = dspy.OutputField(desc="어린이가 이해하기 쉬운 형태로 질병의 원인을 작성 (온습도 변화와 관련이 있다면 언급)(병 이름은 제외)")
    cure: str = dspy.OutputField(desc="어린이가 이해하기 쉬운 형태로 질병의 치료 방법을 작성(병 이름은 제외)")


"""
질병 정보와 환경 정보를 바탕으로 설명을 생성하는 DSPy 모듈
"""
class GenerateAnswer(dspy.Module):
    def __init__(self):
        super().__init__()
        self.answerer = dspy.Predict(ExplainSignature)

    """
    질병 설명, 원인, 치료 방법을 생성한다.
    """
    def forward(self, disease, temperature, humidity):
        # 질병 별 설명 및 대응 방법을 LLM에게 함께 제공한다.
        disease_info = """
            토마토 질병에 대한 설명을 보고, 주어진 토마토 질병 이름과 일치하는 설명, 원인, 치료 방법을 파악하세요.
            
            - Bacterial_spot: 습한 환경에서 병원균에 의해 발병, 재배 환경을 청결하게 관리하고 습하지 않도록 통풍과 환기를 잘 시켜야 함
            - Early_blight: 세균, 바이러스, 곰팡이에 감염된 경우 발병, 감염된 잎 제거, 같은 토양에서 다양한 작물 재배, 잎에 물이 닿지 않도록 해야 함
            - Late_blight: 물을 너무 많이 주거나 양분이 부족한 경우, 곰팡이성 병원균에 감염된 경우 발병, 습도를 낮추고 감염된 잎은 즉시 제거해야 함
            - Leaf_mold: 습하고 비가 많이 오는 환경에서 주로 발병, 곰팡이 핀 잎은 즉시 제거, 환기를 통해 습기를 제거해야 함
            - Mosaic_virus: 진딧물 등 해충이나 오염된 토양 등에서 전염된 경우 발병, 병든 잎 제거, 기구, 토양 및 옷 소독, 건강한 토양을 선택해야 함
            - Septoria_leaf_spot: 잎에 수분이 오래 묻은 경우 발병, 잎이 젖어있는 시간 최소화, 고추와 인접 재배하면 안됨
            - Spider_mites_two_spotted_spider_mite: 점박이응애로 인한 피해, 점박이응애가 잎의 즙을 빨아 먹었을 때 발생, 물, 진공청소기 등으로 제거, 습도를 높여 번식을 억제해야 함
            - Yellowleaf_curl_virus: 바이러스를 가지고 있는 담배가루이가 토마토에 접촉한 경우 발병, 방충망 등을 이용해 해충의 침입을 막아야 함
        """
        prediction = self.answerer(
            disease=disease,
            temperature=temperature,
            humidity=humidity,
            disease_info=disease_info,
        )
        return dspy.Prediction(
            explain=prediction.explain,
            cause=prediction.cause,
            cure=prediction.cure,
        )


"""
DiseaseExplainer 인터페이스의 DSPy 구현체
"""
class DspyDiseaseExplainer:
    def __init__(self, predictor, lm) -> None:
        self.predictor = predictor
        self.lm = lm

    def explain(self, disease, temperature, humidity):
        with dspy.context(lm=self.lm):
            result = self.predictor(
                disease=disease,
                temperature=temperature,
                humidity=humidity,
            )
        return result.explain, result.cause, result.cure
