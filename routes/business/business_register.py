from fastapi import HTTPException, status, APIRouter, Request, Cookie, Depends
from pymongo import ReturnDocument
import json
from routes.business.business_models import *
from database.database import database
from routes.authentication import val_token

business_router = APIRouter()
business_collection = database.get_collection('business')
user_collection = database.get_collection('users')


@business_router.post("/business/register")
async def create_business(business: Business, token: str = Depends(val_token)):
    if token[0] is True:
        details = business.dict()
        search_criteria ={"email": token[1]['email'], "business": {
            "$elemMatch": {
                "business_name": details['name']
            }
        }}

        # Find documents matching the search criteria
        cursor = user_collection.find(search_criteria)
        print(cursor)
        # Iterate over the results
        document_list = []
        for document in cursor:
            print("Matching document:", document)
            document_list.append(document)
        if document_list:
            raise HTTPException(status_code=409, detail=f"Business {details['name']} Exists")
        else:
            find_user = user_collection.find_one({'email':token[1]['email']})
            result = business_collection.insert_one(details)
            if result.inserted_id:
                update_user = user_collection.update_one({'email': token[1]['email']}, {
                    '$push': {'business': {'business_id': result.inserted_id, 'business_name': details['name']}}},
                                                    upsert=True)

                if update_user:

                    update_business_users = business_collection.update_one({'_id': ObjectId(result.inserted_id)}, {
                        '$push': {'User_ids': find_user['_id']}
                        },upsert=True)
                    if update_business_users:
                        return {"Business": f"Created Business {details['name']}"}
                else:
                    raise HTTPException(status_code=400, detail="Failed to update data")
            else:
                raise HTTPException(status_code=500, detail="Failed to insert data")
        # else:
        #     raise HTTPException(status_code=409, detail=f"Business {business['name']} Exists")
    #
    else:
        raise HTTPException(status_code=401, detail=token)


@business_router.post("/edit/business")
async def update_business(edit_business: EditBusiness, token: str = Depends(val_token)):
    from pymongo import ReturnDocument
    if token[0] is True:
        edit_business = edit_business.dict(exclude_none=True)
        get_user = user_collection.find_one({'email': token[1]['email']})
        print(get_user)
        if get_user:
            edit_business['updated_at'] = datetime.utcnow()
            print(edit_business)
            matching_business = [b for b in get_user["business"] if b["business_name"] == edit_business['name']]
            if matching_business:
                print("Matching business details:", matching_business)
                update_user = business_collection.find_one_and_update({'_id': matching_business[0]['business_id']}, {
                    '$set': edit_business}, upsert=True)
                print("Matching business details:", update_user)
            else:
                raise HTTPException(status_code=404, detail=f'Unable to find business - {edit_business["name"]}')
        else:
            raise HTTPException(status_code=409, detail=f"business {edit_business['name']} does not Exists")

    else:
        raise HTTPException(status_code=401, detail=token)

    return {'status': f'Updated Business Successfully- {edit_business["name"]}'}
