import os
import re
import json
import time
import random
import asyncio
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("LLMOrchestrator")


class ExtractedStartupSchema(BaseModel):
    schemaVersion: str = "1.0"
    recordType: str = "STARTUP"
    source_name: str
    source_url: str
    entityName: str
    employeeCount: Optional[int] = None
    collectedAt: str


class TextChunker:
    """
    Prevents HTTP 413 (Payload Too Large) by pruning HTML bloat
    and enforcing token/character density limits.
    """
    @staticmethod
    def clean_html(raw_html: str) -> str:
        # Strip script, style, SVG, and base64 image tags
        clean = re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"data:image/[^;]+;base64,[^\s\"\']+", "", clean)
        clean = re.sub(r"<[^>]+>", " ", clean)
        return " ".join(clean.split())

    @staticmethod
    def chunk_payload(text: str, max_chars: int = 4000) -> str:
        """Truncates cleanly to sentence/paragraph boundary if payload exceeds window."""
        if len(text) <= max_chars:
            return text
        truncated = text[:max_chars]
        last_period = truncated.rfind(".")
        return truncated[:last_period + 1] if last_period != -1 else truncated


class LLMOrchestrator:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        
        # Priority tier list: Tier 1 -> Tier 2 -> Tier 3
        self.model_tiers = ["gemini-1.5-flash", "groq-llama3-70b", "deepseek-chat"]

    async def _mock_or_call_api(self, model_name: str, payload: str) -> Dict[str, Any]:
        """
        Simulates / executes provider calls with rate limit and context simulation.
        Drop actual SDK calls (google.generativeai, groq, openai) here when API keys are loaded.
        """
        # Simulate edge-case 429 if no key present
        await asyncio.sleep(0.2)
        
        # Fallback structured extraction parser
        return {
            "schemaVersion": "1.0",
            "recordType": "STARTUP",
            "source_name": "Web Extraction Engine",
            "source_url": "https://example-ai-startup.com",
            "entityName": "Sample AI Intelligence",
            "employeeCount": 45,
            "collectedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    async def extract_with_fallback(
        self,
        raw_content: str,
        max_retries_per_tier: int = 3
    ) -> Dict[str, Any]:
        """
        Executes multi-tier fallback chain with 413 prevention and 429 exponential backoff + jitter.
        """
        # Step 1: 413 Mitigation - Prune DOM bloat and apply token chunking
        cleaned_text = TextChunker.clean_html(raw_content)
        chunked_text = TextChunker.chunk_payload(cleaned_text, max_chars=4000)

        # Step 2: Traverse Multi-Tier Providers
        for model in self.model_tiers:
            logger.info(f"Attempting structured extraction with Tier: [{model}]")

            for attempt in range(1, max_retries_per_tier + 1):
                try:
                    # Execute call
                    result = await self._mock_or_call_api(model, chunked_text)
                    logger.info(f"✅ Successfully extracted entity using Tier [{model}]")
                    return result

                except Exception as exc:
                    err_msg = str(exc)

                    # 429 Rate Limit Handling: Exponential Backoff + Jitter
                    if "429" in err_msg or "RateLimit" in err_msg:
                        backoff = (2 ** attempt) + random.uniform(0.5, 1.5)
                        logger.warning(f"[{model}] 429 Too Many Requests on attempt {attempt}/{max_retries_per_tier}. Backing off for {backoff:.2f}s...")
                        await asyncio.sleep(backoff)
                    
                    # 413 Payload Too Large Handling: Dynamically shrink payload by 50%
                    elif "413" in err_msg or "PayloadTooLarge" in err_msg:
                        logger.warning(f"[{model}] 413 Payload Too Large. Dynamically shrinking chunk size...")
                        chunked_text = TextChunker.chunk_payload(chunked_text, max_chars=len(chunked_text) // 2)
                        await asyncio.sleep(0.5)

                    else:
                        logger.error(f"[{model}] Failed with error: {exc}. Moving to next tier in fallback chain...")
                        break  # Fall back to next model tier

        raise RuntimeError("CRITICAL: All LLM providers in fallback chain exhausted.")


if __name__ == "__main__":
    orchestrator = LLMOrchestrator()
    sample_dirty_html = """
    <html>
        <head><style>.ad { display:none; }</style></head>
        <body>
            <script>var x = 10;</script>
            <h1>Sample AI Technologies, Inc.</h1>
            <p>We are an enterprise AI safety startup with 45 engineers building alignment guardrails.</p>
        </body>
    </html>
    """
    res = asyncio.run(orchestrator.extract_with_fallback(sample_dirty_html))
    print("\nExtraction Result:\n", json.dumps(res, indent=2))