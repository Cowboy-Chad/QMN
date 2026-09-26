import asyncio
import os
import subprocess

DEFAULT_MODEL = os.environ.get("FABRIC_MODEL", "deepseek/deepseek-v4-flash")
DEFAULT_VENDOR = os.environ.get("FABRIC_VENDOR", "OpenRouter")
FABRIC_TIMEOUT = int(os.environ.get("FABRIC_TIMEOUT", "600"))
MAX_RETRIES = int(os.environ.get("FABRIC_MAX_RETRIES", "3"))
RETRY_BASE_DELAY = float(os.environ.get("FABRIC_RETRY_BASE_DELAY", "2.0"))

# Curated list of patterns available for selection
CURATED_PATTERNS = sorted([
    "analyze_claims",
    "analyze_debate",
    "analyze_incident",
    "analyze_mistakes",
    "analyze_personality",
    "analyze_presentation",
    "analyze_risk",
    "analyze_spiritual_text",
    "analyze_tech_impact",
    "analyze_threat_report",
    "analyze_threat_report_trends",
    "ask_uncle_duke",
    "audit_transparency",
    "capture_thinkers_work",
    "check_falsifiability",
    "compare_and_contrast",
    "create_5_sentence_summary",
    "create_academic_paper",
    "create_bd_issue",
    "create_conceptmap",
    "create_cyber_summary",
    "create_flash_cards",
    "create_golden_rules",
    "create_idea_compass",
    "create_investigation_visualization",
    "create_micro_summary",
    "create_newsletter_entry",
    "create_prd",
    "create_quiz",
    "create_reading_plan",
    "create_recursive_outline",
    "create_story_about_person",
    "create_summary",
    "create_visualization",
    "detect_mind_virus",
    "dialog_with_socrates",
    "explain_terms",
    "extract_alpha",
    "extract_all_quotes",
    "extract_bd_ideas",
    "extract_business_ideas",
    "extract_core_message",
    "extract_extraordinary_claims",
    "extract_ideas",
    "extract_insights",
    "extract_main_idea",
    "extract_predictions",
    "extract_primary_problem",
    "extract_primary_solution",
    "extract_questions",
    "extract_references",
    "extract_wisdom",
    "extract_wisdom_with_attribution",
    "find_hidden_message",
    "heal_person",
    "provide_guidance",
    "summarize",
    "summarize_debate",
    "youtube_summary",
])


async def run_fabric(pattern: str, input_text: str, model: str | None = None, vendor: str | None = None) -> str:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        cmd = ["fabric", "-p", pattern]
        cmd.extend(["-m", model or DEFAULT_MODEL])
        if vendor or DEFAULT_VENDOR:
            cmd.extend(["-V", vendor or DEFAULT_VENDOR])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(input=input_text.encode()), timeout=FABRIC_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(f"fabric analysis timed out after {FABRIC_TIMEOUT}s for pattern '{pattern}'")
        if proc.returncode == 0:
            return stdout.decode().strip()

        stderr_str = stderr.decode()
        if proc.returncode == 1 and "429" in stderr_str and attempt < MAX_RETRIES:
            last_error = stderr_str
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            await asyncio.sleep(delay)
            continue

        raise RuntimeError(f"fabric exited code {proc.returncode}: {stderr_str}")

    raise RuntimeError(f"fabric exited code 1 after {MAX_RETRIES} retries: {last_error}")


async def list_patterns() -> list[dict]:
    return [{"name": n, "description": ""} for n in CURATED_PATTERNS]


async def read_pattern(pattern: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "fabric",
        "--readpattern", pattern,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"fabric --readpattern failed: {stderr.decode()}")
    return stdout.decode()