import openai
import os
import json
import aiohttp
import datetime
from dotenv import load_dotenv
from makeCall import makeTaskCall
from helper import convert_iso_to_gmt_plus10, convert_local_to_iso, getCurrentUserData, getCurrentGraphData, updateGraphData, getLastEntries
# Global cost counter:
total_cost = 0

load_dotenv()
openai.api_key = os.getenv("MY_OPENAI_KEY")


async def askLLM(prompt: str, isJson: bool = False) -> str:
    if isJson:
        prompt = prompt + "\nYour output should not include anything except the json valid object/list. You should not start or end with ``` or json or anything other than { or }"
    
    print("Asking AI:", prompt)
    # input("Click enter to confirm")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4.1-2025-04-14",
                "messages": [{"role": "system", "content": prompt}],
                "temperature": 0.2
            }
        ) as response:
            result = await response.json()
            
    try:
        extractedResponse = result['choices'][0]['message']['content'].strip()
        print(f"Successfully processed AI response: {extractedResponse}")
        usage = result['usage']
        
        prompt_tokens = usage['prompt_tokens']
        completion_tokens = usage['completion_tokens']
        
        priceOfCall = prompt_tokens * (2 / 1000000) + completion_tokens * (8 / 1000000)
        global total_cost
        total_cost += priceOfCall
        print("Cost of call: $" + str(priceOfCall))
        print("running total of cost: $" + str(total_cost))
        
        if not isJson:
            return extractedResponse
        else:
            try:
                # If the response has ```json at the start take that off the start and ``` off the end
                if (extractedResponse.startswith("```json") or extractedResponse.startswith("``` json")) and extractedResponse.endswith("```"):
                    extractedResponse = extractedResponse[7:-3]
                return json.loads(extractedResponse)
            except:
                print("Failed to parse into json", result)
                return {"result": extractedResponse}
    except:
        print(f"Failed to parse AI response:", result)
        return None

async def generateGraphObjects(transcription: str) -> list:
    prompt = f"""
{transcription}
-----------------------
Date and time: {datetime.datetime.now().strftime("%A")}, {datetime.datetime.now().strftime("%B")} {datetime.datetime.now().strftime("%d")}, {datetime.datetime.now().strftime("%Y")} at {datetime.datetime.now().strftime("%H:%M")}
Based on the above transcription of a phone call,
create a list of objects that represent graphs to achieve what the user wanted.
Choose graph types that work best for the user's request.
Each object should be structured in the following format:
{{
    "title": "The title of the graph from the user's perspective (e.g My daily steps)",
    "description": "A description (less than 100 characters) of the data recorded from the user's perspective"
    "type": "The type of graph that best represents the data. Choose from the following: ['contribution', 'line', 'bar']. Contribution is a heatmap style graph that shows how frequently someone does something. Line is a line chart. Bar is a bar chart."
    "settings":    {{
        // if it's a contribution graph → {{ "totalCells": number }}
        // if it's a line graph         → {{  }}  // no settings
        // if it's a bar graph          → {{ "timeFrame": 'week' | 'month' | 'year' }}
    }}
}}
"""
    
    graphs = await askLLM(prompt, isJson=True)
    
    return graphs

async def getInitialUserObject(transcription: str) -> dict:

    prompt = f"""
{transcription}
-----------------------
Based on the above transcription of a phone call,
Create an object that represents the user.
You can give it any keys you want but start with UserInfo.
This is an example. Do not use any information from this, 
only base it off the transcription
{{
    "UserInfo": {{
      "Name": "Will",
      "Age": "21",
      "Birthday": "31st of May"
      }},
    "FriendsAndFamily": {{
      "Abbey": {{
        "Description": "Abbey is Will's girlfriend. They've been dating for 2.5 years now and are very happy together. They want to buy a cottage in the mountains in the future. Abbey is studying Graphic Design at Melbourne University and she uses these skills in her business with Will called Lucent Studio which is a web development agency"
      }},
      "Chirag": {{
        "Description": "Chirag is Will's friend from High School. They often work on SaaS businesses together and their girlfriends are best friends"
      }},
      "Charlotte": {{
        "Description": "Chirag's girlfriend and one of Abbey's closest friends. She's studying film at Swinburne"
      }},
    }},
  }}
See how that starts with any info learned about Will and then adds a friends and family given that he must have described his friends and family in the relevant transcription?
Again. That is just an example to show you the structure. No matter how similar the actualy user is, do not use any of that data.
This should only be an object that represents them as a person. Don't add things like the goals they want to set every day, that will be handled by another function.
You should be logging longer term things like their friends, family, projects, how they want to be talked to, their job, etc.
Calendar items will be logged by another function too. Though things like "plays basketball every Tuesday" is still important to note that they play basketball.
You can have as many keys and use lists etc. as you need to describe the user.
"""
    
    userObject = await askLLM(prompt, isJson=True)
    
    return userObject

async def UpdateGraphs(transcription: str, phone_number: str) -> list:
    
    currentGraphData = getCurrentGraphData(phone_number)
    
    lastEntryGraphData = getLastEntries(currentGraphData)
    
    prompt = f"""
{transcription}
-----------------------
Current Date and time: {datetime.datetime.now().strftime("%A")}, {datetime.datetime.now().strftime("%B")} {datetime.datetime.now().strftime("%d")}, {datetime.datetime.now().strftime("%Y")} at {datetime.datetime.now().strftime("%H:%M")}
Based on the above transcription of a phone call,
create a object that represents the next entry into each of the graphs in the following format:
{{"graphId": [{{"date": "the date this data is for in dd/mm/yyyy format", "value": n}}]}}
where n is the value that the transcription suggests. don't add units, that will be done later
Here is the current graph data:
{lastEntryGraphData}
Your output should be in an object.
"""
    newGraphEntries = await askLLM(prompt, isJson=True)
    
    # Add the new entries to the graph and then send the data to supabase with the updateGraphData helper function
    
    graphs = []
    for graph in currentGraphData:
        if graph['id'] in newGraphEntries:
            graph['data'].extend(newGraphEntries[graph['id']])
            graphs.append(graph)
            updateGraphData(graph['data'], graph['id'])
        else:
            print("uh oh... forgot graph", graph['title'])
            # Could potentially loop back and ask to fix but I don't want to waste credits for now
    
    return graphs

async def updateUserData(transcription: str, phone_number: str) -> dict:
    currentData = getCurrentUserData(phone_number)
    
    prompt = f"""
{transcription}
-----------------------
Based on the above transcription of a phone call,
Update the following representation of the user:
{currentData}
You can give it any new keys you want and update information if they mention it's outdated
only base it off the transcription
This should only be an object that represents them as a person. Don't add things like the goals they want to set every day, that will be handled by another function.
You should be logging longer term things like their friends, family, projects, how they want to be talked to, their job, etc.
Calendar items will be logged by another function too. Though things like "plays basketball every Tuesday" is still important to note that they play basketball.
You can have as many keys and use lists etc. as you need to describe the user.
"""

    newUserObject = await askLLM(prompt, isJson=True)
    
    return newUserObject

async def setNextCall(customerNumber: str, customerData: dict, transcription: str, createdAt: str, dataToCollect: dict={}):
    # Format time from 2025-05-12T05:17:19.039Z into May 12, 2025 at 3:17:19 PM
    formattedTime = convert_iso_to_gmt_plus10(createdAt)
    
    print(formattedTime)
    prompt = f"""
    {transcription}
    -----------------------
    Based on the above transcription of a phone call,
    return a json that represents the time that the user wants to have the call next
    The time of the call was {formattedTime}.
    If they never mentioned a new time or the time they set was invalid (yesterday etc.): 
    just set it to tommorrow, same time.
    Assume tomorrow unless they specifically say.
    Do not explain or question anything. Just return the string in the exact same format as the following:
    {formattedTime}
    Don't put quotations around it to show it's a string or anything. Just the text. Nothing else.
    It will be parsed directly so leave it as is.
    If the call went to voicemail or the user doesn't want a call, return null
    """
    
    nextCall = await askLLM(prompt)
    
    iso_time = convert_local_to_iso(nextCall)
    
    makeTaskCall(customerNumber, iso_time, customerData, dataToCollect)
    
    return iso_time