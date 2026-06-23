import os
from fastapi import FastAPI, Request, Response, status
from google.cloud import firestore
from google.cloud import logging as cloud_logging

# Initialize Google Cloud Services (matching main.py setup)
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "somaspark-ai")
db = firestore.Client(project=PROJECT_ID)
log_client = cloud_logging.Client(project=PROJECT_ID)
logger = log_client.logger("somaspark-agent-logs")

app = FastAPI()

@app.post("/mpesa-callback")
async def mpesa_callback(request: Request):
    """
    Receives the transaction response payload from Safaricom Daraja API
    after a parent completes an STK Push payment.
    """
    try:
        mpesa_data = await request.json()
        
        # Navigate Safaricom's nested JSON structure
        stk_callback = mpesa_data.get("Body", {}).get("stkCallback", {})
        result_code = stk_callback.get("ResultCode")
        merchant_request_id = stk_callback.get("MerchantRequestID")
        
        # Log incoming payment data structure for audit tracking
        logger.log_struct({
            "event": "MPESA_CALLBACK_RECEIVED",
            "merchant_request_id": merchant_request_id,
            "result_code": result_code
        }, severity="INFO")

        # ResultCode 0 means SUCCESSFUL payment
        if result_code == 0:
            callback_metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            
            # Extract essential payment variables natively
            amount = None
            mpesa_receipt_number = None
            phone_number = None

            for item in callback_metadata:
                name = item.get("Name")
                value = item.get("Value")
                if name == "Amount":
                    amount = value
                elif name == "MpesaReceiptNumber":
                    mpesa_receipt_number = value
                elif name == "PhoneNumber":
                    phone_number = str(value)

            if phone_number:
                # Standardize phone formats (Ensure it matches WhatsApp formatting '254...')
                if phone_number.startswith("7") or phone_number.startswith("1"):
                    phone_number = f"254{phone_number}"

                # AGENT EXECUTION: Update Firestore to activate the user account immediately
                user_ref = db.collection("users").document(phone_number)
                user_ref.set({
                    "is_active": True,
                    "amount_paid": amount,
                    "mpesa_receipt": mpesa_receipt_number,
                    "merchant_request_id": merchant_request_id,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }, merge=True)

                # Continuous execution log verification for "Product Evidence"
                logger.log_struct({
                    "event": "AGENT_ACCOUNT_ACTIVATED",
                    "user": phone_number,
                    "receipt": mpesa_receipt_number,
                    "amount": amount
                }, severity="INFO")

                return Response(content="Success acknowledged", status_code=status.HTTP_200_OK)
        
        else:
            # Payment cancelled or failed (e.g., wrong PIN, insufficient funds)
            logger.log_text(
                f"AGENT_DECISION: Payment failed for Request ID {merchant_request_id}. Code: {result_code}", 
                severity="WARNING"
            )
            return Response(content="Failure acknowledged", status_code=status.HTTP_200_OK)

    except Exception as e:
        logger.log_text(f"CALLBACK_ERROR: Critical failure in processing payload. Error: {str(e)}", severity="ERROR")
        return Response(content="Internal error mapping data", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)