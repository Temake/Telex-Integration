from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import re
import os
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

app = FastAPI()
scheduler = BackgroundScheduler()
scheduler.start()

# Trello Credentials
TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_TOKEN = os.getenv("TRELLO_TOKEN")
LIST_ID = os.getenv("LIST_ID")

# Ensure credentials are loaded
if not all([TRELLO_API_KEY, TRELLO_TOKEN, LIST_ID]):
    raise ValueError("Missing Trello API credentials. Check your .env file.")

# Function to create a Trello card (task)
def create_trello_card(task_name: str):
    url = "https://api.trello.com/1/cards"
    query = {
        "key": TRELLO_API_KEY,
        "token": TRELLO_TOKEN,
        "idList": LIST_ID,
        "name": task_name,
        "desc": f"Scheduled task: {task_name}",
    }
    
    response = requests.post(url, params=query)
    if response.status_code == 200:
        print(f"Trello card '{task_name}' created successfully.")
    else:
        print(f"Failed to create Trello card: {response.json()}")

# Function to execute scheduled tasks
def execute_task(task_name: str, task_url: str):
    response = requests.post(task_url)
    print(f"Executed {task_name}: {response.status_code}")

# Function to extract task details from the message
def extract_task_details(message: str):
    pattern = r"(?:Schedule|Task): (\w+).*?(?:at|every) (\d{1,2} (?:AM|PM)|\w+)"
    match = re.search(pattern, message, re.IGNORECASE)

    if match:
        task_name = match.group(1)
        interval = match.group(2).lower()

        # Map common time keywords to scheduler-compatible intervals
        interval_mapping = {
            "hourly": "hours",
            "daily": "days",
            "weekly": "weeks"
        }
        interval_type = interval_mapping.get(interval, "days")  # Default to daily if unknown

        return {"task_name": task_name, "interval": interval_type}

    return None

# API Endpoint to process incoming messages
@app.post("/process-message/")
async def process_message(background_tasks: BackgroundTasks, message: str, task_url: str = None):
    task_details = extract_task_details(message)

    if not task_details:
        raise HTTPException(status_code=400, detail="No valid task found in the message.")

    task_name = task_details["task_name"]
    interval = task_details["interval"]

    # Schedule Trello Task
    create_trello_card(task_name)

    # Schedule Execution Task if task_url is provided
    if task_url:
        scheduler.add_job(execute_task, trigger="interval", args=[task_name, task_url], **{interval: 1})

    modified_message = f"Task '{task_name}' scheduled successfully every {interval}."
    
    return {"modified_message": modified_message, "task_name": task_name, "interval": interval}

# API Endpoint to serve integration JSON
@app.get("/integration.json")
def get_integration_json(request: Request):
    base_url = str(request.base_url).rstrip("/")
    return {
        "data": {
            "descriptions": {
                "app_name": "Telex Task Auto-Scheduler",
                "app_description": "Extracts task details from messages and schedules them automatically.",
                "app_url": "https://telex-integration-1g06.onrender.com",
                "app_logo": "https://i.imgur.com/lZqvffp.png",
                "background_color": "#fff"
            },
            "integration_type": "Modifier",
            "integration_category": "Task Automation",
            "settings": [
                {
                    "key": "default_task_interval",
                    "type": "string",
                    "label": "Default Task Interval",
                    "default": "daily",
                    "description": "Default execution interval if not specified in the message."
                }
            ],
            "target_url": "https://telex-integration-1g06.onrender.com/process-message/"
        }
    }
