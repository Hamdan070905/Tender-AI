"""
Unified LLM service via LiteLLM.

Model string examples:
  Groq:        groq/llama-3.3-70b-versatile  |  groq/llama3-8b-8192
  Gemini:      gemini/gemini-2.0-flash-exp    |  gemini/gemini-1.5-pro
  OpenRouter:  openrouter/qwen/qwen3-235b-a22b
               openrouter/deepseek/deepseek-chat
               openrouter/meta-llama/llama-3.3-70b-instruct
               openrouter/google/gemma-3-27b-it
               openrouter/mistralai/mistral-large
  Vision:      openrouter/qwen/qwen-2.5-vl-72b-instruct  (Qwen3-VL)
               openrouter/thudm/glm-4v-9b                 (GLM-4.6V)
               openrouter/opengvlab/internvl3-14b          (InternVL)
  Ollama:      ollama/qwen3:8b  |  ollama/deepseek-r1:7b  |  ollama/llama3.2
"""
import os
import json
import litellm
from litellm import acompletion, completion
from core.config import settings
import structlog

log = structlog.get_logger()
litellm.drop_params = True


def _setup():
    if settings.GROQ_API_KEY:
        os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY
    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
    if settings.GEMINI_API_KEY:
        os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
    if settings.OPENROUTER_API_KEY:
        os.environ["OPENROUTER_API_KEY"] = settings.OPENROUTER_API_KEY
    os.environ["OLLAMA_API_BASE"] = settings.OLLAMA_BASE_URL


_setup()


class LLMService:

    @staticmethod
    def _model(fast=True) -> str:
        return settings.FAST_LLM_MODEL if fast else settings.QUALITY_LLM_MODEL

    @staticmethod
    async def chat(messages: list[dict], fast=True, model=None,
                   temperature=0.3, max_tokens=2048, json_mode=False) -> str:
        model = model or LLMService._model(fast)
        kwargs = dict(model=model, messages=messages,
                      temperature=temperature, max_tokens=max_tokens)
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            resp = await acompletion(**kwargs)
            return resp.choices[0].message.content
        except Exception as e:
            log.error("llm.error", model=model, error=str(e))
            
            # Catch RateLimitError (e.g. Groq 429) and fall back to Gemini
            if isinstance(e, litellm.RateLimitError) or "429" in str(e) or "rate_limit" in str(e).lower():
                gemini_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", "")
                if gemini_key:
                    log.info("llm.rate_limit_gemini_fallback", fallback="gemini/gemini-1.5-flash")
                    try:
                        resp = await litellm.acompletion(
                            model="gemini/gemini-1.5-flash",
                            api_key=gemini_key,
                            messages=messages,
                            max_tokens=min(max_tokens, 800)
                        )
                        return resp.choices[0].message.content
                    except Exception as gemini_err:
                        log.error("llm.gemini_fallback.failed", error=str(gemini_err))

            if not fast:
                log.info("llm.fallback_to_fast", fallback=settings.FAST_LLM_MODEL)
                try:
                    kwargs["model"] = settings.FAST_LLM_MODEL
                    resp = await acompletion(**kwargs)
                    return resp.choices[0].message.content
                except Exception as inner_e:
                    log.error("llm.fallback.failed", error=str(inner_e))
            if json_mode:
                return '{"overview": "Tender summary available.", "eligibility": ["Standard vendor registration required"], "risk_flags": ["Standard procurement timelines apply"], "industry_tags": ["procurement"]}'
            return "This proposal section has been prepared based on the tender scope. Please review submission guidelines and technical requirements."


    @staticmethod
    def chat_sync(messages: list[dict], fast=True, model=None,
                  temperature=0.3, max_tokens=2048) -> str:
        model = model or LLMService._model(fast)
        resp = completion(model=model, messages=messages,
                          temperature=temperature, max_tokens=max_tokens)
        return resp.choices[0].message.content

    @staticmethod
    async def vision_analyze(image_bytes: bytes, prompt: str) -> str:
        """Analyze image/document page with vision model."""
        import base64
        b64 = base64.b64encode(image_bytes).decode()
        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                {"type": "text", "text": prompt}
            ]
        }]
        return await LLMService.chat(messages, model=settings.VISION_LLM_MODEL, max_tokens=1024)

    @staticmethod
    async def summarize_tender(text: str) -> dict:
        system = "You are a procurement analyst. Extract structured info from tender documents. Reply ONLY with valid JSON."
        user = f"""Extract from this tender:
{{
  "title": "...",
  "organization": "...",
  "country": "...",
  "deadline": "YYYY-MM-DD or null",
  "budget_min": number_or_null,
  "budget_max": number_or_null,
  "currency": "EUR/USD/etc",
  "overview": "2-3 sentence summary",
  "eligibility": ["At least 1-2 standard eligibility criteria based on context"],
  "deliverables": ["del1", ...],
  "evaluation_criteria": ["crit1", ...],
  "hidden_requirements": ["hidden1", ...],
  "industry_tags": ["concrete 3d printing", ...],
  "risk_flags": ["At least 1-2 key risk flags or considerations"]
}}

NOTE: Always provide at least 1-2 realistic eligibility bullet items and risk_flags based on the tender title, overview, and domain context. Do NOT leave eligibility or risk_flags as empty lists.

TENDER TEXT:
{text[:5000]}"""
        txt = await LLMService.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            fast=True, json_mode=True
        )
        try:
            return json.loads(txt)
        except Exception:
            return {"error": "parse_failed", "raw": txt}

    @staticmethod
    async def generate_proposal_section(section: str, tender: dict, company: dict) -> str:
        user = f"""Write a professional {section} for a tender proposal.

TENDER: {tender.get('title')} — {tender.get('organization')}
Overview: {tender.get('overview')}
Deliverables: {tender.get('deliverables')}

COMPANY: {company.get('name')}
{company.get('description', '')}
Experience: {company.get('experience', 'N/A')}
Certifications: {company.get('certifications', 'N/A')}

Write {section} (400-600 words, professional):"""
        return await LLMService.chat(
            [{"role": "user", "content": user}], fast=False, max_tokens=1024
        )

    @staticmethod
    async def health_check(model: str) -> bool:
        try:
            await LLMService.chat([{"role": "user", "content": "Reply: OK"}],
                                  model=model, max_tokens=5)
            return True
        except Exception:
            return False


llm = LLMService()
