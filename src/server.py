from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests
import tempfile
import os
from main import main


app = FastAPI()


# JSON Body 정의
class AnalyzeRequest(BaseModel):
    image_path: str
    temperature: str
    humidity: str


@app.post("/analyze")
async def analyze_endpoint(body: AnalyzeRequest):

    # JSON body 파싱
    image_path = body.image_path
    temperature = body.temperature
    humidity = body.humidity

    # S3 이미지 다운로드
    try:
        response = requests.get(image_path)
        if response.status_code != 200:
            return JSONResponse(content={"photo": "이미지를 불러올 수 없습니다."})
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(response.content)
            local_image_path = tmp.name
    except Exception as e:
        return JSONResponse(content={"photo": f"이미지 다운로드 오류: {str(e)}"})

    # main() 실행
    result = main(local_image_path, temperature, humidity)

    # 결과 해석 및 반환
    if not result:
        return JSONResponse(content={
            "photo": False,
            "state": None,
            "message": "식물이 잘 보이지 않아요. 다시 촬영해주세요!"
        })

    elif isinstance(result, str) and result == "Healthy":
        return JSONResponse(content={
            "photo": True,
            "state": "정상",
            "message": "식물이 건강해요!"
        })

    else:
        disease, explained, cause, cure = result
        return JSONResponse(content={
            "photo": True,
            "state": disease,
            "message": "식물이 아파요",
            "explain": explained,
            "cause": cause,
            "cure": cure
        })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
