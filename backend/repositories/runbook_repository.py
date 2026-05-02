from supabase import create_client
from core.config import Config

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)


# ─────────────────────────────────────────────
# VECTOR SEARCH  ✅ NEW (replaces text search)
# ─────────────────────────────────────────────
async def search_runbooks_by_vector(embedding: list[float], top_k: int = 1) -> list[dict]:
    """
    Cosine similarity search against runbook embeddings via Supabase RPC.
    Requires match_runbooks() SQL function to be created in Supabase.
    """
    try:
        res = supabase.rpc(
            "match_runbooks",
            {
                "query_embedding": embedding,
                "match_count":     top_k,
            }
        ).execute()

        if res.data:
            return res.data

        print("⚠️  search_runbooks_by_vector: no matches found")
        return []

    except Exception as e:
        print(f"❌ search_runbooks_by_vector error: {e}")
        return []


# # ─────────────────────────────────────────────
# # FULL-TEXT SEARCH  (kept as fallback)
# # ─────────────────────────────────────────────
# async def search_runbooks_by_text(query_text: str, top_k: int = 3) -> list[dict]:
#     try:
#         if not query_text or not query_text.strip():
#             return []

#         sanitised = query_text.strip()

#         res = (
#             supabase.table("runbooks")
#             .select(
#                 "id, title, category, severity, symptoms, "
#                 "resolution_steps, escalation_team, owner, "
#                 "estimated_resolution_time, ci_asset, status"
#             )
#             .text_search("keywords", sanitised, config="english", type="plain")
#             .eq("status", "Active")
#             .limit(top_k)
#             .execute()
#         )

#         return res.data if res.data else []

#     except Exception as e:
#         print(f"❌ search_runbooks_by_text error: {e}")
#         return []


# # ─────────────────────────────────────────────
# # GET ALL RUNBOOKS
# # ─────────────────────────────────────────────
# async def get_all_runbooks() -> list[dict]:
#     try:
#         res = (
#             supabase.table("runbooks")
#             .select("*")
#             .eq("status", "Active")
#             .order("created_at", desc=True)
#             .execute()
#         )
#         return res.data if res.data else []

#     except Exception as e:
#         print(f"❌ get_all_runbooks error: {e}")
#         return []


# # ─────────────────────────────────────────────
# # GET SINGLE RUNBOOK BY ID
# # ─────────────────────────────────────────────
# async def get_runbook_by_id(runbook_id: int) -> dict | None:
#     try:
#         res = (
#             supabase.table("runbooks")
#             .select("*")
#             .eq("id", runbook_id)
#             .single()
#             .execute()
#         )
#         return res.data if res.data else None

#     except Exception as e:
#         print(f"❌ get_runbook_by_id error: {e}")
#         return None