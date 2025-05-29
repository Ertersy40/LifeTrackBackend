from fastapi import HTTPException
from supabaseClient import supabase
from datetime import datetime, timezone, timedelta
import copy


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
        raise RuntimeError(f"No session found with call_sid: {call_sid}")

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



def convert_iso_to_gmt_plus10(iso_ts: str) -> str:
    """
    Convert an ISO8601 UTC timestamp (ending in 'Z') to:
      'Weekday, Month D, YYYY H:MM:SS AM/PM (This is GMT +10)'
    by simply adding 10 hours—no OS-specific strftime hacks.
    """
    print("Raw iso:", iso_ts)
    # 1) Parse the UTC timestamp
    dt_utc = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    
    # 2) Apply fixed +10h offset
    dt_local = dt_utc + timedelta(hours=10)
    
    # 3) Break out each component
    weekday = dt_local.strftime("%A")     # e.g. "Monday"
    month   = dt_local.strftime("%B")     # e.g. "May"
    day     = dt_local.day                # e.g. 12
    year    = dt_local.year               # e.g. 2025
    
    hour24  = dt_local.hour               # 0–23
    hour12  = hour24 % 12 or 12           # convert to 12h, with 12 instead of 0
    minute  = dt_local.minute             # 0–59
    second  = dt_local.second             # 0–59
    ampm    = "AM" if hour24 < 12 else "PM"
    
    # 4) Zero-pad minutes/seconds, then assemble
    time_str = f"{hour12}:{minute:02d}:{second:02d} {ampm}"
    
    print(f"Converted time: {weekday}, {month} {day}, {year} {time_str}")
    return f"{weekday}, {month} {day}, {year} {time_str}"


def convert_local_to_iso(local_str: str) -> str:
    """
    Parse a string like "Monday, May 12, 2025 3:17:19 PM" (GMT+10),
    and convert it back to an ISO8601 UTC timestamp ending in 'Z'.
    """
    # 1) Parse the local time (naïve datetime) including weekday
    #    %A = full weekday name, %B = full month name, %d = zero-padded day,
    #    %Y = 4-digit year, %I = 12-hour clock, %M = minute, %S = second, %p = AM/PM
    dt_local_naive = datetime.strptime(local_str, "%A, %B %d, %Y %I:%M:%S %p")
    
    # 2) Attach the fixed GMT+10 offset
    tz_offset = timezone(timedelta(hours=10))
    dt_local = dt_local_naive.replace(tzinfo=tz_offset)
    
    # 3) Convert to UTC
    dt_utc = dt_local.astimezone(timezone.utc)
    
    # 4) Format as ISO8601 with 'Z'
    #    (millisecond precision is dropped; add if you need it)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def saveCall(callId: str, callType: str, customerNumber: str):
    
    session_row = {
        "id": callId,
        "call_type": callType,
    }

    print("Sending call type info to supabase", session_row)
    # 1) catch any transport/auth errors
    try:
        resp = supabase.table("calls") \
                        .insert([session_row]) \
                        .execute()
    except Exception as e:
        print("SupabaseRequestFailed:", e)
        # e.g. network failure, auth failure, bad URL, etc.
        raise HTTPException(500, f"Supabase request failed: {e}")

    updated_rows = getattr(resp, "data", None)
    
def deleteCall(callId: str):
  
  resp = supabase.table("calls") \
                        .delete() \
                        .eq("id", callId) \
                        .execute()
  print(resp)
  
def getCallType(callId: str):
    resp = supabase.table("calls") \
                        .select("call_type") \
                        .eq("id", callId) \
                        .execute()
    return resp.data[0]['call_type']


def getCurrentUserData(phone_number: str):
    resp = supabase.table('user_data') \
                        .select("userdata") \
                        .eq("phone_number", phone_number) \
                        .execute()
    return resp.data[0]['userdata']

def getCustomerData(user_id: str):
    resp = supabase.table('user_data') \
                        .select("phone_number, userdata") \
                        .eq("user_id", user_id) \
                        .execute()
    phone_number =  resp.data[0]['phone_number']
    userData = resp.data[0]['userdata']
    return phone_number, userData
    

def getCurrentGraphData(phone_number: str):
    userIdDataResp = supabase.table('user_data') \
                        .select("id") \
                        .eq("phone_number", phone_number) \
                        .execute()
    userId = userIdDataResp.data[0]['id']
    
    graphsResp = supabase.table('graphs') \
                        .select("*") \
                        .eq("user_data_id", userId) \
                        .execute()

    graphsInfo = graphsResp.data
    graphData = []
    for graph in graphsInfo:
        graphDataResp = supabase.table('graph_data') \
                        .select("data") \
                        .eq("graph_id", graph['id']) \
                        .execute()
        tempGraph = graph
        del tempGraph['user_data_id']
        tempGraph['data'] = graphDataResp.data[0]['data']
        graphData.append(tempGraph)
    
    return graphData

def updateGraphData(graphData: list, graphId: str):
    print("Updating graph data!", graphData)

    resp = supabase.table('graph_data') \
                    .update({'data': graphData}) \
                    .eq('graph_id', graphId) \
                    .execute()
    
    print("Updated graph data maybe!!")
    

def getLastEntries(graphData):
    lastEntryGraphData = []
    
    for graph in graphData:
        
        if len(graph['data']) > 0:
            graph['lastEntry'] = graph['data'][-1]
            tempGraph = copy.deepcopy(graph)
            del tempGraph['data']
            lastEntryGraphData.append(tempGraph)

    return lastEntryGraphData

import os
from dotenv import load_dotenv
load_dotenv()


def getPhoneNumberId(phoneNumber):
    if phoneNumber.startswith("+1"):
        return os.getenv("VAPI_US_PHONE_ID")
    elif phoneNumber.startswith("+61"):
        return os.getenv("VAPI_AU_PHONE_ID")
    elif phoneNumber.startswith("+64"):
        return os.getenv("VAPI_NZ_PHONE_ID")
    elif phoneNumber.startswith("+44"):
        return os.getenv("VAPI_UK_PHONE_ID")
    else:
        print("Phone number not in provided country code options")