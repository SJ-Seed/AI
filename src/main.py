import dspy
from openai import OpenAI
import os
import json
import base64
import dspy
import time
from PlantDetector import analyze_image
from PlantDoctor import analyze_disease
from ExplainDiseaseForKids import explain


def main(image_path, temperature, humidity):

    """ 1. 입력된 사진이 식물 사진인지 판별 """
    for _ in range(0, 5):
        is_plant = analyze_image(image_path)
        if is_plant in ["True", "False"]:
            break
        time.sleep(1.5)
    if not is_plant:    # 식물 사진이 아닌 경우 멈춤
        return None
    

    """ 2. 입력된 사진의 질병을 판별 """
    disease = analyze_disease(image_path)
    # 만약 건강하다면 Healthy 반환
    if disease == "Healthy":
        return disease
    

    """ 3. 질병 설명 제공 """
    explained, cause, cure = explain(disease, temperature, humidity)
    return disease, explained, cause, cure


if __name__ == "__main__":
    image_path = "./data/Leaf_mold/16.jpeg"
    temperature = "최근 1주일 평균 28도, 최고 32도, 최저 25도"
    humidity = "최근 1주일 평균 습도 85% 이상"

    disease, explained, cause, cure = main(image_path, temperature, humidity)
    print("disease: ", disease)
    print("explained: ", explained)
    print("cause: ", cause)
    print("cure: ", cure)
    