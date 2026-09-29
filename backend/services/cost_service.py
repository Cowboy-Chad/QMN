import httpx
import tiktoken

# Reuse the one resolver from openrouter_service rather than parsing the same file
# a second time — two readers of one secret is two chances to disagree about it.
# (No import cycle: openrouter_service does not import cost_service.)
from backend.services.openrouter_service import OPENROUTER_API_KEY

# Imported from fabric_service so the model used for a cost estimate is by
# construction the same constant that was passed to `fabric -p`. Defining it here
# as well meant the two could drift and price a different model than the one that
# actually ran.
from backend.services.fabric_service import DEFAULT_MODEL as FABRIC_MODEL

_pricing_cache: dict[str, dict] = {}
_pricing_cache_timestamp: float = 0


async def fetch_live_pricing() -> dict:
    global _pricing_cache, _pricing_cache_timestamp
    import time

    now = time.time()
    if _pricing_cache and now - _pricing_cache_timestamp < 300:
        return _pricing_cache

    if not OPENROUTER_API_KEY:
        return {}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        )
        if resp.status_code != 200:
            return {}
        data = resp.json()
        for model in data.get("data", []):
            model_id = model["id"]
            pricing = model.get("pricing", {})
            _pricing_cache[model_id] = {
                "prompt": float(pricing.get("prompt", 0)),
                "completion": float(pricing.get("completion", 0)),
            }
        _pricing_cache_timestamp = now
    return _pricing_cache


def _get_model_for_tokenizer(model: str) -> str:
    model_lower = model.lower()
    if "gpt-4" in model_lower or "gpt-3" in model_lower or "gpt-audio" in model_lower:
        return "cl100k_base"
    if "deepseek" in model_lower:
        return "cl100k_base"
    return "cl100k_base"


def count_tokens(text: str, model: str = FABRIC_MODEL) -> int:
    encoding_name = _get_model_for_tokenizer(model or FABRIC_MODEL)
    try:
        enc = tiktoken.get_encoding(encoding_name)
        return len(enc.encode(text))
    except Exception:
        return len(text) // 4


async def estimate_cost(input_text: str, output_text: str, model: str = FABRIC_MODEL) -> dict:
    effective_model = model or FABRIC_MODEL
    pricing = await fetch_live_pricing()

    input_tokens = count_tokens(input_text, effective_model)
    output_tokens = count_tokens(output_text, effective_model)

    model_pricing = pricing.get(effective_model, {})
    prompt_price = model_pricing.get("prompt", 0)
    completion_price = model_pricing.get("completion", 0)

    cost = (input_tokens * prompt_price) + (output_tokens * completion_price)

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "prompt_price_per_token": prompt_price,
        "completion_price_per_token": completion_price,
        "estimated_cost": round(cost, 6),
        "pricing_source": "OpenRouter API (live)" if model_pricing else "OpenRouter API (default)",
    }