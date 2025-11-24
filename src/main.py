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
    if is_plant == "False":    # 식물 사진이 아닌 경우 멈춤
        return "식물아님", None, None, None
    

    """ 2. 입력된 사진의 질병을 판별 """
    disease = analyze_disease(image_path)
    # 만약 건강하다면 Healthy 반환
    if disease == "Healthy":
        return "정상", None, None, None
    

    """ 3. 질병 설명 제공 """
    explained, cause, cure = explain(disease, temperature, humidity)
    # 질병 이름 한국어로 변환
    if disease == "Bacterial_spot":
        disease = "세균성 점무늬병"
    elif disease == "Early_blight":
        disease = "반점병"
    elif disease == "Late_blight":
        disease = "잎마름병"
    elif disease == "Leaf_mold":
        disease = "잎곰팡이병"
    elif disease == "Mosaic_virus":
        disease = "모자이크병"
    elif disease == "Septoria_leaf_spot":
        disease = "흰별무늬병"
    elif disease == "Spider_mites_two_spotted_spider_mite":
        disease = "점박이응애로 인한 피해"
    elif disease == "Yellowleaf_curl_virus":
        disease = "황화잎말림 바이러스"
    return disease, explained, cause, cure


if __name__ == "__main__":
    # image_path = "./data/Leaf_mold/16.jpeg"
    image_path = "./data/No_tomato/2.jpg"
    temperature = "최근 1주일 평균 28도, 최고 32도, 최저 25도"
    humidity = "최근 1주일 평균 습도 85% 이상"

    disease, explained, cause, cure = main(image_path, temperature, humidity)

    print("disease: ", disease)
    print("explained: ", explained)
    print("cause: ", cause)
    print("cure: ", cure)
    