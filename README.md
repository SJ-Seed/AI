# 🌱 쑥쑥 자라라 씨앗아, '쑥자씨' (SJ-Seed)
**중앙대학교 캡스톤디자인(1) 팀 프로젝트**
>
> **초등학생을 위한 IoT & AI 기반 스마트 반려 식물 교육 플랫폼**
> 아날로그 방식의 식물 키우기를 넘어, 데이터를 통해 식물과 교감하고 과학적 사고력을 기르는 에듀테크(Edu-Tech) 어플리케이션입니다.

| OnBoarding | Home | Hospital |
| :---: | :---: | :---: |
| <img src="https://github.com/user-attachments/assets/39460c1e-4f37-4cba-8d91-02e1254b2c0b" width="250"> | <img src="https://github.com/user-attachments/assets/2932cd53-de8b-4575-b1d6-645a203c0195" width="250"> | <img src="https://github.com/user-attachments/assets/f8706282-3d1e-49f9-a6e3-27d0b92a1a05" width="250"> |

<br/>

## 📖 프로젝트 개요 (Overview)

기존의 식물 키우기 활동은 초등학생들에게 자칫 지루하고 반복적인 과정으로 느껴질 수 있습니다. 

**쑥자씨**는 이러한 아날로그 방식을 디지털로 전환하여, 아이들이 스스로 식물의 상태를 파악하고 과학적 원리를 체험하며 즐겁게 식물을 키울 수 있도록 돕습니다. 아두이노 센서 데이터와 AI 기술을 활용하여 식물의 생장 과정을 논리적으로 이해하고, 자연과학적 사고력을 함양하는 것을 목표로 합니다.

<br/>

## 💡 주요 기능 (Key Features)

### 1. 🌿 IoT 기반 실시간 상태 모니터링 & 눈높이 설명
아두이노 센서를 통해 식물의 **온도, 습도, 토양 수분 데이터**를 실시간으로 수집합니다.
* **눈높이 상태 알림:** 딱딱한 수치 대신 "목이 말라요", "너무 추워요" 등 초등학생이 직관적으로 이해할 수 있는 캐릭터(쑥자씨)의 대사로 변환하여 알려줍니다.
* **스마트 물주기 가이드:** 토양 수분 센서 데이터를 바탕으로 사용자가 식물에게 물을 올바르게 주고 있는지 파악하고 피드백을 제공합니다.

### 2. 🏥 AI 식물 병원 & 과학적 원인 분석
식물에 이상이 생겼을 때, 사진 한 장으로 질병을 진단하고 원인을 과학적으로 분석합니다.
* **AI 질병 진단:** 촬영된 식물 사진을 AI가 분석하여 질병명, 주요 증상, 예방법 및 맞춤형 치료법을 제시합니다.
* **데이터 기반 원인 규명:** 단순히 병명만 알려주는 것이 아니라, 지금까지 기록된 **온도/습도 데이터와 질병의 인과관계를 설명**해줌으로써 아이들이 환경과 식물 건강의 상관관계를 과학적으로 이해하도록 돕습니다.

### 3. 📖 게이미피케이션 & 식물 도감 (Reward System)
지속적인 학습과 관리에 대한 동기를 부여하기 위해 흥미로운 보상 시스템을 도입했습니다.
* **보상 시스템:** 앱 접속(출석), 올바른 물주기, 병든 식물 치료 등 긍정적인 행동을 할 때마다 코인을 획득합니다.
* **나만의 도감 채우기:** 획득한 코인으로 '식물 조각 뽑기'를 진행하여 다양한 식물 조각을 모으고, 나만의 도감을 완성하며 성취감을 느낄 수 있습니다.

<br/>

## 🛠 기술 스택 (Tech Stack)

| Category | Technologies |
| --- | --- |
| **Mobile (iOS)** | ![Swift](https://img.shields.io/badge/Swift-5.9-F05138?logo=swift) ![SwiftUI](https://img.shields.io/badge/SwiftUI-MVVM-blue) ![Xcode](https://img.shields.io/badge/Xcode-15.0+-147EFB?logo=xcode) |
| **Hardware (IoT)** | ![Arduino](https://img.shields.io/badge/Arduino-UNO-00979D?logo=arduino) (Temp/Hum/Soil Sensors) |
| **Network** | `URLSession`, `REST API` |
| **Concurrency** | `Swift Concurrency (async/await)`, `Combine` |
| **Collaboration** | ![Git](https://img.shields.io/badge/Git-F05032?logo=git) ![GitHub](https://img.shields.io/badge/GitHub-181717?logo=github) |

<br/>

## 🎯 기대 효과 (Expected Effect)
1.  **과학적 사고력 증진:** 데이터를 기반으로 식물의 상태 변화 원인을 추론하며 논리적 사고력을 기릅니다.
2.  **자기 주도적 학습:** AI의 가이드에 따라 스스로 식물을 관찰하고 돌보는 과정을 통해 문제 해결 능력을 키웁니다.
3.  **정서 함양:** 디지털 펫(캐릭터)과의 상호작용을 통해 생명에 대한 애정과 책임감을 배웁니다.

<br/>
