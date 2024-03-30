from datetime import date, datetime, time, timedelta
from typing import List, Optional
from typing import List
from pydantic import BaseModel, EmailStr, constr
from bson.objectid import ObjectId


class Customer(BaseModel):
    name: str
    email: str
    phone: str
    business_ids: str
    created_at: datetime


class EditCustomer(BaseModel):
    name: str or None = None
    email: str
    phone: str or None = None


class LoginCustomerSchema(BaseModel):
    email: EmailStr
    password: constr(min_length=8)
    business_id: str
