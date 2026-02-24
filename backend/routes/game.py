from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from services.cache_service import cache
from services.llm_service import llm_service

router = APIRouter(tags=["game"]) # Prefix in main.py
logger = logging.getLogger(__name__)

class Question(BaseModel):
    id: int
    difficulty: str
    type: str
    question: str
    options: Optional[List[str]] = None
    correct: str # For client side validation of easy/medium, or just internal? 
                 # Requirement says "correct: A" or model answer.
                 # We probably shouldn't send correct answer to client for easy validation if we want security, 
                 # but for this app, sending it is fine or we validate on backend.
                 # The prompt implies structure is sent to frontend? 
                 # "Return questions" usually means to frontend. 
                 # Let's include it.
    explanation: Optional[str] = None
    start_time: Optional[int] = None

class QuestionsResponse(BaseModel):
    questions: List[Question]

class GradeRequest(BaseModel):
    question: str
    correct_answer: str
    user_answer: str
    difficulty: str

class GradeResponse(BaseModel):
    score: int
    feedback: str
    xp_earned: int

class GameResult(BaseModel):
    id: int
    correct: bool # or score
    
class GameCompleteRequest(BaseModel):
    video_id: str
    results: List[Any] # just list for now, or specific model
    total_xp: int

class GameCompleteResponse(BaseModel):
    level: str
    xp: int
    comprehension_score: float
    weakest_concept: Optional[str] = None


@router.get("/{video_id}/questions")
async def get_questions(video_id: str):
    try:
        cached = cache.get(f"questions:{video_id}")
        if cached:
            return cached
        
        transcript = cache.get(f"transcript:{video_id}")
        if not transcript:
            raise HTTPException(status_code=400, detail="Video not processed yet")
        
        # Sample from beginning, middle, and end for full coverage
        max_section = 1700
        if len(transcript) > max_section * 3:
            beginning = transcript[:max_section]
            mid_start = len(transcript) // 2 - max_section // 2
            middle = transcript[mid_start:mid_start + max_section]
            ending = transcript[-max_section:]
            trimmed = f"{beginning}\n\n{middle}\n\n{ending}"
        else:
            trimmed = transcript
        
        messages = [
            {
                "role": "user",
                "content": f"""Based on this video information, generate exactly 15 quiz questions.
Return ONLY valid JSON, no markdown, no explanation outside the JSON.

{{
  "questions": [
    {{
      "id": 1,
      "difficulty": "easy",
      "type": "mcq",
      "question": "question text",
      "options": ["A. option1", "B. option2", "C. option3", "D. option4"],
      "correct": "A",
      "explanation": "friend-like, natural explanation directly answering why it's correct without ever mentioning 'the transcript', 'the video', or saying 'it is given in...'",
      "start_time": 0
    }}
  ]
}}

Rules:
- Questions 1-5: difficulty=easy, type=mcq, simple factual questions
- Questions 6-10: difficulty=medium, type=mcq, conceptual questions  
- Questions 11-15: difficulty=hard, type=open (no options array needed, correct=full answer string)
- ALL questions must be based only on the information below.
- The `explanation` field MUST respond naturally as a friend, without mentioning source material.
- For open questions set options to empty array []

INFORMATION:
{trimmed}"""
            }
        ]
        
        result = llm_service.chat_completion_json(messages, max_tokens=1500)
        
        # Validate structure
        if "questions" not in result:
            raise HTTPException(status_code=500, detail="Invalid questions format from AI")
        
        cache.set(f"questions:{video_id}", result, ttl=86400*30)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"GAME ERROR: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/grade", response_model=GradeResponse)
async def grade_answer(request: GradeRequest):
    # Only called for hard/open questions usually
    prompt = (
        f"Grade this answer 0-3. Question: {request.question}. "
        f"Expected: {request.correct_answer}. Student answer: {request.user_answer}. "
        "Return ONLY JSON: {'score': 0-3, 'feedback': 'one friendly, encouraging sentence talking directly to the user as a friend, without mentioning transcript or video.'}"
    )
    
    messages = [{"role": "user", "content": prompt}]
    
    try:
        result = llm_service.chat_completion_json(messages)
        score = result.get("score", 0)
        feedback = result.get("feedback", "")
    except Exception as e:
        logger.error(f"Grading failed: {e}")
        score = 0
        feedback = "Error grading answer."

    xp = score * 10
    return GradeResponse(score=score, feedback=feedback, xp_earned=xp)

@router.post("/complete", response_model=GameCompleteResponse)
async def complete_game(request: GameCompleteRequest):
    xp = request.total_xp
    
    # Calculate Level
    level = "Listener"
    if xp >= 300:
        level = "Master"
    elif xp >= 150:
        level = "Analyst"
    elif xp >= 50:
        level = "Thinker"
        
    # Calculate Comprehension Score
    # Assuming max possible score is based on questions count.
    # 15 questions. 
    # Easy (5) * 10xp = 50
    # Medium (5) * 20xp = 100? Or just 10?
    # Logic says "XP to Level". 
    # Let's just create a heuristic for comprehension based on XP or provide a raw calculation.
    # Requirement: "Calculate: comprehension_score (percentage)"
    # Let's assume max XP is ~300-400?
    # Hard (5) * 30xp (score 3 * 10)?
    # 5*10 + 5*20 + 5*30 = 50+100+150 = 300 XP Max?
    # If so, comprehension = (xp / 300) * 100
    
    max_xp = 300 # Estimated
    comprehension_score = min((xp / max_xp) * 100, 100.0)
    
    return GameCompleteResponse(
        level=level,
        xp=xp,
        comprehension_score=comprehension_score,
        weakest_concept="None" # placeholder
    )
