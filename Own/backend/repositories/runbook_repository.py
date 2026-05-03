from supabase import create_client
from core.config import Config
from core.constants import RUNBOOK_SIMILARITY_THRESHOLD

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)


# ─────────────────────────────────────────────
# VECTOR SEARCH WITH SIMILARITY THRESHOLD
# ─────────────────────────────────────────────
async def search_runbooks_by_vector(
    embedding: list[float],
    top_k: int = 5   # 🔥 increased for reranking support
) -> list[dict]:
    """
    Cosine similarity search against runbook embeddings via Supabase RPC.

    Flow:
    1. Fetch top_k candidates from DB
    2. Apply threshold filter in Python (not DB)
    3. Return filtered results for optional AI rerank
    """

    try:
        if not embedding:
            return []

        # Convert 45% → 0.45
        min_similarity = RUNBOOK_SIMILARITY_THRESHOLD / 100

        res = supabase.rpc(
            "match_runbooks",
            {
                "query_embedding": embedding,
                "match_count": top_k,
                "min_similarity": min_similarity
            }
        ).execute()

        results = res.data or []

        if not results:
            print(f"⚠️ No runbooks returned from DB")
            return []

        # ─────────────────────────────────────────────
        # POST FILTERING + DEBUG LOGGING
        # ─────────────────────────────────────────────
        filtered_results = []

        print("\n🔍 Runbook Similarity Scores:")

        for r in results:
            similarity = r.get("similarity", 0)
            sim_percent = round(similarity * 100, 2)

            print(f"   → {sim_percent}% | {r.get('title')}")

            # ✅ APPLY THRESHOLD HERE (FINAL GATE)
            if sim_percent >= RUNBOOK_SIMILARITY_THRESHOLD:
                filtered_results.append(r)

        if not filtered_results:
            print(f"❌ No runbook passed threshold ({RUNBOOK_SIMILARITY_THRESHOLD}%)")
            return []

        print(f"\n✅ {len(filtered_results)} runbook(s) passed threshold")

        return filtered_results

    except Exception as e:
        print(f"❌ search_runbooks_by_vector error: {e}")
        return []