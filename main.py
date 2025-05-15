from fastapi import FastAPI, Path, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from makeCall import makeTaskCall, makeOnboardingCall
from supabaseClient import supabase
from transcriptionAnalysis import generateGraphObjects, getInitialUserObject, setNextCall, updateUserData, UpdateGraphs
from graphs import add_graph
from helper import format_conversation, updateStatus, replace_user_data, deleteCall, getCallType, getCustomerData, getCurrentGraphData, getLastEntries

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
    
class TaskRequest(BaseModel):
    userId: str


# ---------- Routes ----------

@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.json()
    messageType = payload['message']['type']
    print(messageType)
    sid = payload['message']['call']['transport']['callSid']
    phone_number = payload['message']['call']['customer']['number']
    if messageType == "end-of-call-report":
        print("\n\n\n CALL ENDED \n\n\n")
        print(payload)
        callType = getCallType(payload['message']['call']['id'])
        formatted_convo = format_conversation(payload['message']['artifact']['messages'][1:])
        if callType == 'onboarding':
            await handleOnboardingEnd(sid, phone_number, payload, formatted_convo)
        else: #if callType == 'task':
            await handleTaskEnd(phone_number, payload, formatted_convo)
        # else:
        #     print("SHIT! Don't know the call type soz...", formatted_convo)
        print(sid)
        
        
        
    elif messageType == "status-update":
        print("\n\n\n STATUS UPDATE \n\n\n")
        print(sid)
        print(payload['message']['status'])
        status = payload['message']['status']
        if status == 'in-progress':
            updateStatus(sid, 'answered')
            print("Call in progress!")
            # Update Supabase with the new status
        elif status == 'ended':
            updateStatus(sid, 'completed')
            print('Call ended!')
            
        
    return {
        "user_id": '123',
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "role": "user",
        "created_at": "2025-01-01T12:00:00Z"
    }


async def handleOnboardingEnd(sid: str, phone_number: str, payload: dict, formatted_convo: str):

    updateStatus(sid, 'completed')
    
    print("Formatted Conversation:", formatted_convo)
    graphs = await generateGraphObjects(formatted_convo)
    for graph in graphs:
        print('\nAdding Graph:', graph)
        add_graph(graph, phone_number)
    
    userObj = await getInitialUserObject(formatted_convo)
    await setNextCall(phone_number, userObj, formatted_convo, payload['message']['call']['createdAt'], graphs)
    
    print("User Object:", userObj)
    replace_user_data(phone_number, userObj)
    
    deleteCall(payload['message']['call']['id'])

async def handleTaskEnd(phone_number: str, payload: str, formatted_convo: str):
    
    # Steps to handle Task End:
    # 
    #  1. Update graphs with new data
    graphs = await UpdateGraphs(formatted_convo, phone_number)
    
    #  2. Update user object with new data
    customerData = await updateUserData(formatted_convo, phone_number)
    
    #  3. Schedule the next call
    await setNextCall(phone_number, customerData, formatted_convo, payload['message']['call']['createdAt'], graphs)
    
    #  4. Delete the call type
    deleteCall(payload['message']['call']['id'])

    return 'no lol'

@app.post("/onboarding")
async def onboarding(req: OnboardRequest):
    """
    Sends a call to the user to set up their dashboard.
    Gets info like who they are, what their goals are,
    what time they want to be called etc.
    """
    print("AHHHHHH")
    
    try:
        resp = supabase.table("user_data") \
                        .select("*") \
                        .eq("phone_number", req.phone_number) \
                        .execute()
    except Exception as e:
        # e.g. network failure, auth failure, bad URL, etc.
        raise HTTPException(500, f"Supabase request failed: {e}")
    
    if len(resp.data):
        print("User already onboarded!", resp.data)
        return {"sid": "OnboardedAlready"}
    
    print("User not onboarded yet! Making call...")
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
        print("AHHH FAILED 1", e)
        # you might choose to delete new_session here if you want full rollback
        raise HTTPException(500, f"Supabase insert (user_data) failed: {e}")

    if not ud_resp.data or not isinstance(ud_resp.data, list):
        print("AHHH FAILED 2")
        raise HTTPException(500, "No data returned after inserting user_data")
    
    return {"sid": sid}

@app.post("/task")
async def webhook(req: TaskRequest):
    phone_number, data = getCustomerData(req.userId)
    id, graphData = getCurrentGraphData(phone_number)
    lastEntries = getLastEntries(graphData)
    makeTaskCall(phone_number, None, data, lastEntries)
    


# ---------- Run Server ----------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
