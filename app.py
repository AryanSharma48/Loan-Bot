import sqlite3
import json
import os
import requests  # We'll use requests to call the Gemini API
from flask import Flask, request, jsonify, render_template, send_from_directory
from fpdf import FPDF # For the PDF "agent"

# --- Flask App Setup ---
app = Flask(__name__, template_folder='templates', static_folder='static')

# --- Gemini API Configuration ---

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key="

API_KEY = "AIzaSyBLtV6PO09ySknbPfDNaxVytsRdjNU1-6Y" 

# --- AGENT 1: KYC Verification Tool ---
# This is our first "Loan Processing Agent". It's just a Python function.
def agent_verify_kyc(customer_name):
    """Checks the KYC (Know Your Customer) status for a given customer."""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT kyc_status FROM customers WHERE lower(name) = ?", (customer_name,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {"status": result[0]} # e.g., 'verified', 'pending'
        else:
            return {"status": "not_found"}
    except Exception as e:
        return {"error": str(e)}

# --- AGENT 2: Credit Evaluation Tool ---
# This is our second "agent".
def agent_evaluate_credit(customer_name):
    """Fetches the mock credit score and max loan limit for a customer."""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT credit_score, loan_limit FROM customers WHERE lower(name) = ?", (customer_name,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {"credit_score": result[0], "loan_limit": result[1]}
        else:
            return {"error": "user_not_found"}
    except Exception as e:
        return {"error": str(e)}

# --- AGENT 3: Sanction Letter Generation Tool ---
# This is our third "agent".
def agent_generate_sanction(customer_name, loan_amount):
    """Generates a PDF sanction letter and returns a download link."""
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'LOAN SANCTION LETTER', 0, 1, 'C')
        pdf.ln(20)
        
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f'Dear {customer_name},', 0, 1)
        pdf.ln(10)
        pdf.multi_cell(0, 10, f'This is to confirm that your personal loan of ${loan_amount:,.2f} has been reviewed and sanctioned.')
        pdf.ln(10)
        pdf.multi_cell(0, 10, 'We are excited to be a part of your financial journey.')
        pdf.ln(20)
        pdf.cell(0, 10, 'Sincerely,', 0, 1)
        pdf.cell(0, 10, 'The EY-Bot Team', 0, 1)
        
        # Ensure the 'static' directory exists
        if not os.path.exists('static'):
            os.makedirs('static')
            
        # Save the file to the 'static' folder
        filepath = f'static/sanction_{customer_name}.pdf'
        pdf.output(filepath)
        
        # Return the web-accessible download link
        return {"download_link": f'/{filepath}'}
    except Exception as e:
        print(f"Error in PDF generation: {e}")
        return {"error": str(e)}

# --- Define Our "Tools" for the AI ---
# This is the "Function Calling" part. We describe our Python functions
# to the Gemini API in its required JSON format.
tools = [
    {
        "functionDeclarations": [
            {
                "name": "agent_verify_kyc",
                "description": "Get the KYC (Know Your Customer) status for a user. Call this first.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "customer_name": {"type": "STRING", "description": "The customer's first name."}
                    },
                    "required": ["customer_name"]
                }
            },
            {
                "name": "agent_evaluate_credit",
                "description": "Get a user's credit score and maximum loan limit *after* their KYC is 'verified'.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "customer_name": {"type": "STRING", "description": "The customer's first name."}
                    },
                    "required": ["customer_name"]
                }
            },
            {
                "name": "agent_generate_sanction",
                "description": "Generate a PDF sanction letter *after* a loan is fully approved. Confirms the final amount with the user.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "customer_name": {"type": "STRING", "description": "The customer's first name."},
                        "loan_amount": {"type": "NUMBER", "description": "The final approved loan amount."}
                    },
                    "required": ["customer_name", "loan_amount"]
                }
            }
        ]
    }
]

# --- System Prompt ---
# This guides the AI's personality and goals (Bonus Creativity!)
SYSTEM_PROMPT = """
You are "Loamy", a friendly, persuasive, and intelligent conversational sales assistant for EY Personal Loans. 
Your goal is to guide users through the loan application process and get them to accept a loan.
You must be empathetic, encouraging, and human-like.
NEVER be robotic. Use emotion-based persuasion (e.g., "That's fantastic news!", "I can help you achieve that dream.").

Your process is:
1.  **Greet the user** and ask for their name to get started.
2.  **Call `agent_verify_kyc`** with their name.
3.  **If KYC is 'pending' or 'failed'**: Gently inform them and stop.
4.  **If KYC is 'verified'**: Congratulate them! Then, ask how much they'd like to borrow.
5.  **Once you have an amount**: Call `agent_evaluate_credit`.
6.  **Analyze credit**:
    * If `credit_score` < 650: Gently reject them, explaining the minimum score.
    * If `loan_amount` > `loan_limit`: Be persuasive! Say "You've been approved for a bit less, but it's a great rate. Your limit is ${loan_limit}. Would you like to proceed with that?"
    * If `loan_amount` <= `loan_limit`: "Great news! You're eligible for the full ${loan_amount}!"
7.  **Final Confirmation**: Ask for a final "yes" to confirm the amount.
8.  **Call `agent_generate_sanction`**: Once confirmed, call this agent. After the call is successful, just say "Great news! Your sanction letter is ready!" DO NOT include the link or any markdown in your text response. The system will create the clickable link automatically.
"""

# Store our Python functions in a dictionary to call them by name
available_agents = {
    "agent_verify_kyc": agent_verify_kyc,
    "agent_evaluate_credit": agent_evaluate_credit,
    "agent_generate_sanction": agent_generate_sanction,
}

# --- Main Flask Routes ---

@app.route('/')
def index():
    """Serves the main index.html file."""
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    """Serves files from the 'static' directory (for PDF downloads)."""
    return send_from_directory('static', path)

@app.route('/chat', methods=['POST'])
def chat():
    """The main 'Conversational Master Agent' endpoint."""
    data = request.json
    user_history = data.get('history', [])
    

    # Prepare the payload for the Gemini API
    payload = {
        "contents": user_history,
        "tools": tools,
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]}
    }

    # --- The "Agentic Loop" ---
    # This loop allows the AI to call multiple tools in a row (e.g., KYC -> Credit)
    # without the user having to say anything.
    
    while True:
        try:
            # 1. Send to Gemini
            response = requests.post(f"{GEMINI_API_URL}{API_KEY}", json=payload)
            response.raise_for_status() # Raise an error for bad responses
            
            gemini_response = response.json()

            # Handle errors from Gemini
            if "candidates" not in gemini_response:
                print("Error: No candidates in response", gemini_response)
                return jsonify({"reply": "I'm sorry, I'm having a little trouble thinking right now. Please try again in a moment."})

            candidate = gemini_response["candidates"][0]
            
            # If the AI is just talking, break the loop and send the reply
            if "functionCall" not in candidate["content"]["parts"][0]:
                text_reply = candidate["content"]["parts"][0]["text"]
                return jsonify({"reply": text_reply})

            # 2. If Gemini wants to call a function (an "agent")
            function_call = candidate["content"]["parts"][0]["functionCall"]
            func_name = function_call["name"]
            func_args = function_call["args"]
            
            print(f"AI -> Calling Agent: {func_name} with args {func_args}")

            # 3. Call the corresponding Python function
            if func_name in available_agents:
                func_to_call = available_agents[func_name]
                # Use ** to unpack the arguments from the JSON
                function_result = func_to_call(**func_args)
                
                print(f"Agent -> Result: {function_result}")

                # 4. Add the function's result to the history
                # This tells the AI what happened.
                payload["contents"].append(candidate["content"]) # Add the AI's "call" turn
                payload["contents"].append({
                    "role": "function",
                    "parts": [
                        {"functionResponse": {
                            "name": func_name,
                            "response": function_result
                        }}
                    ]
                })
                # Loop continues, calling Gemini again with the new info
            
            else:
                # This should not happen if our prompt is good
                return jsonify({"reply": f"Error: Unknown agent {func_name}"})

        except requests.exceptions.RequestException as e:
            print(f"HTTP Request error: {e}")
            return jsonify({"reply": f"Error communicating with AI: {e}"}), 500
        except Exception as e:
            print(f"Error in chat loop: {e}")
            return jsonify({"reply": f"An unexpected error occurred: {e}"}), 500

# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)
