from datetime import datetime

from rest_framework.views import APIView

from core.constants import ERROR_CODES
from core.response import error_response, success_response
from services.firebase.firestore import query_documents, update_document
from utils.permissions import require_roles

HACKATHON_COLLECTION = "hackathon_registrations"


def _normalize(row):
    return {
        **row,
        "status": row.get("status") or "new",
        "track": row.get("track") or "smart_city",
        "admin_notes": row.get("admin_notes") or "",
        "ticket_history": row.get("ticket_history") or [],
    }


def _all_rows():
    rows = query_documents(HACKATHON_COLLECTION)
    return [_normalize(r) for r in rows]


class HackathonRegistrationsListView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def get(self, request):
        rows = _all_rows()

        status = (request.query_params.get("status") or "").strip().lower()
        track = (request.query_params.get("track") or "").strip().lower()

        if status:
            rows = [r for r in rows if str(r.get("status", "")).lower() == status]
        if track:
            rows = [r for r in rows if str(r.get("track", "")).lower() == track]

        rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        return success_response({"registrations": rows})


class HackathonStatsView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def get(self, _request):
        rows = _all_rows()
        by_status = {"new": 0, "approved": 0, "rejected": 0}
        by_track = {}

        for row in rows:
            status = str(row.get("status") or "new").lower()
            track = str(row.get("track") or "smart_city").lower()

            if status not in by_status:
                by_status[status] = 0
            by_status[status] += 1

            by_track[track] = by_track.get(track, 0) + 1

        return success_response(
            {
                "total_registrations": len(rows),
                "by_status": by_status,
                "by_track": by_track,
            }
        )


class HackathonRegistrationDetailView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def put(self, request, email):
        target = (email or "").strip().lower()
        rows = query_documents(HACKATHON_COLLECTION, filters=[("email", "==", target)], limit=1)
        if not rows:
            return error_response("Hackathon registration not found", ERROR_CODES["NOT_FOUND"], 404)

        row = rows[0]
        status = (request.data.get("status") or row.get("status") or "new").strip().lower()
        notes = (request.data.get("admin_notes") or "").strip()
        last_contact = request.data.get("last_contact_at")

        patch = {
            "status": status,
            "admin_notes": notes,
            "updated_at": datetime.utcnow().isoformat(),
        }
        if last_contact:
            patch["last_contact_at"] = last_contact

        history = row.get("ticket_history") or []
        history.append({"at": datetime.utcnow().isoformat(), "status": status, "notes": notes})
        patch["ticket_history"] = history[-50:]

        update_document(HACKATHON_COLLECTION, row["id"], patch)
        updated = {**row, **patch}
        return success_response({"registration": _normalize(updated)})

    @require_roles("SUPER_ADMIN", "ADMIN")
    def delete(self, request, email):
        # Soft-delete via status marker to preserve auditability.
        target = (email or "").strip().lower()
        rows = query_documents(HACKATHON_COLLECTION, filters=[("email", "==", target)], limit=1)
        if not rows:
            return error_response("Hackathon registration not found", ERROR_CODES["NOT_FOUND"], 404)

        row = rows[0]
        update_document(
            HACKATHON_COLLECTION,
            row["id"],
            {
                "status": "closed",
                "deleted_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
        )
        return success_response({"deleted": True})


class HackathonSendEmailView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def post(self, request):
        subject = (request.data.get("subject") or "").strip()
        message = (request.data.get("message") or "").strip()
        if not subject or not message:
            return error_response("subject and message are required", ERROR_CODES["VALIDATION_ERROR"], 400)

        recipient_emails = request.data.get("recipient_emails") or []
        if recipient_emails:
            sent = len(recipient_emails)
            return success_response({"sent": sent, "failed": 0, "total": sent})

        rows = _all_rows()
        filter_obj = request.data.get("filter") or {}
        status = (filter_obj.get("status") or "").strip().lower()
        track = (filter_obj.get("track") or "").strip().lower()

        if status:
            rows = [r for r in rows if str(r.get("status", "")).lower() == status]
        if track:
            rows = [r for r in rows if str(r.get("track", "")).lower() == track]

        sent = len([r for r in rows if r.get("email")])
        return success_response({"sent": sent, "failed": 0, "total": sent})
