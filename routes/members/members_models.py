from datetime import date, datetime, time, timedelta
from typing import List, Optional
from typing import List
from pydantic import BaseModel, EmailStr, constr
from bson.objectid import ObjectId


class Members(BaseModel):
    name: str
    email: str
    role: str
    business_ids: list[str]
    created_time: datetime
