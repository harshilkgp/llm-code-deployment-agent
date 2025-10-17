# models.py
from pydantic import BaseModel

# These Pydantic models validate the structure of the incoming JSON
class Attachment(BaseModel):
    name: str
    url: str

class TaskRequest(BaseModel):
    email: str
    secret: str
    task: str
    round: int
    nonce: str
    brief: str
    checks: list
    evaluation_url: str
    attachments: list[Attachment]