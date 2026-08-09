"""
모델 학습 및 컴파일
"""

import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))
    
import dspy
from app.core.config import load_settings, require_openai_api_key
from dspy.teleprompt import MIPROv2
from dspy.evaluate import Evaluate
from scripts.make_dataset import build_datasets

""" #0. DSPy 초기 설정 """
api_key = require_openai_api_key(load_settings())
model = dspy.LM(model="gpt-4o", api_key=api_key, temperature=0)
dspy.settings.configure(lm=model)


""" #1. 입출력 정의 """
class DiseaseSignature(dspy.Signature):

    # 주어진 사진과 질병 정보를 보고 최종 질병 라벨 반환
    image: dspy.Image = dspy.InputField(desc="토마토 잎/줄기 사진")
    disease_info: str = dspy.InputField(desc="토마토 각 질병 별 설명 (시각적 특징)")
    answer: str = dspy.OutputField(desc="정답 레이블. "
        "Bacterial_spot, Early_blight, Healthy, Late_blight, "
        "Leaf_mold, Mosaic_virus, Septoria_leaf_spot, "
        "Spider_mites_two_spotted_spider_mite, Yellowleaf_curl_virus "
        "중에 그대로 작성.")


""" #2. 응답 생성을 위한 과정 및 방법 정의 """
class GenerateAnswer(dspy.Module):
    def __init__(self):
        super().__init__()
        self.answerer = dspy.Predict(DiseaseSignature)
    
    def forward(self, image):
        disease_info = """
            아래 중 어떤 질병의 시각적 특징과 가장 유사한지 판단하세요.

            1. Bacterial_spot: 잎/줄기에 작고 어두운 반점이 여러 개 생김.
            2. Early_blight: 잎에 크고 어두운 원형의 고리무늬 반점 존재, 점 안에 동심원이 보임.
            3. Healthy: 병반이 없음, 녹색 균일.
            4. Late_blight: 잎이 어둡게 혹은 노랗게 시들거나 흰 곰팡이층이 생김, 시들어보임.
            5. Leaf_mold: 잎에 노란색/갈색 곰팡이층(여러 개의 반점).
            6. Mosaic_virus: 잎이 얼룩덜룩한(노랑/초록) 무늬, 색이 불균형, 쭈글쭈글.
            7. Septoria_leaf_spot: 중앙이 흰색인 가장자리 검은 점 여러 개, 점의 크기는 작은 편.
            8. Spider_mites_two_spotted_spider_mite: 매우 작고 미세한 하얀 점들 존재.
            9. Yellowleaf_curl_virus: 잎의 가장자리가 말리고 노랗게 변함.
        """
        image = dspy.Image.from_file(image)
        prediction = self.answerer(image=image, disease_info=disease_info)
        return dspy.Prediction(answer=prediction.answer)

predictor = GenerateAnswer()


""" #3. 프롬프트 최적화 """
trainset, devset = build_datasets()

# 성능 평가 metric 정의 (간단한 문자열 비교)
def metric(example, pred, trace=None):
    gold_label = example.answer.strip()
    predicted_label = pred.answer.strip()

    # 정답 문자열과 예측이 정확히 일치하는지 확인
    is_correct = predicted_label == gold_label

    # 최적화 과정 중일 땐 bool, 평가 단계에서는 float
    if trace is not None:
        return is_correct
    return 1.0 if is_correct else 0.0

# 프롬프트 최적화 Optimizer 설정
teleprompter = MIPROv2(metric=metric)
compiled_program = teleprompter.compile(
    GenerateAnswer(),
    trainset=trainset,
)
compiled_program.save("./compiled_leaf_disease", save_program=True)


""" #4. Evaluation """
evaluation = Evaluate(devset=devset, metric=metric, display_progress=True, display_table=True, num_threads=1)
eval_result = evaluation(compiled_program)

print(f"Evaluation result: {eval_result}")
