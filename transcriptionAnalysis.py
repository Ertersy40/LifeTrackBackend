import openai
import os
import json
import aiohttp
from dotenv import load_dotenv

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
Based on the above transcription of a phone call,
create a list of objects that represent graphs to achieve what the user wanted.
Choose graph types that work best for the user's request.
Each object should be structured in the following format:
{{
    "title": "The title of the graph from the user's perspective (e.g My daily steps)",
    "description": "A description (less than 100 characters) of the data recorded from the user's perspective"
    "type": "The type of graph that best represents the data. Choose from the following: ['contribution', 'line', 'bar']. Contribution is a heatmap style graph that shows how frequently someone does something. Line is a line chart. Bar is a bar chart."
    "settings":    {{
        // contribution → {{ "totalCells": number }}
        // line         → {{  }}  // no settings
        // bar          → {{ "timeFrame": 'week' | 'month' | 'year' }}
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
You can have as many keys and use lists etc. as you need to describe the user.
"""
    userObject = await askLLM(prompt, isJson=True)
    return userObject