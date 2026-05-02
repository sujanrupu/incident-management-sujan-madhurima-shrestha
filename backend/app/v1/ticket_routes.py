# app/v1/ticket_routes.py

from fastapi import APIRouter, HTTPException

# schemas + orchestrator
from schemas.ticket_schema import TicketRequest
from orchestrator.ams_orchestrator import handle_ticket

# repository layer
from repositories.ticket_repository import (
    get_all_tickets,
    delete_ticket_cascade,
    update_status_cascade,
    update_ticket_runbook,
)

# Jira integration
from services.jira_service import (
    delete_jira_ticket,
    update_jira_status,
)

# Runbook module
from modules.runbook_execution.handler import handle_runbook_flow

router = APIRouter()


# ───────────── SUBMIT TICKET ─────────────
@router.post("/submit")
async def submit(data: TicketRequest):
    """Full ticket creation pipeline via orchestrator."""
    result = await handle_ticket(data)

    if not isinstance(result, dict):
        return {"type": "error", "message": "Invalid orchestrator response"}

    return result


# ───────────── GET ALL TICKETS ─────────────
@router.get("/tickets")
async def get_tickets():
    """Fetch all tickets from DB."""
    tickets = await get_all_tickets()

    if not isinstance(tickets, list):
        return []

    return tickets


# ───────────── DELETE TICKET (CASCADE) ─────────────
@router.delete("/tickets/{issueKey}")
async def delete(issueKey: str):
    try:
        jira_deleted = await delete_jira_ticket(issueKey)

        if not jira_deleted:
            return {"type": "error", "message": f"Failed to delete {issueKey} from Jira"}

        db_deleted = await delete_ticket_cascade(issueKey)

        if not db_deleted:
            return {"type": "error", "message": "Database delete failed"}

        return {"type": "success", "message": "Parent and all child tickets deleted successfully"}

    except Exception as e:
        print(f"❌ delete error: {e}")
        return {"type": "error", "message": str(e)}


# ───────────── COMPLETE TICKET ─────────────
@router.put("/tickets/{issueKey}/complete")
async def complete_ticket(issueKey: str):
    try:
        tickets = await get_all_tickets()

        if not tickets:
            return {"type": "error", "message": "No tickets found"}

        current = next((t for t in tickets if t["issue_key"] == issueKey), None)

        if not current:
            return {"type": "error", "message": "Ticket not found"}

        parent_key = current.get("parent_ticket_key") or current.get("issue_key")

        print(f"🔍 Completing parent ticket: {parent_key}")

        jira_ok = await update_jira_status(parent_key)

        if not jira_ok:
            print(f"⚠️  Jira update failed for parent: {parent_key}")

        db_ok = await update_status_cascade(parent_key, "Completed")

        if not db_ok:
            return {"type": "error", "message": "Database update failed"}

        print(f"✅ Completed status applied for {parent_key}")

        return {"type": "success", "message": "Marked as completed", "id": parent_key}

    except Exception as e:
        print(f"❌ complete_ticket error: {e}")
        return {"type": "error", "message": str(e)}


# ───────────── GET RUNBOOK FOR TICKET ─────────────
@router.get("/tickets/{issueKey}/runbook")
async def get_runbook(issueKey: str):
    try:
        # ── 1. Find ticket ──
        tickets = await get_all_tickets()
        ticket  = next((t for t in tickets if t["issue_key"] == issueKey), None)

        if not ticket:
            raise HTTPException(status_code=404, detail=f"Ticket {issueKey} not found")

        # ── 2. Duplicate redirect ──
        if ticket.get("is_duplicate") and ticket.get("parent_ticket_key"):
            parent_key = ticket["parent_ticket_key"]
            print(f"↩️  [{issueKey}] Duplicate ticket — redirecting to parent {parent_key}")
            return {
                "type":              "duplicate",
                "message":           f"This is a duplicate ticket. See runbook for parent: {parent_key}",
                "parent_ticket_key": parent_key,
            }

        # ── 3. Return cached runbook if available ──
        if ticket.get("checklist_steps") and ticket.get("commands"):
            print(f"📦 [{issueKey}] CACHE HIT — returning stored runbook (no LLM call)")
            return {
                "checklist":        ticket["checklist_steps"],
                "commands":         ticket["commands"],
                "runbook_title":    ticket.get("runbook_title"),
                "runbook_category": ticket.get("runbook_category"),
                "match_type":       ticket.get("match_type"),
                "message":          "Loaded from cache",
            }

        # ── 4. Build handler state ──
        print(f"🤖 [{issueKey}] CACHE MISS — calling LLM to generate runbook...")
        state = {
            "id":      issueKey,
            "summary": ticket.get("summary", ""),
            "data":    ticket,
            "type":    None,
            "message": "",
        }

        # ── 5. Run runbook agent ──
        result = await handle_runbook_flow(state)

        if result.get("type") == "error":
            raise HTTPException(status_code=500, detail=result.get("message"))

        # ── 6. Shape commands for frontend ──
        checklist_steps: list = result.get("checklist_steps", [])
        raw_commands:    list = result.get("commands", [])

        commands = [
            {"label": f"Command {i + 1}", "command": cmd}
            for i, cmd in enumerate(raw_commands)
        ]

        # ── 7. Save to Supabase (cache for future requests) ──
        await update_ticket_runbook(
            issue_key        = issueKey,
            checklist_steps  = checklist_steps,
            commands         = commands,
            runbook_title    = result.get("runbook_title"),
            runbook_category = result.get("runbook_category"),
            match_type       = result.get("match_type"),
        )
        print(f"💾 [{issueKey}] Runbook saved to Supabase — future requests will use cache")

        # ── 8. Return response ──
        return {
            "checklist":        checklist_steps,
            "commands":         commands,
            "runbook_title":    result.get("runbook_title"),
            "runbook_category": result.get("runbook_category"),
            "match_type":       result.get("match_type"),
            "message":          result.get("message"),
        }

    except HTTPException:
        raise

    except Exception as e:
        print(f"❌ get_runbook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))