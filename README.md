# SomaSpark-AI

SomaSpark AI is a fully autonomous, WhatsApp-first AI agent platform designed to solve the immense educational and instructional friction faced by millions of Kenyan parents under the Competency-Based Curriculum (CBC).
Instead of generating copy-paste answers for students , the platform operates entirely through AI agents to deliver localized, easy-to-understand "Parent Lesson Plans". By analyzing images or text descriptions of school assignments , the system empowers parents with pedagogical scaffolding techniques using cheap, readily available household items (such as plastic bottle caps/vifuniko for math or old newspapers for art tracking).

Live Production URL: https://somaspark-service-188464481054.us-central1.run.app 

Product Execution Evidence: evidence/agent_execution_logs.json 

Financial & Profit Evidence: evidence/mpesa_pnl_statement.csv

## Technical Architecture & Agent Workflow
The system runs entirely headless, managing user lifecycles, paywall gates, financial confirmations, multimodal processing, and execution logging natively without manual human data entry.

[Parent WhatsApp Client]

         │
         ▼ (Inbound Text/Image via Webhook Gateway)
         
[Google Cloud Run (FastAPI Service)]

         │
         ├───► [Google Cloud Firestore] ─── (Subscription Check)
         │          │
         │          ▼ (If Unpaid)
         ├───► [Safaricom Daraja API] ────► (STK Push Trigger to Phone)
         │
         ▼ (If Paid: Multi-Modal Contextual Processing)
         
[Vertex AI: Gemini 1.5 Flash Model] 

         │
         ▼ (Asynchronous Data Observability)
         
[Google Cloud Logging ──► Log Explorer Metric Dashboard]

0. Intake & State Isolation: Inbound text or photo messages hit our asynchronous processing service hosted on Google Cloud Run.
1. Autonomous Billing Wall: The container checks user state variables within Google Cloud Firestore (Native Mode). If unpaid or expired, it triggers a programmatic Safaricom M-Pesa STK Push payload to the parent's phone asking for the KSh 300 monthly subscription fee.
2. Instant Account Activation: Once the parent enters their secure PIN, Safaricom's cryptographic event hook notifies our /mpesa-callback endpoint, instantaneously switching their subscription record state to active.
3. Multimodal Analysis & Contextual Layout: The active session transfers image and metadata streams directly into Gemini 1.5 Flash via the Vertex AI SDK. The model extracts visual vectors, aligns them implicitly with Kenya Institute of Curriculum Development (KICD) principles, and formats a markdown-friendly pedagogical guide streaming directly back over WhatsApp.

## Technology Stack
Languages & Frameworks: Python 3.10, FastAPI, Uvicorn 

AI Tooling & Models: Google Vertex AI, Gemini 1.5 Flash 

Cloud Infrastructure (GCP): Cloud Run, Artifact Registry, Cloud Builds, Cloud IAM, Cloud Logging, Cloud Firestore (Native Mode) 

Core Core Interfacing APIs: Safaricom Daraja API (Lipa Na M-Pesa Online), Twilio/Africa's Talking Messaging Gateways
