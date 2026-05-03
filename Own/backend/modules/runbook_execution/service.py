from services.embedding_service import get_embedding
from repositories.runbook_repository import search_runbooks_by_vector
from services.llm_service import call_llm
from core.constants import RUNBOOK_SIMILARITY_THRESHOLD
from modules.runbook_execution.prompt import RUNBOOK_RERANK_PROMPT


# ─────────────────────────────────────────────────────────────
# RUNBOOK SEARCH (VECTOR + THRESHOLD + RERANK)
# ─────────────────────────────────────────────────────────────
async def fetch_best_runbook(summary: str, description: str) -> dict | None:
    try:
        query = f"{summary} {description}".strip()
        if not query:
            return None

        query_embedding = await get_embedding(query)
        if not query_embedding:
            return None

        query_embedding = [float(x) for x in query_embedding]

        # 🔥 Fetch multiple runbooks
        results = await search_runbooks_by_vector(query_embedding, top_k=5)

        if not results:
            print("⚠️ No runbooks returned from DB")
            return None

        # ─────────────────────────────────────────
        # FILTER BY THRESHOLD
        # ─────────────────────────────────────────
        filtered = []

        for r in results:
            similarity_score = r.get("similarity", 0) * 100
            print(f"[RunbookService] {r.get('title')} → {similarity_score:.2f}%")

            if similarity_score >= RUNBOOK_SIMILARITY_THRESHOLD:
                filtered.append(r)

        if not filtered:
            print("❌ No runbooks passed threshold")
            return None

        # ─────────────────────────────────────────
        # SINGLE MATCH → RETURN DIRECTLY
        # ─────────────────────────────────────────
        if len(filtered) == 1:
            print("✅ Single runbook selected")
            return filtered[0]

        # ─────────────────────────────────────────
        # MULTIPLE MATCH → USE LLM (GROQ)
        # ─────────────────────────────────────────
        print("🤖 Multiple runbooks found → reranking using AI")

        runbook_text = ""
        for i, r in enumerate(filtered, start=1):
            runbook_text += f"""
{i}.
Title: {r.get('title')}
Category: {r.get('category')}
Symptoms: {r.get('symptoms')}
"""

        # ✅ Use prompt from prompt.py
        prompt = RUNBOOK_RERANK_PROMPT.format(
            summary=summary,
            description=description,
            runbooks=runbook_text
        )

        res = await call_llm(prompt)

        try:
            idx = int(res.strip())
        except:
            idx = 0

        if idx <= 0 or idx > len(filtered):
            print("⚠️ Invalid LLM response → fallback to best similarity")
            return filtered[0]

        print(f"✅ LLM selected runbook #{idx}")

        return filtered[idx - 1]

    except Exception as e:
        print(f"❌ fetch_best_runbook error: {e}")
        return None


# ─────────────────────────────────────────────
# OUTPUT PARSER
# ─────────────────────────────────────────────
def parse_llm_output(raw: str) -> tuple[list[str], list[str]]:
    steps = []
    commands = []

    for line in raw.splitlines():
        line = line.strip()

        if line.upper().startswith("STEP:"):
            text = line[5:].strip()
            if text:
                steps.append(text)

        elif line.upper().startswith("CMD:"):
            text = line[4:].strip()
            if text and text.upper() != "N/A":
                commands.append(text)

    if not steps and raw.strip():
        steps = [raw.strip()]

    return steps, commands


# ─────────────────────────────────────────────
# SAFETY FILTER
# ─────────────────────────────────────────────
_DANGEROUS_PATTERNS = [
    "rm -rf", "drop table", "drop database", "delete from",
    "kill -9", "truncate", "chmod 777", ":(){:|:&};:", "mkfs", "dd if=",
]


def filter_safe_commands(commands: list[str]) -> list[str]:
    safe = []

    for cmd in commands:
        lower = cmd.lower()

        if any(pattern in lower for pattern in _DANGEROUS_PATTERNS):
            print(f"⚠️ Unsafe command blocked: {cmd}")
        else:
            safe.append(cmd)

    return safe