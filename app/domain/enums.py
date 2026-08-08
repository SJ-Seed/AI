"""
질병 이름 매핑
"""

from enum import Enum


class AnalysisStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

DISEASE_NAMES_KO = {
    "Bacterial_spot": "세균성 점무늬병",
    "Early_blight": "반점병",
    "Late_blight": "잎마름병",
    "Leaf_mold": "잎곰팡이병",
    "Mosaic_virus": "모자이크병",
    "Septoria_leaf_spot": "흰별무늬병",
    "Spider_mites_two_spotted_spider_mite": "점박이응애로 인한 피해",
    "Yellowleaf_curl_virus": "황화잎말림 바이러스",
}
