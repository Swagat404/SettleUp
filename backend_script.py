
from fastapi import FastAPI, HTTPException, File, UploadFile,Form,Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import datetime
from fastapi.responses import JSONResponse
from gpt_4_parser import Bill_parser
from PIL import Image
import tempfile
from io import BytesIO
from voice import Voicee

app = FastAPI()

# Enable CORS - Modified configuration
origins = [
    "http://localhost:3001",
    "http://localhost:3000",  # Added common React development port
    "http://10.122.94.24:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicitly specify methods
    allow_headers=["*"],
    expose_headers=["*"],  # Add expose_headers
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Initialize Supabase
load_dotenv("/Users/swagatbhowmik/CS projects/CodeJam2024/bill_parser/.env")
supabase_url = "https://ltpasfjejihckukshlhs.supabase.co"
supabase_key = os.getenv("REACT_APP_SUPABASE_ANON_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Pydantic models for request validation
class User(BaseModel):
    user_id: str
    name: str
    created: str
    email: str

class AddFriend(BaseModel):
    user_id: str
    friend_id: str

class GroupCreate(BaseModel):
    group_name: str
    description: str
    created_by: str

class GroupMember(BaseModel):
    group_id: str
    user_id: str

class IndividualExpense(BaseModel):
    group_id: str
    user_id: str




from fastapi.routing import APIRoute
from typing import List
import traceback
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AddSplit(BaseModel):
    bill_id: str
    item_id: str
    payer_id: str
    user_ids: List[str]
    total_price: float

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/add_friend")
async def add_friend(friend:AddFriend):
    try:
        # Add bidirectional friendship
        supabase.table("Friends").insert([
            {"user_id": friend.user_id, "friend_id": friend.friend_id},
            {"user_id": friend.friend_id, "friend_id": friend.user_id},
        ]).execute()

        return {"status": "success", "message": "Friend added successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/friends")
async def get_friends(user_id: str):
    try:
        # Fetch all friends of the user
        friends_response = supabase.table("Friends") \
            .select("friend_id") \
            .eq("user_id", user_id) \
            .execute()
        friend_ids = [friend["friend_id"] for friend in friends_response.data]
        if not friend_ids:  # Check if group_ids is empty
            return {
                "status": "success",
                "data": "No Friends found",
                }
            

        # If group_ids is not empty, fetch group details
        friends_data = supabase.table("User_info").select("id, name").in_("id", friend_ids).execute()
        cleaned_data = [
            {
                "friend_id": friend["id"],
                "friend_name": friend["name"],
            }
            for friend in friends_data.data
        ]
        return {
            "status": "success",
            "data": cleaned_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


@app.get("/find-friend")
async def find_friend(email_id: str):
    try:

        user = supabase.table("User_info").select("*").eq("email", email_id).execute()

        
        if not user.data:  
            return {
                "status": "success",
                "data": "No User found",
                }

        return {
            "status": "success",
            "data": user.data,
        }


    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


@app.get("/user-details")
async def user_details(user_id: str):
    try:

        user = supabase.table("User_info").select("*").eq("id", user_id).execute()

        
        if not user.data:  
            return {
                "status": "success",
                "data": "No User found",
                }

        return {
            "status": "success",
            "data": user.data,
        }


    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }





@app.post("/users")
async def create_user(user: User):
    print(f"Received user data: {user.dict()}")  # Log the received data
    try:
        response = supabase.table("User_info").insert({
            "id": user.user_id,
            "name": user.name,
            "created_at": user.created,
            "email": user.email
        }).execute()
        
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))








@app.post("/groups/create")
async def create_group(group: GroupCreate):
    try:
        # First create the group
        group_data = {
            "group_name": group.group_name,
            "description": group.description,
            "created_by": group.created_by,
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        
        # Insert into Groups table
        group_response = supabase.table("Groups").insert(group_data).execute()
        
        if not group_response.data:
            raise HTTPException(status_code=400, detail="Failed to create group")
        
        new_group = group_response.data[0]
        group_id = new_group.get('group_id')
        
        # Add creator as first member
        member_data = {
            "group_id": group_id,
            "user_id": group.created_by,
            "joined_at": datetime.datetime.utcnow().isoformat()
        }
        
        # Insert into Group_Members table
        member_response = supabase.table("Group_Members").insert(member_data).execute()
        
        if not member_response.data:
            # Rollback group creation if member addition fails
            supabase.table("Groups").delete().eq("group_id", group_id).execute()
            raise HTTPException(status_code=400, detail="Failed to add creator to group")
        
        return {
            "status": "success",
            "message": "Group created successfully",
            "data": {
                "group": new_group,
                "member": member_response.data[0]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/groups")
async def get_group_list(user_id: str):
    try:
        # Step 1: Get the list of group IDs the user belongs to
        group_response = supabase.table("Group_Members").select("group_id").eq("user_id", user_id).execute()

        # Step 2: Extract group IDs from the response
        group_ids = [group["group_id"] for group in group_response.data]

        # Step 3: Query the Groups table for the desired columns, filtering by the group IDs
        if not group_ids:  # Check if group_ids is empty
            return {
                "status": "success",
                "data": "No groups found",
                }

        # If group_ids is not empty, fetch group details
        groups_data = supabase.table("Groups").select("group_id, group_name, created_at,created_by, User_info(name)").in_("group_id", group_ids).execute()
        cleaned_data = [
            {
                "group_id": group["group_id"],
                "group_name": group["group_name"],
                "created_by": group["User_info"]["name"],
                "created_at": group["created_at"]
            }
            for group in groups_data.data
        ]
        return {
            "status": "success",
            "data": cleaned_data,
        }


    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }





@app.get("/groups/{group_id}")
async def get_group(group_id: str):
    try:
        # Fetch group details
        group_response = supabase.table("Groups").select("*").eq("group_id", group_id).execute()
        
        if not group_response.data:
            raise HTTPException(status_code=404, detail="Group not found")
            
        # Fetch group members
        members_response = (
            supabase.table("Group_Members")
            .select("user_id, joined_at, User_info(name, email)")
            .eq("group_id", group_id)
            .execute()
        )
        
        return {
            "status": "success",
            "data": {
                "group": group_response.data[0],
                "members": members_response.data
            }
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/groups/{group_id}/members")
async def add_group_member(group_id: str, member: GroupMember):
    try:
        # Check if group exists
        group_exists = supabase.table("Groups").select("group_id").eq("group_id", group_id).execute()
        if not group_exists.data:
            return {
                "status": "error",
                "message": "Group not found"
            }

        # Check if user exists
        user_exists = supabase.table("User_info").select("id").eq("id", member.user_id).execute()
        if not user_exists.data:
            return {
                "status": "error",
                "message": "User not found"
            }

        # Check if user is already a member
        existing_member = (
            supabase.table("Group_Members")
            .select("*")
            .eq("group_id", group_id)
            .eq("user_id", member.user_id)
            .execute()
        )

        if existing_member.data:
            return {
                "status": "error",
                "message": "User is already a member of this group"
            }

        # Add new member
        member_data = {
            "group_id": group_id,
            "user_id": member.user_id,
            "joined_at": datetime.datetime.utcnow().isoformat()
        }

        response = supabase.table("Group_Members").insert(member_data).execute()

        return {
            "status": "success",
            "message": "Member added successfully",
            "data": response.data[0]
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }



 
@app.post("/scan-bill")
async def predict(group_id: str = Form(...), 
                 user_id: str = Form(...),
                 file: UploadFile = File(...)):
    try:
        image_data = await file.read()
        
        parser = Bill_parser()
        bill_json = parser.parse_byte(image_data)
        json_obj = parser.jsonify_parse(bill_json)
        total_price = sum(item['total_price'] for item in json_obj['items'])
        translated = parser.translate(json_obj)

        # Insert bill record
        response = supabase.table("Bills").insert({
            "group_id": group_id,
            "uploaded_by": user_id,
            "total_amount": total_price,
        }).execute()

        bill_id = response.data[0]["bill_id"]
        translated['bill_id'] = bill_id  # Add bill_id to the main object

        # Process each item and add IDs
        for item in translated['items']:
            item_response = supabase.table("Bill_Items").insert({
                "bill_id": bill_id,
                "item_name": item["item_name"],
                "quantity": item["quantity"],
                "total_price": item["total_price"],
            }).execute()
            
            # Add bill_id and item_id to each item
            item['bill_id'] = bill_id
            item['item_id'] = item_response.data[0]["item_id"]

        return {
            "status": "success",
            "data": translated
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }




@app.post("/audio-split")
async def transcribe_audio(
    group_id: str = Form(...),
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        # Fetch group members
        logger.info(f"Fetching members for group_id: {group_id}")
        members_response = supabase.table("Group_Members").select("user_id").eq("group_id", group_id).execute()
        if not members_response.data:
            return {"status": "error", "message": "No members found in the group"}
        
        user_ids = [member["user_id"] for member in members_response.data]
        
        logger.info(f"Querying names for user_ids: {user_ids}")
        users_response = supabase.table("User_info").select("id, name").in_("id", user_ids).execute()
        if not users_response.data:
            return {"status": "error", "message": "No user information found", "data": []}
        
        # Create a mapping of names to user_ids
        name_to_user_id = {user["name"]: user["id"] for user in users_response.data}

        names = [user["name"] for user in users_response.data]
        logger.info(f"Names fetched: {names}")

        # Save audio to a temporary file
        audio_bytes = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = temp_audio.name
            logger.info(f"Audio file saved temporarily at {temp_audio_path}")

        try:
            # Open the temporary file in binary mode and pass it to the API
            with open(temp_audio_path, "rb") as audio_file:
                voice_split = Voicee()
                found_names = voice_split.transcribe(audio_file, names)
                logger.info(f"Transcription complete: {found_names}")
        finally:
            # Ensure the temporary file is deleted
            os.remove(temp_audio_path)
            logger.info(f"Temporary file {temp_audio_path} deleted.")

        # Convert found names to user_ids
        found_user_ids = [name_to_user_id[name] for name in found_names if name in name_to_user_id]
        logger.info(f"User IDs found: {found_user_ids}")
        return {
            "status": "success",
            "group_id": group_id,
            "user_id": user_id,
            "transcription": found_user_ids,
        }
    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}



@app.get("/group-expense")
async def get_group_expense(
    group_id: str = Query(..., description="Group ID"),
    user_id: str = Query(..., description="User ID"),
):
    individual_expense = IndividualExpense(group_id=group_id, user_id=user_id)
    try:
        # Step 1: Get the list of bill_ids the user belongs to
        bills_response = supabase.table("Bills").select("bill_id").eq("group_id", individual_expense.group_id).execute()

        # Step 2: Extract bill_ids from the response
        bill_ids = [bill["bill_id"] for bill in bills_response.data]  # Corrected variable name

        # Step 3: Check if there are no bills for the group
        if not bill_ids:
            return {
                "status": "success",
                "data": "settled up bo bill",
            }

        # Fetch the splits for the user for the corresponding bill_ids
        splits_data = supabase.table("Splits").select("amount_due", "amount_paid") \
            .in_("bill_id", bill_ids) \
            .eq("user_id", individual_expense.user_id) \
            .execute()
        
        logger.info(f"splits_data: {splits_data.data}")

        if not splits_data.data:
            return {
                "status": "success",
                "data": "settled up no splits",
            }

        # Query to calculate the total amount paid by the user
        paid_query = (
            supabase.table("Payment_Transactions")
            .select("amount")
            .eq("payer_id", individual_expense.user_id)
            .eq("group_id", individual_expense.group_id)
            .execute()
        )

        # Query to calculate the total amount received by the user
        received_query = (
            supabase.table("Payment_Transactions")
            .select("amount")
            .eq("payee_id", individual_expense.user_id)
            .eq("group_id", individual_expense.group_id)
            .execute()
        )

        # Extracting and summing up amounts
        def calculate_total_amount(query_result):
            if query_result.data:
                return sum(transaction["amount"] for transaction in query_result.data)
            return 0

        total_paid = calculate_total_amount(paid_query)
        total_received = calculate_total_amount(received_query)

        # Calculate net amount
        total_amount_due = round(sum(item["amount_due"] for item in splits_data.data) - total_paid, 2)
        total_amount_paid = round(sum(item["amount_paid"] for item in splits_data.data) - total_received, 2)
        logger.info(f"amount_due_total: {total_amount_due}")
        logger.info(f"amount_paid_total: {total_amount_paid}")

        return {
            "status": "success",
            "data": {"owe": total_amount_due, "lent": total_amount_paid}
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


@app.get("/user-total-expense")
async def get_total_expense(user_id: str):
    try:
        # Step 1: Get all groups the user is part of
        groups_response = supabase.table("Group_Members").select("group_id").eq("user_id", user_id).execute()
        
        if not groups_response.data:
            return {
                "status": "success",
                "data": {"owe": 0, "lent": 0}
            }

        group_ids = [group["group_id"] for group in groups_response.data]

        # Step 2: Get all bills from these groups
        bills_response = supabase.table("Bills").select("bill_id").in_("group_id", group_ids).execute()

        if not bills_response.data:
            return {
                "status": "success",
                "data": {"owe": 0, "lent": 0}
            }

        bill_ids = [bill["bill_id"] for bill in bills_response.data]

        # Step 3: Fetch all splits for the user across these bills
        splits_data = supabase.table("Splits").select("amount_due", "amount_paid") \
            .in_("bill_id", bill_ids) \
            .eq("user_id", user_id) \
            .execute()

        if not splits_data.data:
            return {
                "status": "success",
                "data": {"owe": 0, "lent": 0}
            }

        # Step 4: Get all payments made by the user across all groups
        paid_query = (
            supabase.table("Payment_Transactions")
            .select("amount")
            .eq("payer_id", user_id)
            .in_("group_id", group_ids)
            .execute()
        )

        # Step 5: Get all payments received by the user across all groups
        received_query = (
            supabase.table("Payment_Transactions")
            .select("amount")
            .eq("payee_id", user_id)
            .in_("group_id", group_ids)
            .execute()
        )

        # Calculate totals
        def calculate_total_amount(query_result):
            if query_result.data:
                return sum(transaction["amount"] for transaction in query_result.data)
            return 0

        total_paid = calculate_total_amount(paid_query)
        total_received = calculate_total_amount(received_query)

        # Calculate net amounts
        total_amount_due = round(sum(item["amount_due"] for item in splits_data.data) - total_paid, 2)
        total_amount_paid = round(sum(item["amount_paid"] for item in splits_data.data) - total_received, 2)

        return {
            "status": "success",
            "data": {
                "owe": total_amount_due,
                "lent": total_amount_paid
            }
        }

    except Exception as e:
        print(f"Error in get-total-expense: {str(e)}")  # For debugging
        return {
            "status": "error",
            "message": str(e)
        }




@app.post("/add-split")
async def split(adsplit: AddSplit):
    try:
        logger.info(f"Starting split process for bill_id: {adsplit.bill_id}")
        
        '''# Use the group_id from the input directly
        group_id = adsplit.group_id
        logger.info(f"Using provided group_id: {group_id}")'''
        
        # Calculate amount per person (including the payer)
        #removed +1 since payer name is included in splits
        num_people = len(adsplit.user_ids) 
        amount_per_person = round(adsplit.total_price / num_people, 2)
        logger.info(f"Calculated amount per person: {amount_per_person}")
        
        splits_to_insert = []
        index=0
        count=0
        # Create split entries for each user
        if adsplit.payer_id in adsplit.user_ids:
            for user_id in adsplit.user_ids:
                if user_id!=adsplit.payer_id:
                    split_entry = {
                        "bill_id": adsplit.bill_id,
                        "user_id": user_id,
                        "amount_due": amount_per_person,
                        "amount_paid": 0
                    }
                    splits_to_insert.append(split_entry)
                else:
                    split_entry = {
                        "bill_id": adsplit.bill_id,
                        "user_id": user_id,
                        "amount_due": 0,
                        "amount_paid": amount_per_person*(num_people-1)
                    }
                    splits_to_insert.append(split_entry)
        else:
            for user_id in adsplit.user_ids:
                split_entry = {
                        "bill_id": adsplit.bill_id,
                        "user_id": user_id,
                        "amount_due": amount_per_person,
                        "amount_paid": 0
                    }
                splits_to_insert.append(split_entry)
            payer_entry = {
                    "bill_id": adsplit.bill_id,
                    "user_id": adsplit.payer_id,
                    "amount_due": 0,
                    "amount_paid": amount_per_person*num_people
                    }
            splits_to_insert.append(payer_entry)
            
        
        # Insert each split one by one
        logger.info("Attempting to insert splits...")
        
        for split_entry in splits_to_insert:
            response = supabase.table("Splits").insert(split_entry).execute()
            logger.info(f"Insert response for {split_entry['user_id']}: {response}")
        
        return {
            "status": "success",
            "message": "Splits added successfully"
        }
        
    except Exception as e:
        logger.error(f"Error in add-split: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": f"Error details: {str(e)}\nTraceback: {traceback.format_exc()}"
        }




@app.delete("/delete-group")
async def delete_group(group_id: str, user_id: str):
    try:
        # First verify if the group exists and check authorization
        group = supabase.table("Groups").select("*").eq("group_id", group_id).execute()
        
        if not group.data:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "Group not found"
                },
                status_code=404
            )
        
        # Check if the user is the creator of the group
        if group.data[0]["created_by"] != user_id:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "Unauthorized: Only the group creator can delete this group"
                },
                status_code=403
            )

        # Rest of your deletion logic remains the same...
        bills_response = supabase.table("Bills").select("bill_id").eq("group_id", group_id).execute()
        print(f"Found bills: {bills_response.data}")  # Debug log
        
        bill_ids = [bill["bill_id"] for bill in bills_response.data]

        if bill_ids:
            # Step 2: Delete all bill items
            try:
                bill_items_deletion = supabase.table("Bill_Items") \
                    .delete() \
                    .in_("bill_id", bill_ids) \
                    .execute()
                print(f"Deleted bill items: {bill_items_deletion.data}")  # Debug log
            except Exception as e:
                print(f"Error deleting bill items: {str(e)}")
                raise e

            # Step 3: Delete splits
            try:
                splits_deletion = supabase.table("Splits") \
                    .delete() \
                    .in_("bill_id", bill_ids) \
                    .execute()
                print(f"Deleted splits: {splits_deletion.data}")  # Debug log
            except Exception as e:
                print(f"Error deleting splits: {str(e)}")
                raise e

            # Step 4: Delete payment transactions
            try:
                payments_deletion = supabase.table("Payment_Transactions") \
                    .delete() \
                    .eq("group_id", group_id) \
                    .execute()
                print(f"Deleted payments: {payments_deletion.data}")  # Debug log
            except Exception as e:
                print(f"Error deleting payments: {str(e)}")
                raise e

            # Step 5: Delete bills
            try:
                bills_deletion = supabase.table("Bills") \
                    .delete() \
                    .eq("group_id", group_id) \
                    .execute()
                print(f"Deleted bills: {bills_deletion.data}")  # Debug log
            except Exception as e:
                print(f"Error deleting bills: {str(e)}")
                raise e

        # Step 6: Delete group members
        try:
            group_members_deletion = supabase.table("Group_Members") \
                .delete() \
                .eq("group_id", group_id) \
                .execute()
            print(f"Deleted group members: {group_members_deletion.data}")  # Debug log
        except Exception as e:
            print(f"Error deleting group members: {str(e)}")
            raise e

        # Step 7: Delete group
        try:
            group_deletion = supabase.table("Groups") \
                .delete() \
                .eq("group_id", group_id) \
                .execute()
            print(f"Deleted group: {group_deletion.data}")  # Debug log
        except Exception as e:
            print(f"Error deleting group: {str(e)}")
            raise e

        return JSONResponse(
            content={
                "status": "success",
                "message": "Group and all related data deleted successfully"
            },
            status_code=200
        )

    except Exception as e:
        error_message = str(e)
        print(f"Error in delete-group: {error_message}")  # Debug log
        return JSONResponse(
            content={
                "status": "error",
                "message": error_message
            },
            status_code=500
        )

@app.delete("/delete-bill")
async def delete_bill(bill_id: str):
    try:
        # First verify if the bill exists
        bill = supabase.table("Bills").select("*").eq("bill_id", bill_id).execute()
        if not bill.data:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "Bill not found"
                },
                status_code=404
            )

        # Step 1: Delete all bill items
        try:
            bill_items_deletion = supabase.table("Bill_Items") \
                .delete() \
                .eq("bill_id", bill_id) \
                .execute()
            print(f"Deleted bill items: {bill_items_deletion.data}")  # Debug log
        except Exception as e:
            print(f"Error deleting bill items: {str(e)}")
            raise e

        # Step 2: Delete splits
        try:
            splits_deletion = supabase.table("Splits") \
                .delete() \
                .eq("bill_id", bill_id) \
                .execute()
            print(f"Deleted splits: {splits_deletion.data}")  # Debug log
        except Exception as e:
            print(f"Error deleting splits: {str(e)}")
            raise e

        # Step 3: Delete the bill itself
        try:
            bill_deletion = supabase.table("Bills") \
                .delete() \
                .eq("bill_id", bill_id) \
                .execute()
            print(f"Deleted bill: {bill_deletion.data}")  # Debug log
        except Exception as e:
            print(f"Error deleting bill: {str(e)}")
            raise e

        return JSONResponse(
            content={
                "status": "success",
                "message": "Bill and all related data deleted successfully"
            },
            status_code=200
        )

    except Exception as e:
        error_message = str(e)
        print(f"Error in delete-bill: {error_message}")  # Debug log
        return JSONResponse(
            content={
                "status": "error",
                "message": error_message
            },
            status_code=500
        )