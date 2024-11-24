# "source bill_parser/.env_gpt4_parser/bin/activate"
import openai
from openai import OpenAI
import os
from dotenv import load_dotenv
import base64
import json
import re
import requests
from PIL import Image

from io import BytesIO

class Bill_parser:
    def __init__(self):
        # Load environment variables
        load_dotenv("/Users/swagatbhowmik/CS projects/CodeJam2024/bill_parser/.env")
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=openai.api_key)

    def parse(self,image_path):
        # Function to encode the image
        def encode_image(image_path):
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        # Getting the base64 string
        base64_image = encode_image(image_path)

        response = self.client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": "Can you see this bill. I want you to parse item name as item_name, quantity as quantity, price of One as price_per_unit, total price of n quantity as total_price and name of people x,y,z and bill category as bill_category. Give me this as a json",
                },
                {
                "type": "image_url",
                "image_url": {
                    "url":  f"data:image/jpeg;base64,{base64_image}"
                },
                },
            ],
            }
        ],
        )

        return response.choices[0].message.content
    

    def parse_byte(self,image_data):
        def encode_image_from_bytes(image_data):
            # Convert bytes to a file-like object
            image_file = BytesIO(image_data)
            # Open the image using PIL (Pillow)
            image = Image.open(image_file)
            # Save the image to a bytes buffer in a format that preserves quality (e.g., PNG)
            with BytesIO() as output:
                image.save(output, format="PNG")  # Save as PNG regardless of input format
                return base64.b64encode(output.getvalue()).decode('utf-8')

        # Getting the base64 string
        base64_image = encode_image_from_bytes(image_data)
        response = self.client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": "Can you see this bill? I want you to parse item name as item_name, quantity as quantity, price of one as price_per_unit, total price of n quantity as total_price, name of people x, y, z as people, and bill category as bill_category. Please account for any discounted prices visible on the bill and give me the JSON output with these exact fields, maintaining their structure",
                },
                {
                "type": "image_url",
                "image_url": {
                    "url":  f"data:image/jpeg;base64,{base64_image}"
                },
                },
            ],
            }
        ],
        )

        return response.choices[0].message.content
    

    def translate(self,json_obj):
        category=json_obj["bill_category"]
        count=0
        for item in json_obj.get('items', []):
            key=list(item.keys())[0]
            completion = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"You are a concise translator translating the item names to English from {category} bills, if it already in english don't translate it"},
                {"role": "user", "content": f"{item[key]}"}
            ]
            )
            item[key]=completion.choices[0].message.content
        return json_obj
    

    def jsonify_parse(self,bill_json):
        def convert_to_json(string):
            # Step 1: Extract the portion between ``` and ```
            match = re.search(r"```json(.*?)```", string, re.DOTALL)

            if match:
                # Step 2: Remove the "json" keyword from the extracted string
                json_part = match.group(1).strip()
                try:
                    # Parse the JSON portion to ensure it's valid
                    parsed_json = json.loads(json_part)
                    print("Extracted JSON:", parsed_json)
                    return parsed_json
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON: {e}")
                    return None
            else:
                return None
                print("No JSON portion found in the string.")


        # Create a deep copy of the original bill to avoid modifying the input
        copy=json.loads(json.dumps(bill_json))
        json_copy = convert_to_json(copy)
    
    
        # item names
        for item in json_copy.get('items', []):
            # Try to translate, keep original if no translation found
            print(item)
            key=list(item.keys())[0]
            print(item[key])

        
        return json_copy


'''parser=Bill_parser()
bill_json=parser.parse(image_path="/Users/swagatbhowmik/CS projects/CodeJam2024/bill_parser/WhatsApp Image 2024-11-20 at 18.21.11.jpeg")
json_obj=parser.jsonify_parse(bill_json)
print(parser.translate(json_obj))'''







