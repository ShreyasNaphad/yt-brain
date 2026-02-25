import os
from pathlib import Path
from dotenv import load_dotenv

# Always load .env from the backend directory
_backend_dir = Path(__file__).resolve().parent.parent
_env_path = _backend_dir / ".env"
load_dotenv(dotenv_path=_env_path)

from groq import Groq
import json
import logging
import time
from typing import List, Dict, Any
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.error(f"GROQ_API_KEY not found! .env path: {_env_path}, exists: {_env_path.exists()}")
            self.client = None
        else:
            self.client = Groq(api_key=api_key)
            logger.info("Groq client initialized successfully")

        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    def chat_completion(self, messages: List[Dict[str, str]], max_tokens: int = 300, temperature: float = 0.3) -> str:
        if not self.client:
            raise Exception("LLM Service not available - GROQ_API_KEY missing")

        max_retries = 3
        base_delay = 2

        for attempt in range(max_retries):
            try:
                chat_completion = self.client.chat.completions.create(
                    messages=messages,
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=30
                )
                return chat_completion.choices[0].message.content
            except Exception as e:
                error_str = str(e).lower()
                if "rate limit" in error_str or "connection" in error_str or "429" in error_str:
                    if attempt < max_retries - 1:
                        sleep_time = base_delay * (2 ** attempt) + (0.1 * attempt)
                        logger.warning(f"Groq API error: {e}. Retrying in {sleep_time:.2f}s...")
                        time.sleep(sleep_time)
                        continue

                logger.error(f"Error in chat completion: {e}")
                raise Exception(f"LLM error: {str(e)}")

        raise Exception("Maximum retries exceeded for LLM service.")

    def chat_completion_json(self, messages: List[Dict[str, str]], max_tokens: int = 800) -> Dict[str, Any]:
        if not self.client:
            raise Exception("LLM Service not available - GROQ_API_KEY missing")

        max_retries = 3
        base_delay = 2

        for attempt in range(max_retries):
            try:
                chat_completion = self.client.chat.completions.create(
                    messages=messages,
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=0.1,
                    timeout=30,
                    response_format={"type": "json_object"}
                )
                response = chat_completion.choices[0].message.content
                return json.loads(response)
            except json.JSONDecodeError as e:
                logger.error(f"JSON PARSE ERROR: {e}\nRaw response: {response[:500]}")
                if attempt == max_retries - 1:
                    raise Exception(f"AI response parse error: {str(e)}")
            except Exception as e:
                error_str = str(e).lower()
                if "rate limit" in error_str or "connection" in error_str or "429" in error_str:
                    if attempt < max_retries - 1:
                        sleep_time = base_delay * (2 ** attempt) + (0.1 * attempt)
                        time.sleep(sleep_time)
                        continue
                if attempt == max_retries - 1:
                    raise Exception(f"AI error: {str(e)}")
        
        raise Exception("Maximum retries exceeded for LLM service JSON.")


# Module-level singleton
llm_service = LLMService()
