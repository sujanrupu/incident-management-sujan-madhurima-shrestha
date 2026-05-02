from modules.runbook_execution.agent import RunbookAgent


async def handle_runbook_flow(state: dict) -> dict:
    try:
        
        print(f"DEBUG state keys: {list(state.keys())}")
        print(f"DEBUG summary: {repr(state.get('summary'))}")
        print(f"DEBUG data: {repr(state.get('data'))}")
        summary     = state.get("summary", "")
        description = ""

        raw_data = state.get("data")
        if raw_data:
            if hasattr(raw_data, "description"):
                description = raw_data.description or ""
            elif isinstance(raw_data, dict):
                description = raw_data.get("description", "")

        if not summary:
            return {
                **state,
                "type": "error",
                "message": "Runbook module: ticket summary is empty",
            }

        agent  = RunbookAgent()

        # ✅ pass full state so agent can check is_duplicate + parent_ticket_key
        result = await agent.run(
            summary=summary,
            description=description,
            state=state          
        )

        return {
            **state,
            "runbook_title":    result.get("runbook_title"),
            "runbook_category": result.get("runbook_category"),
            "runbook_severity": result.get("runbook_severity"),
            "checklist_steps":  result.get("checklist_steps", []),
            "commands":         result.get("commands", []),
            "match_type":       result.get("match_type", "ai_fallback"),
            "type":             state.get("type") or "runbook_executed",
            "message":          result.get("message", "Runbook execution complete"),
        }

    except Exception as e:
        print(f"❌ handle_runbook_flow error: {e}")
        return {
            **state,
            "type":    "error",
            "message": f"Runbook module failed: {str(e)}",
        }