from fastapi import FastAPI, Path, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from makeCall import makeTaskCall, makeOnboardingCall
from supabaseClient import supabase
from transcriptionAnalysis import generateGraphObjects, getInitialUserObject
from graphs import add_graph
from helper import format_conversation, updateStatus, replace_user_data

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",    # Vite default
        "http://localhost:3000",    # if you ever run on 3000
        "https://vapi.ai",
        "https://api.vapi.ai",
        "https://life-track-two.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],          # allow GET, POST, OPTIONS, etc.
    allow_headers=["*"],
)


# ---------- Schemas ----------

class WebhookRequest(BaseModel):
    user_id: str
    
class OnboardRequest(BaseModel):
    phone_number: str


# ---------- Routes ----------

@app.post("/webhook")
async def webhook(request: Request):
    """
    Simulated webhook endpoint.
    Receives a user ID and returns placeholder user info.
    Replace this with real user lookup logic in the future.
    """
    payload = await request.json()
    messageType = payload['message']['type']
    print(messageType)
    sid = payload['message']['call']['transport']['callSid']
    phone_number = payload['message']['call']['customer']['number']
    if messageType == "end-of-call-report":
        print("\n\n\n CALL ENDED \n\n\n")
        print(sid)
        if payload['message']['analysis']['successEvaluation'] == 'true':
            updateStatus(sid, 'completed')
            formatted_convo = format_conversation(payload['message']['artifact']['messages'][1:])
            print("Formatted Conversation:", formatted_convo)
            graphs = await generateGraphObjects(formatted_convo)
            for graph in graphs:
                print('\nAdding Graph:', graph)
                add_graph(graph, phone_number)
            
            userObj = await getInitialUserObject(formatted_convo)
            print("User Object:", userObj)
            replace_user_data(phone_number, userObj)
        else:
            updateStatus(sid, 'failed')
        
        
    elif messageType == "status-update":
        print("\n\n\n STATUS UPDATE \n\n\n")
        print(sid)
        if payload['message']['status'] == 'in-progress':
            updateStatus(sid, 'answered')
            print("Call in progress!")
            # Update Supabase with the new status
            
        
    return {
        "user_id": '123',
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "role": "user",
        "created_at": "2025-01-01T12:00:00Z"
    }




@app.post("/onboarding")
async def onboarding(req: OnboardRequest):
    """
    Sends a call to the user to set up their dashboard.
    Gets info like who they are, what their goals are,
    what time they want to be called etc.
    """
    print("Onboarding request received! Making call...")
    sid = makeOnboardingCall(req.phone_number)
    if not sid:
        print("Calling failed? No SID")
        raise HTTPException(status_code=500, detail="Failed to initiate onboarding call")
    print("Call sent successfully!", sid)
    # build the payload to insert
    session_row = {
        "phone_number": req.phone_number,
        "status": "pending",                # we just kicked off the call
        "call_sid": sid,
        "user_id": None                     # null until they sign up
    }

    print("Sending info to supabase", session_row)
    # 1) catch any transport/auth errors
    try:
        resp = supabase.table("onboarding_sessions") \
                        .insert([session_row]) \
                        .execute()
    except Exception as e:
        # e.g. network failure, auth failure, bad URL, etc.
        raise HTTPException(500, f"Supabase request failed: {e}")
    print(resp)
    # make sure we got back the inserted row
    if not resp.data or not isinstance(resp.data, list):
        raise HTTPException(500, "No data returned from Supabase after insert")
    print(resp.data[0])
    # new_session = resp.data[0]  # this is your row, including its `id`, timestamps, etc.
    
    # —————————————————————————
    # 2) write the initial user_data row
    # —————————————————————————
    
    user_data_row = {
        "phone_number": req.phone_number,
        "userdata": {},     # start with an empty JSON blob
        "user_id": None     # now allowed to be null
    }
    print("User data adding:", user_data_row)
    try:
        ud_resp = (
            supabase
            .table("user_data")
            .upsert([user_data_row])
            .execute()
        )
    except Exception as e:
        # you might choose to delete new_session here if you want full rollback
        raise HTTPException(500, f"Supabase insert (user_data) failed: {e}")

    if not ud_resp.data or not isinstance(ud_resp.data, list):
        raise HTTPException(500, "No data returned after inserting user_data")
    
    return {"sid": sid}




# ---------- Run Server ----------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
