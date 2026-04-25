from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.debate import run_debate
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI 데이트 플래너", description="멀티에이전트 토론 기반 데이트 코스 추천 API")


class DateRequest(BaseModel):
    query: str


class DateResponse(BaseModel):
    input: str
    debate_rounds: int
    final_course: list
    total_cost: int
    debate_summary: str
    verdict: str


@app.get("/")
def root():
    return {"message": "AI 데이트 플래너 API", "docs": "/docs"}


@app.post("/plan", response_model=DateResponse)
def create_date_plan(request: DateRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="쿼리를 입력해주세요")

    result = run_debate(request.query)
    final = result["final"]

    return DateResponse(
        input=result["input"],
        debate_rounds=result["debate_rounds"],
        final_course=final.get("final_course", []),
        total_cost=final.get("total_cost", 0),
        debate_summary=final.get("debate_summary", ""),
        verdict=final.get("verdict", ""),
    )


@app.get("/health")
def health():
    return {"status": "ok"}
