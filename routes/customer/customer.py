import hashlib
from random import randbytes

import bson
from fastapi import HTTPException, status, APIRouter, Request, Cookie, Depends, Response

from config.config import settings
from routes.business.business_register import business_collection
from routes.customer.customer_models import *
from database.database import database
from database.database import database
from routes.authentication import val_token
from routes.customer.customer_utils import generate_temp_password, hash_password, verify_password
from routes.emails import Email
from routes.user_registration import user_utils
from serializers.userSerializers import customerEntity

customer_router = APIRouter()
customers_collection = database.get_collection('customers')
user_collection = database.get_collection('users')


async def customer_register(details):
    business_details = business_collection.find_one({"_id": ObjectId(str(details['business_ids']))})
    if business_details:
        find_user = user_collection.find_one({'_id': business_details['User_ids'][0]})
        temp_password = generate_temp_password()
        hashed_temp_password = hash_password(temp_password)
        details['password'] = hashed_temp_password
        details['User_ids'] = [find_user['_id']]
        result = customers_collection.insert_one(details)
        await Email(temp_password, details['email'], 'customer_register').send_email()
        if result.inserted_id:
            return {"status": f"New Customer- {details['name']} added",
                    'message': 'Temporary password successfully sent to your email'}
        else:
            raise HTTPException(status_code=500, detail="Failed to insert data")
    else:
        raise HTTPException(status_code=404, detail=f'Unable to find business - {details["business_ids"]}')


@customer_router.post("/customer/register")
async def create_customer(customer: Customer):
    details = customer.dict()
    customer_collection = database.get_collection('customers')
    print(customer_collection)
    customer = customers_collection.find_one({'email': details["email"]})
    try:
        if customer:
            check_business = customers_collection.find({
                '_id': ObjectId(str(customer['_id'])),
                "business_ids": ObjectId(str(details['business_ids']))
            })
            if check_business:
                raise HTTPException(status_code=409, detail=f"Customer Email- {customer['email']} Exists")
            else:
                return await customer_register(details)
        if not customer:
            return await customer_register(details)
    except bson.errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid business ID")


@customer_router.post("/edit/customer")
async def update_customer(edit_customer: EditCustomer, token: str = Depends(val_token)):
    from pymongo import ReturnDocument
    if token[0] is True:
        edit_customer = edit_customer.dict(exclude_none=True)
        customer_collection = database.get_collection('customers')
        customer = customers_collection.find_one({'email': edit_customer["email"]})
        if customer:
            edit_customer['updated_at'] = datetime.utcnow()
            result = customer_collection.find_one_and_update({'_id': customer['_id']}, {'$set': edit_customer},
                                                             return_document=ReturnDocument.AFTER)

            if not result:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f'Unable to Update for this Customer - {result}')
        else:
            raise HTTPException(status_code=409, detail=f"Customer {customer['phone']} does not Exists")

    else:
        raise HTTPException(status_code=401, detail=token)

    return {'status': f'Updated Customer Successfully- {customer["name"]}'}


@customer_router.post('/customer/login')
async def login(payload: LoginCustomerSchema, response: Response):
    # Check if the user exist
    db_user = customers_collection.find_one({'email': payload.email.lower()})
    if not db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Incorrect Email or Password')
    user = customerEntity(db_user)
    ACCESS_TOKEN_EXPIRES_IN = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    REFRESH_TOKEN_EXPIRES_IN = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    # Check if user verified his email

    if not verify_password(payload.password, user['password']):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Incorrect Email or Password')

    # Create access token
    access_token = user_utils.create_refresh_token(user['email'], user['name'], 'Customer')

    # Create refresh token
    refresh_token = user_utils.create_access_token(user['email'], user['name'], 'Customer')

    # Store refresh and access tokens in cookie
    response.set_cookie('access_token', access_token, ACCESS_TOKEN_EXPIRES_IN * 60,
                        ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, True, 'lax')
    response.set_cookie('refresh_token', refresh_token,
                        REFRESH_TOKEN_EXPIRES_IN * 60, REFRESH_TOKEN_EXPIRES_IN * 60, '/', None, False, True, 'lax')
    response.set_cookie('logged_in', 'True', ACCESS_TOKEN_EXPIRES_IN * 60,
                        ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, False, 'lax')

    # Send both access
    return {'status': 'success', 'access_token': access_token}
