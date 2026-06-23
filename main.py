import os
import requests
from fastapi import FastAPI, Request, Response, status
from contextlib import asynccontextmanager

# Define global placeholders for clients
db = None
logger = None
model = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Safely initializes heavy Cloud clients when the server boots up."""
    global db, logger, model
    try:
        import vertexai
        from google.cloud import firestore
        from google.cloud import logging as cloud_logging
        from vertexai.generative_models import GenerativeModel

        PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "somaspark-ai")
        LOCATION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

        # Initialize Vertex AI
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        model = GenerativeModel("gemini-1.5-flash", system_instruction=CBC_SYSTEM_PROMPT)

        # Initialize Firestore & Logging
        db = firestore.Client(project=PROJECT_ID)
        log_client = cloud_logging.Client(project=PROJECT_ID)
        logger = log_client.logger("somaspark-agent-logs")
        
        print("🚀 SomaSpark Agents initialized successfully!")
    except Exception as e:
        print(f"❌ CRITICAL STARTUP ERROR: {str(e)}")
    yield
    # Clean up operations go here if needed

# Initialize FastAPI with the lifecycle wrapper
app = FastAPI(lifespan=lifespan)

CBC_SYSTEM_PROMPT = """
You are SomaSpark AI, an expert virtual assistant for Kenyan parents navigating the Competency-Based Curriculum (CBC). 
Provide a practical, easy-to-understand "Parent Lesson Plan" using cheap, locally available household items in Kenya.
"""

def check_subscription(phone_number: str) -> bool:
    if db is None:
        return False  # Fallback if DB client initialization failed
    try:
        user_ref = db.collection("users").document(phone_number)
        doc = user_ref.get()
        return doc.to_dict().get("is_active", False) if doc.exists else False
    except Exception:
        return False

# ==========================================
# 📲 WHATSAPP INTAKE WEBHOOK ROUTE
# ==========================================
@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    from vertexai.generative_models import Part
    form_data = await request.form()
    from_number = form_data.get("From", "").replace("whatsapp:", "")
    body_text = form_data.get("Body", "")
    media_url = form_data.get("MediaUrl0")
    media_type = form_data.get("ContentType0", "")

    if logger:
        logger.log_text(f"AGENT_INBOUND: Msg from {from_number}", severity="INFO")

    if not check_subscription(from_number):
        return Response(
            content="Mambo! Welcome to SomaSpark AI. 🚀 Please complete the KSh 300 M-Pesa prompt on your phone to unlock.",
            media_type="text/plain"
        )

    if model is None:
        return Response(content="System initializing, please retry in 5 seconds.", media_type="text/plain")

    prompt_contents = []
    if media_url and "image" in media_type:
        image_bytes = requests.get(media_url).content
        prompt_contents.append(Part.from_bytes(data=image_bytes, mime_type=media_type))
        prompt_contents.append(f"Analyze this assignment: {body_text}")
    else:
        prompt_contents.append(body_text)

    response = model.generate_content(prompt_contents)
    return Response(content=response.text, media_type="text/plain")

# ==========================================
# 💰 M-PESA DARAJA CALLBACK ROUTE
# ==========================================
@app.post("/mpesa-callback")
async def mpesa_callback(request: Request):
    try:
        mpesa_data = await request.json()
        stk_callback = mpesa_data.get("Body", {}).get("stkCallback", {})
        result_code = stk_callback.get("ResultCode")
        
        if result_code == 0 and db is not None:
            callback_metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            amount, mpesa_receipt_number, phone_number = None, None, None
            for item in callback_metadata:
                if item.get("Name") == "Amount": amount = item.get("Value")
                elif item.get("Name") == "MpesaReceiptNumber": mpesa_receipt_number = item.get("Value")
                elif item.get("Name") == "PhoneNumber": phone_number = str(item.get("Value"))

            if phone_number:
                if phone_number.startswith("7") or phone_number.startswith("1"):
                    phone_number = f"254{phone_number}"
                
                db.collection("users").document(phone_number).set({
                    "is_active": True,
                    "amount_paid": amount,
                    "mpesa_receipt": mpesa_receipt_number,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }, merge=True)
                
        return Response(content="Success acknowledged", status_code=status.HTTP_200_OK)
    except Exception as e:
        return Response(content=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/")
def health_check():
    return {"status": "healthy", "agent": "SomaSpark AI"}