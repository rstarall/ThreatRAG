from pydantic import BaseModel

class ConversationSchema(BaseModel):
    input: str
    output: str