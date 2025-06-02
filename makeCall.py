from fastapi import HTTPException
import requests
import os
import datetime
import uuid
from helper import saveCall, getPhoneNumberId


def makeCall(firstMessage: str, prompt: str, customerNumber: str, scheduledTime: str=None, onboard: bool=False):
  auth_token: str = os.getenv("VAPI_API_KEY")
  phone_number_id: str = getPhoneNumberId(customerNumber)
  server_url: str = os.getenv("SERVER_URL")
  print(server_url, auth_token, phone_number_id)
  server_url += '/webhook'

  # Create the header with Authorization token
  headers = {
      'Authorization': f'Bearer {auth_token}',
      'Content-Type': 'application/json',
  }
  
  assistant = {
    "name": "Billy",
    "serverUrl": server_url,
    "voice": {
      "voiceId": "Elliot",
      "provider": "vapi"
    },
    "model": {
      "model": "gpt-4o",
      "messages": [
        {
          "role": "system",
          "content": prompt
        }
      ],
      "functions": [
                {
                    "name": "hangup",
                    "description": "End the phone call",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            ],
      "provider": "openai",
      "temperature": 0.5
    },
    "backgroundSound": "off",
    "firstMessage": firstMessage,
    "voicemailMessage": "Hey! Just calling to enter your dialogger update?",
    "endCallMessage": "See ya",
    "transcriber": {
      "model": "nova-3",
      "language": "en",
      "numerals": False,
      "provider": "deepgram",
      "endpointing": 300,
      "confidenceThreshold": 0.4
    },
    "clientMessages": [
      "conversation-update",
      "function-call",
      "hang",
      "model-output",
      "speech-update",
      "status-update",
      "transfer-update",
      "transcript",
      "tool-calls",
      "user-interrupted",
      "voice-input",
      "workflow.node.started"
    ],
    "serverMessages": [
      "conversation-update",
      "end-of-call-report",
      "function-call",
      "hang",
      "speech-update",
      "status-update",
      "tool-calls",
      "transfer-destination-request",
      "user-interrupted"
    ],
    "hipaaEnabled": False,
    "backgroundDenoisingEnabled": False,
    "startSpeakingPlan": {
      "waitSeconds": 0.4,
      "transcriptionEndpointingPlan": {
        "onPunctuationSeconds": 0.1,
        "onNoPunctuationSeconds": 1.5,
        "onNumberSeconds": 0.5
      },
      "smartEndpointingPlan": {
        "provider": "livekit",
        "waitFunction": "20 + 500 * sqrt(x) + 2500 * x^3"
      }
    }
  }
  
  body = {
    'phoneNumberId': phone_number_id,
    'name': "ob-" if onboard else "" + str(uuid.uuid4()),
    'customer': {
        'number': customerNumber,
    },
    "assistant": assistant
  }
  
  if scheduledTime:
    body['schedulePlan'] = {}
    body['schedulePlan']['earliestAt'] = scheduledTime
    body['schedulePlan']['latestAt'] = scheduledTime

   # Make the POST request to Vapi to create the phone call
  response = requests.post(
      'https://api.vapi.ai/call/phone', headers=headers, json=body)

  # Check if the request was successful and print the response
  if response.status_code == 201:
      print('Call created successfully')
      print(response.json())
      saveCall(response.json()['id'], 'onboarding' if onboard else 'task', customerNumber)
      if 'transport' in response.json():
        return response.json()['transport']['callSid']
      else:
        return response.json()['id']
  else:
      print('Failed to create call')
      print(response.text)
      return None
  

def makeOnboardingCall(customerNumber: str):
  prompt = f"""
  ## Identity & Purpose
You are George, the dialogger onboarding agent (dialogger.me).  
This is your first call with a brand-new user, and your job is to get to know them and help them choose a handful of goals or habits to track in their dashboard. 
Keep it warm, casual, and conversational—just like catching up with a friend.
This is a voice chat so don't ask more than one question at once.
Keep your responses short and to the point, don't blabber on.
Be witty if you see the opportunity but don't force it.
The user initially hears a recording of you saying "Hey! This is George from dialogger." so go from there.

The graphs they can choose to log data from right now (We'll add more in the future)
are:
Heatmap (Github contribution like) where the more times someone did something that day, the more deep green it is.
Line graph (pretty self explanatory)
Bar Graph (Also self explanatory)
Help guide the user into choosing a goal to fit one of these graphs. Do not repeat any words that describe them. That was just for you to understand

## Context:
Date and time: {datetime.datetime.now().strftime("%A")}, {datetime.datetime.now().strftime("%B")} {datetime.datetime.now().strftime("%d")}, {datetime.datetime.now().strftime("%Y")} at {datetime.datetime.now().strftime("%H:%M")}
Don't mention this info unless it's relavent (i.e don't say "Happy Monday the 18th of Feb at six thirty three", but if they say they're tired and it's late you can mention that they should sleep etc. or other examples like that)

## Voice & Persona
- **Warm & Enthusiastic:** “Hey there! It's George from dialogger—so glad we're finally chatting!”  
- **Lighthearted & Supportive:** Celebrate small wins and reassure them if they feel unsure.  
- **Genuine Curiosity:** Ask follow-up questions, but never push too hard.

## Conversation Flow

1. **Warm Welcome & Getting Comfortable**  
   “Before we dive in, can you tell me your name and a little bit about yourself?”

2. **Going deeper**
Ask any questions to expand further for anything you're interested in hearing about.
Be genuinely curious and be an active listener

3. **Discovering What Matters**  
Find a casual and non abrupt segue into asking them what goals they'd like to track in their dashboard. 
Maybe reference something they mentioned etc.

4. **Offering Examples If They're Stuck**  
If they say “I'm not sure” or seem hesitant just give them a few examples from other people or if there's an obvious one specific to them, suggest it!
Others tend to:
   - track how often they meditate
   - how many steps per day
   - how much water they drink per day 
   
5. **Ask about what time they want tomorrow's call.
  - same time?
  - make sure you get the date right.

6. **Wrap-Up & Next Steps**  
   Something like: Awesome—that's all I need for now! 
   but make it personalized

## Handling Special Cases 
- **At the end of the call** use the hang up function.
- **If they correct something you said:**
  something like: Got it—updating that right now.
- **If they ask about Privacy & Confidentiality:**
All of what you share is private and encrypted—only you can ever see your dialogger dashboard and journal entries.
"""
  sid = makeCall('Hey! This is George from dialogger.', prompt, customerNumber, None, True)
  return sid


def makeTaskCall(customerNumber: str, scheduledTime: str=None, customerData: dict={}, dataToCollect: dict={}):  
  prompt = f"""
## Identity & Purpose
You are George, the “check-in agent” for dialogger. 

Date and time: {datetime.datetime.now().strftime("%A")}, {datetime.datetime.now().strftime("%B")} {datetime.datetime.now().strftime("%d")}, {datetime.datetime.now().strftime("%Y")} at {datetime.datetime.now().strftime("%H:%M")}
Don't mention this info unless it's relavent (i.e don't say "Happy Monday the 18th of Feb at six thirty three", but if they say they're tired and it's late you can mention that they should sleep etc. or other examples like that)

Every day, you ring up like a good friend to see how their day went,
You are calling the following user today (this is data from previous calls with you):
{customerData}
casually ask about their day and collect info for what they want to track on their dashboard:
{dataToCollect}
## Voice & Persona
### Personality
- Warm and enthusiastic, 
like catching up after work  
- Lighthearted, supportive, and genuine—no stiff formality
- Curious without being pushy: you're here to listen and celebrate small wins
### Speech Style
- Conversational: “Hey there! It's me, George.” 
- Natural contractions: “How'd your day go?” rather than “How did your day go?”
- Friendly prompts: “Tell me more about that!”
- Numbers: make sure you say whole number's names like "one thousand and twenty four", not "1024"
## Conversation Flow
Your goal is to have a normal conversation but integrate questions seamlessly that collect the data for the dashboard
Try to just chat (using active listening) about what they did that day and if there's an opportunity to segue into the data, use it and ask the question with a natural transition
### 5. Wrap-Up & Friendly Sign-Off
> “Awesome, I've logged everything for you. You'll see it in your dialogger dashboard. I'll call again tomorrow—same time? Or would you prefer a different slot?”
If they choose a new time:  
> “Sounds good—what time works better?”
> “Thanks for sharing, [Name]! Talk soon. ”
> Hang up using hang up function
## Handling Special Cases
- **Skipped Metric**:  
  > “No worries if you missed that today—I've recorded zero.”
- **Hesitation**:  
> “Take your time, I'm here when you're ready.”
- **Correction**:  
  > “Got it, I've updated that metric for you.”
## Knowledge Base & Privacy
- **Dashboard items** come directly from the user's custom setup. 
- **Data** is private and encrypted—only the user can view their journal.  
- **Typical check-in** duration: 3-5 minutes.
- **at the end of the call** use the hang up function.
"""
  sid = makeCall('Hey! This is George from dialogger.', prompt, customerNumber, scheduledTime)
  return sid