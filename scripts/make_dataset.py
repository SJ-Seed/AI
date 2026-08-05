"""
데이터셋 생성
"""

import os
import random
import dspy

def build_datasets(data_dir="./data", train_ratio=0.8):
    """폴더별 이미지를 기반으로 trainset / devset 생성"""
    classes = [
        d for d in os.listdir(data_dir)
        if os.path.isdir(os.path.join(data_dir, d))
        and not d.startswith("No_tomato")
        and not d.startswith("Yes_tomato")
    ]

    examples = []
    for cls in classes:
        img_dir = os.path.join(data_dir, cls)
        for fname in os.listdir(img_dir):
            if fname.lower().endswith((".jpg", ".jpeg", ".png")):
                img_path = os.path.join(img_dir, fname)
                examples.append(
                    dspy.Example(
                        image=img_path,
                        answer=cls
                    ).with_inputs("image")
                )

    # 무작위 섞기
    random.shuffle(examples)

    # Train / Dev 분할
    split_idx = int(len(examples) * train_ratio)
    trainset = examples[:split_idx]
    devset = examples[split_idx:]

    print(f"총 {len(examples)}개 이미지 로드 완료")
    print(f"Trainset: {len(trainset)}개")
    print(f"Devset: {len(devset)}개")

    return trainset, devset


# 사용 예시
if __name__ == "__main__":
    trainset, devset = build_datasets("./data")
