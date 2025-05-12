from supabaseClient import supabase

def replace_user_data(phone_number: str, new_data: dict):
    """
    Replace the `userdata` JSONB blob for the user_data row
    matching the given phone_number. Returns the updated row dict
    on success or raises on failure.
    """
    try:
        resp = (
            supabase
            .table("user_data")
            .update({"userdata": new_data})
            .eq("phone_number", phone_number)
            .execute()
        )
    except Exception as e:
        raise RuntimeError(f"Supabase update failed for phone_number={phone_number}: {e}")

    updated_rows = getattr(resp, "data", None)
    if not updated_rows or not isinstance(updated_rows, list):
        raise RuntimeError(f"No user_data row found with phone_number={phone_number}")

    return updated_rows[0]


def updateStatus(call_sid: str, new_status: str):
    """
    Update the `status` column on the onboarding_sessions row
    matching the given call_sid. Returns the updated row dict
    on success or raises on failure.
    """
    try:
        resp = (
            supabase
            .table("onboarding_sessions")
            .update({"status": new_status})
            .eq("call_sid", call_sid)
            .execute()
        )
    except Exception as e:
        # network/auth/table-not-found errors, etc.
        raise RuntimeError(f"Supabase update failed for call_sid={call_sid}: {e}")

    # resp.data should be a list of updated rows
    updated_rows = getattr(resp, "data", None)
    if not updated_rows or not isinstance(updated_rows, list):
        raise RuntimeError(f"No session found with call_sid={call_sid}")

    # return the first (and only) updated row
    return updated_rows[0]

def format_conversation(messages):
    """
    Formats a list of message dicts into a conversation-style string.

    Args:
        messages (list of dict): Each dict should have 'role' and 'message' keys.

    Returns:
        str: Conversation formatted with each line as "Role: message".
    """
    lines = []
    for msg in messages:
        role = msg.get('role', '').capitalize()
        text = msg.get('message', '')
        lines.append(f"{role}: {text}")
    return "\n".join(lines)
