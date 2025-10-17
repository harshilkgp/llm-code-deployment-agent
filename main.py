# main.py
import os
import dotenv
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
import tasks 
from models import TaskRequest

dotenv.load_dotenv()
MY_SECRET = os.getenv("MY_SECRET")

app = FastAPI()

@app.post("/api-endpoint")
async def receive_task(request: TaskRequest, background_tasks: BackgroundTasks):
    if request.secret != MY_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret provided.")

    if request.round == 1:
        background_tasks.add_task(tasks.handle_build_task, request)
    elif request.round == 2:
        background_tasks.add_task(tasks.handle_revise_task, request)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid round: {request.round}")

    print(f"✅ Task '{request.task}' for round {request.round} received. Processing in background.")
    return {"status": "Task received and is being processed."}

@app.get("/")
def read_root():
    return {"status": "Server is running. Send POST requests to /api-endpoint"}
