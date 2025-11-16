<<<<<<< HEAD
# app.py
from flask import Flask, render_template, request, jsonify
from datetime import datetime
from dotenv import load_dotenv
import os
import logging
import uuid

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# load .env (if present)
load_dotenv()

from db_helpers import (
    init_db, create_session, log_message, log_result, close_session,
    get_sessions, get_messages_for_session, get_results_for_session,
    update_session_patient_info, get_conversation_history
)
from symptom_api import call_symptom_api_mock, has_red_flag, call_deepseek

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config['JSON_SORT_KEYS'] = False

# Init DB (creates tables if not present)
init_db()

# Check API status at startup
DEEPSEEK_API_AVAILABLE = False
try:
    if os.getenv("DEEPSEEK_API_KEY"):
        DEEPSEEK_API_AVAILABLE = True
        logger.info("DeepSeek API key found")
    else:
        logger.warning("No DeepSeek API key found")
except Exception as e:
    logger.error(f"Error checking API status: {e}")

# Store active conversations (in production, use Redis)
active_conversations = {}

@app.route("/")
def index():
    return render_template("index.html", deepseek_available=DEEPSEEK_API_AVAILABLE)

@app.route("/api/start_conversation", methods=["POST"])
def start_conversation():
    """Start a new conversation session"""
    data = request.json or {}
    age = data.get("age")
    gender = data.get("gender")
    patient_name = data.get("patient_name", "").strip()
    
    # Create new session
    session_id = create_session(
        start_time=datetime.utcnow(),
        age=(int(age) if age and str(age).isdigit() else None),
        gender=(gender or None),
        patient_name=(patient_name or None)
    )
    
    # Store conversation context
    conversation_id = str(uuid.uuid4())
    active_conversations[conversation_id] = {
        "session_id": session_id,
        "patient_info": {
            "age": age,
            "gender": gender,
            "patient_name": patient_name
        },
        "message_history": [],
        "created_at": datetime.utcnow()
    }
    
    # Log initial message
    if patient_name:
        log_message(session_id, "meta", f"patient_name:{patient_name}")
    
    welcome_message = "👋 Hello! I'm your medical assistant. I can help you understand your symptoms and provide guidance. How can I help you today?"
    log_message(session_id, "bot", welcome_message)
    
    return jsonify({
        "conversation_id": conversation_id,
        "session_id": session_id,
        "welcome_message": welcome_message
    })

@app.route("/api/send_message", methods=["POST"])
def send_message():
    """Process a message in an existing conversation"""
    data = request.json or {}
    conversation_id = data.get("conversation_id")
    message = data.get("message", "").strip()
    
    if not conversation_id:
        return jsonify({"error": "No conversation ID provided"}), 400
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    # Get conversation context
    conversation = active_conversations.get(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    session_id = conversation["session_id"]
    patient_info = conversation["patient_info"]
    
    # Add user message to history and log it
    conversation["message_history"].append({"role": "user", "content": message, "timestamp": datetime.utcnow()})
    log_message(session_id, "user", message)
    
    # Check for red flags immediately
    if has_red_flag(message):
        logger.info(f"Red flag detected in conversation {conversation_id}")
        result = {
            "triage": "🚨 Emergency — seek immediate care",
            "conditions": [{"name": "Potential emergency condition", "probability": 0.8}],
            "advice": "Symptoms indicate possible emergency. Call emergency services or go to nearest ER immediately.",
            "selfcare": ["Do not delay - go to emergency department"],
            "warning": [
                "Severe chest pain or pressure",
                "Difficulty breathing or shortness of breath", 
                "Loss of consciousness or sudden confusion"
            ],
            "summary": "Immediate emergency care is recommended based on the symptoms you provided.",
            "patient_name": patient_info.get("patient_name"),
            "red_flag": True
        }
        
        log_result(session_id, "redflag", result)
        log_message(session_id, "bot", result["advice"])
        
        # Add to conversation history
        conversation["message_history"].append({"role": "bot", "content": result["advice"], "timestamp": datetime.utcnow()})
        
        return jsonify({
            "response": result["advice"],
            "analysis": result,
            "is_emergency": True
        })
    
    # Check if this is a medical query
    medical_keywords = [
        'pain', 'hurt', 'sick', 'fever', 'cough', 'headache', 'nausea', 
        'vomit', 'dizzy', 'rash', 'swollen', 'bleed', 'breath', 'chest',
        'stomach', 'throat', 'cold', 'flu', 'symptom', 'feel', 'unwell'
    ]
    
    is_medical_query = any(keyword in message.lower() for keyword in medical_keywords)
    
    if not is_medical_query:
        # General conversation response
        general_responses = [
            "I'm here to help with medical concerns. Could you describe any symptoms you're experiencing?",
            "I specialize in symptom assessment. Please tell me about any health issues you're having.",
            "For medical assistance, please describe your symptoms and I'll do my best to help.",
            "I understand you have a question. I'm designed to help with medical symptoms and health concerns. What symptoms are you experiencing?"
        ]
        
        response = general_responses[len(conversation["message_history"]) % len(general_responses)]
        log_message(session_id, "bot", response)
        conversation["message_history"].append({"role": "bot", "content": response, "timestamp": datetime.utcnow()})
        
        return jsonify({
            "response": response,
            "is_medical": False
        })
    
    # Medical query - analyze symptoms
    try:
        # Use mock for now due to API issues, but you can switch based on preference
        use_api = "mock"  # You can make this configurable
        
        if use_api == "deepseek" and DEEPSEEK_API_AVAILABLE:
            result = call_deepseek(message, age=patient_info.get("age"), gender=patient_info.get("gender"))
            api_name = "deepseek"
        else:
            result = call_symptom_api_mock(message, age=patient_info.get("age"), gender=patient_info.get("gender"))
            api_name = "mock"
            
    except Exception as api_error:
        logger.error(f"API call failed: {api_error}")
        # Fallback to mock on any API error
        result = call_symptom_api_mock(message, age=patient_info.get("age"), gender=patient_info.get("gender"))
        api_name = "mock_fallback"
        result["api_note"] = "Primary API unavailable - using backup analysis"
    
    # Ensure all required keys exist
    required_keys = ["triage", "conditions", "advice", "selfcare", "warning", "summary"]
    for key in required_keys:
        result.setdefault(key, "")
        
    if not result.get("selfcare"):
        result["selfcare"] = ["Stay hydrated and rest."]
    if not result.get("warning"):
        result["warning"] = ["Seek medical help if symptoms worsen."]
    if not result.get("summary"):
        top_condition = result.get("conditions", [{}])[0].get("name") if result.get("conditions") else None
        if top_condition:
            result["summary"] = f"Most likely: {top_condition}. {result.get('advice', 'Follow up with a physician if unsure.')}"
        else:
            result["summary"] = "Please consult with a healthcare provider for proper diagnosis."
            
    result["patient_name"] = patient_info.get("patient_name")
    
    # Log and store results
    log_result(session_id, api_name, result)
    log_message(session_id, "bot", result.get("advice", ""))
    
    # Add to conversation history
    conversation["message_history"].append({"role": "bot", "content": result["advice"], "timestamp": datetime.utcnow()})
    
    # Prepare follow-up question
    follow_up_questions = [
        "Is there anything else you'd like to know about your symptoms?",
        "Would you like me to clarify anything about this assessment?",
        "Do you have any other symptoms you'd like to discuss?",
        "Is there anything else about your health that you're concerned about?"
    ]
    
    follow_up = follow_up_questions[len(conversation["message_history"]) % len(follow_up_questions)]
    
    return jsonify({
        "response": result["advice"],
        "analysis": result,
        "is_medical": True,
        "follow_up": follow_up
    })

@app.route("/api/update_patient_info", methods=["POST"])
def update_patient_info():
    """Update patient information for an existing conversation"""
    data = request.json or {}
    conversation_id = data.get("conversation_id")
    
    if not conversation_id:
        return jsonify({"error": "No conversation ID provided"}), 400
    
    conversation = active_conversations.get(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    # Update patient info
    age = data.get("age")
    gender = data.get("gender")
    patient_name = data.get("patient_name", "").strip()
    
    conversation["patient_info"].update({
        "age": age,
        "gender": gender,
        "patient_name": patient_name
    })
    
    # Update session in database
    update_session_patient_info(
        conversation["session_id"],
        age=(int(age) if age and str(age).isdigit() else None),
        gender=(gender or None),
        patient_name=(patient_name or None)
    )
    
    return jsonify({"success": True, "message": "Patient information updated"})

@app.route("/api/conversation/<conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    """Get conversation history"""
    conversation = active_conversations.get(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    return jsonify({
        "conversation_id": conversation_id,
        "session_id": conversation["session_id"],
        "patient_info": conversation["patient_info"],
        "message_history": conversation["message_history"],
        "created_at": conversation["created_at"].isoformat()
    })

@app.route("/api/end_conversation", methods=["POST"])
def end_conversation():
    """End a conversation and close the session"""
    data = request.json or {}
    conversation_id = data.get("conversation_id")
    
    if not conversation_id:
        return jsonify({"error": "No conversation ID provided"}), 400
    
    conversation = active_conversations.get(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    # Close the session in database
    close_session(conversation["session_id"])
    
    # Remove from active conversations
    del active_conversations[conversation_id]
    
    return jsonify({"success": True, "message": "Conversation ended"})

@app.route("/check", methods=["POST"])
def check():
    """Legacy endpoint for single symptom check (for backward compatibility)"""
    data = request.json or {}
    age = data.get("age")
    gender = data.get("gender")
    patient_name = (data.get("patient_name","") or "").strip()
    symptoms = (data.get("symptoms","") or "").strip()
    use_api = data.get("use_api", "mock")

    if not symptoms:
        return jsonify({"error":"Please enter symptoms."}), 400

    # create session and log user message
    session_id = create_session(
        start_time=datetime.utcnow(),
        age=(int(age) if age and str(age).isdigit() else None),
        gender=(gender or None),
        patient_name=(patient_name or None)
    )
    if patient_name:
        log_message(session_id, "meta", f"patient_name:{patient_name}")
    log_message(session_id, "user", symptoms)

    # quick red-flag handling
    if has_red_flag(symptoms):
        logger.info(f"Red flag detected for session {session_id}")
        result = {
            "triage": "🚨 Emergency — seek immediate care",
            "conditions": [{"name": "Potential emergency condition", "probability": 0.8}],
            "advice": "Symptoms indicate possible emergency. Call emergency services or go to nearest ER immediately.",
            "selfcare": ["Do not delay - go to emergency department"],
            "warning": [
                "Severe chest pain or pressure",
                "Difficulty breathing or shortness of breath", 
                "Loss of consciousness or sudden confusion"
            ],
            "summary": "Immediate emergency care is recommended based on the symptoms you provided.",
            "patient_name": patient_name,
            "red_flag": True
        }
        log_result(session_id, "redflag", result)
        log_message(session_id, "bot", result["advice"])
        close_session(session_id)
        return jsonify({"session_id": session_id, "result": result})

    # Call chosen API
    logger.info(f"Calling API: {use_api} for session {session_id}")
    
    if use_api == "deepseek" and DEEPSEEK_API_AVAILABLE:
        result = call_deepseek(symptoms, age=age, gender=gender)
        api_name = "deepseek"
    else:
        result = call_symptom_api_mock(symptoms, age=age, gender=gender)
        api_name = "mock"

    # Ensure all required keys exist
    required_keys = ["triage", "conditions", "advice", "selfcare", "warning", "summary"]
    for key in required_keys:
        result.setdefault(key, "")
        
    if not result.get("selfcare"):
        result["selfcare"] = ["Stay hydrated and rest."]
    if not result.get("warning"):
        result["warning"] = ["Seek medical help if symptoms worsen."]
    if not result.get("summary"):
        top_condition = result.get("conditions", [{}])[0].get("name") if result.get("conditions") else None
        if top_condition:
            result["summary"] = f"Most likely: {top_condition}. {result.get('advice', 'Follow up with a physician if unsure.')}"
        else:
            result["summary"] = "Please consult with a healthcare provider for proper diagnosis."
            
    result["patient_name"] = patient_name

    # Log and finish
    log_result(session_id, api_name, result)
    log_message(session_id, "bot", result.get("advice",""))
    close_session(session_id)

    logger.info(f"Session {session_id} completed successfully")
    return jsonify({"session_id": session_id, "result": result})

@app.route("/history", methods=["GET"])
def history():
    try:
        rows = get_sessions(100)
        sessions = []
        for r in rows:
            sessions.append({
                "id": r[0],
                "session_hash": r[1],
                "start_time": r[2],
                "age": r[3],
                "gender": r[4],
                "patient_name": r[5] if len(r) > 5 else None
            })
        return render_template("history.html", sessions=sessions)
    except Exception as e:
        logger.error(f"Error loading history: {e}")
        return render_template("history.html", sessions=[])

@app.route("/history/<int:session_id>", methods=["GET"])
def view_session(session_id):
    try:
        messages = get_messages_for_session(session_id)
        results = get_results_for_session(session_id)
        return render_template("session_view.html", session_id=session_id, messages=messages, results=results)
    except Exception as e:
        logger.error(f"Error viewing session {session_id}: {e}")
        return render_template("session_view.html", session_id=session_id, messages=[], results=[])

@app.route("/conversation/<int:session_id>", methods=["GET"])
def view_conversation(session_id):
    """View full conversation for a session"""
    try:
        conversation = get_conversation_history(session_id)
        return render_template("conversation_view.html", 
                             session_id=session_id, 
                             conversation=conversation)
    except Exception as e:
        logger.error(f"Error viewing conversation {session_id}: {e}")
        return render_template("conversation_view.html", 
                             session_id=session_id, 
                             conversation=[])

# Health check endpoints
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "deepseek_api_available": DEEPSEEK_API_AVAILABLE,
        "active_conversations": len(active_conversations)
    })

@app.route("/debug/api-status", methods=["GET"])
def api_status():
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    return jsonify({
        "deepseek_api_key_set": bool(deepseek_key),
        "deepseek_key_length": len(deepseek_key) if deepseek_key else 0,
        "deepseek_api_available": DEEPSEEK_API_AVAILABLE,
        "environment_loaded": True,
        "active_conversations": len(active_conversations)
    })

# Clean up old conversations (basic implementation)
def cleanup_old_conversations():
    """Remove conversations older than 24 hours"""
    current_time = datetime.utcnow()
    expired_conversations = []
    
    for conv_id, conv_data in active_conversations.items():
        if (current_time - conv_data["created_at"]).total_seconds() > 24 * 3600:  # 24 hours
            expired_conversations.append(conv_id)
    
    for conv_id in expired_conversations:
        close_session(active_conversations[conv_id]["session_id"])
        del active_conversations[conv_id]
    
    if expired_conversations:
        logger.info(f"Cleaned up {len(expired_conversations)} expired conversations")

if __name__ == "__main__":
    # Clean up on startup
    cleanup_old_conversations()
=======
# app.py
from flask import Flask, render_template, request, jsonify
from datetime import datetime
from dotenv import load_dotenv
import os
import logging
import uuid

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# load .env (if present)
load_dotenv()

from db_helpers import (
    init_db, create_session, log_message, log_result, close_session,
    get_sessions, get_messages_for_session, get_results_for_session,
    update_session_patient_info, get_conversation_history
)
from symptom_api import call_symptom_api_mock, has_red_flag, call_deepseek

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config['JSON_SORT_KEYS'] = False

# Init DB (creates tables if not present)
init_db()

# Check API status at startup
DEEPSEEK_API_AVAILABLE = False
try:
    if os.getenv("DEEPSEEK_API_KEY"):
        DEEPSEEK_API_AVAILABLE = True
        logger.info("DeepSeek API key found")
    else:
        logger.warning("No DeepSeek API key found")
except Exception as e:
    logger.error(f"Error checking API status: {e}")

# Store active conversations (in production, use Redis)
active_conversations = {}

@app.route("/")
def index():
    return render_template("index.html", deepseek_available=DEEPSEEK_API_AVAILABLE)

@app.route("/api/start_conversation", methods=["POST"])
def start_conversation():
    """Start a new conversation session"""
    data = request.json or {}
    age = data.get("age")
    gender = data.get("gender")
    patient_name = data.get("patient_name", "").strip()
    
    # Create new session
    session_id = create_session(
        start_time=datetime.utcnow(),
        age=(int(age) if age and str(age).isdigit() else None),
        gender=(gender or None),
        patient_name=(patient_name or None)
    )
    
    # Store conversation context
    conversation_id = str(uuid.uuid4())
    active_conversations[conversation_id] = {
        "session_id": session_id,
        "patient_info": {
            "age": age,
            "gender": gender,
            "patient_name": patient_name
        },
        "message_history": [],
        "created_at": datetime.utcnow()
    }
    
    # Log initial message
    if patient_name:
        log_message(session_id, "meta", f"patient_name:{patient_name}")
    
    welcome_message = "👋 Hello! I'm your medical assistant. I can help you understand your symptoms and provide guidance. How can I help you today?"
    log_message(session_id, "bot", welcome_message)
    
    return jsonify({
        "conversation_id": conversation_id,
        "session_id": session_id,
        "welcome_message": welcome_message
    })

@app.route("/api/send_message", methods=["POST"])
def send_message():
    """Process a message in an existing conversation"""
    data = request.json or {}
    conversation_id = data.get("conversation_id")
    message = data.get("message", "").strip()
    
    if not conversation_id:
        return jsonify({"error": "No conversation ID provided"}), 400
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    # Get conversation context
    conversation = active_conversations.get(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    session_id = conversation["session_id"]
    patient_info = conversation["patient_info"]
    
    # Add user message to history and log it
    conversation["message_history"].append({"role": "user", "content": message, "timestamp": datetime.utcnow()})
    log_message(session_id, "user", message)
    
    # Check for red flags immediately
    if has_red_flag(message):
        logger.info(f"Red flag detected in conversation {conversation_id}")
        result = {
            "triage": "🚨 Emergency — seek immediate care",
            "conditions": [{"name": "Potential emergency condition", "probability": 0.8}],
            "advice": "Symptoms indicate possible emergency. Call emergency services or go to nearest ER immediately.",
            "selfcare": ["Do not delay - go to emergency department"],
            "warning": [
                "Severe chest pain or pressure",
                "Difficulty breathing or shortness of breath", 
                "Loss of consciousness or sudden confusion"
            ],
            "summary": "Immediate emergency care is recommended based on the symptoms you provided.",
            "patient_name": patient_info.get("patient_name"),
            "red_flag": True
        }
        
        log_result(session_id, "redflag", result)
        log_message(session_id, "bot", result["advice"])
        
        # Add to conversation history
        conversation["message_history"].append({"role": "bot", "content": result["advice"], "timestamp": datetime.utcnow()})
        
        return jsonify({
            "response": result["advice"],
            "analysis": result,
            "is_emergency": True
        })
    
    # Check if this is a medical query
    medical_keywords = [
        'pain', 'hurt', 'sick', 'fever', 'cough', 'headache', 'nausea', 
        'vomit', 'dizzy', 'rash', 'swollen', 'bleed', 'breath', 'chest',
        'stomach', 'throat', 'cold', 'flu', 'symptom', 'feel', 'unwell'
    ]
    
    is_medical_query = any(keyword in message.lower() for keyword in medical_keywords)
    
    if not is_medical_query:
        # General conversation response
        general_responses = [
            "I'm here to help with medical concerns. Could you describe any symptoms you're experiencing?",
            "I specialize in symptom assessment. Please tell me about any health issues you're having.",
            "For medical assistance, please describe your symptoms and I'll do my best to help.",
            "I understand you have a question. I'm designed to help with medical symptoms and health concerns. What symptoms are you experiencing?"
        ]
        
        response = general_responses[len(conversation["message_history"]) % len(general_responses)]
        log_message(session_id, "bot", response)
        conversation["message_history"].append({"role": "bot", "content": response, "timestamp": datetime.utcnow()})
        
        return jsonify({
            "response": response,
            "is_medical": False
        })
    
    # Medical query - analyze symptoms
    try:
        # Use mock for now due to API issues, but you can switch based on preference
        use_api = "mock"  # You can make this configurable
        
        if use_api == "deepseek" and DEEPSEEK_API_AVAILABLE:
            result = call_deepseek(message, age=patient_info.get("age"), gender=patient_info.get("gender"))
            api_name = "deepseek"
        else:
            result = call_symptom_api_mock(message, age=patient_info.get("age"), gender=patient_info.get("gender"))
            api_name = "mock"
            
    except Exception as api_error:
        logger.error(f"API call failed: {api_error}")
        # Fallback to mock on any API error
        result = call_symptom_api_mock(message, age=patient_info.get("age"), gender=patient_info.get("gender"))
        api_name = "mock_fallback"
        result["api_note"] = "Primary API unavailable - using backup analysis"
    
    # Ensure all required keys exist
    required_keys = ["triage", "conditions", "advice", "selfcare", "warning", "summary"]
    for key in required_keys:
        result.setdefault(key, "")
        
    if not result.get("selfcare"):
        result["selfcare"] = ["Stay hydrated and rest."]
    if not result.get("warning"):
        result["warning"] = ["Seek medical help if symptoms worsen."]
    if not result.get("summary"):
        top_condition = result.get("conditions", [{}])[0].get("name") if result.get("conditions") else None
        if top_condition:
            result["summary"] = f"Most likely: {top_condition}. {result.get('advice', 'Follow up with a physician if unsure.')}"
        else:
            result["summary"] = "Please consult with a healthcare provider for proper diagnosis."
            
    result["patient_name"] = patient_info.get("patient_name")
    
    # Log and store results
    log_result(session_id, api_name, result)
    log_message(session_id, "bot", result.get("advice", ""))
    
    # Add to conversation history
    conversation["message_history"].append({"role": "bot", "content": result["advice"], "timestamp": datetime.utcnow()})
    
    # Prepare follow-up question
    follow_up_questions = [
        "Is there anything else you'd like to know about your symptoms?",
        "Would you like me to clarify anything about this assessment?",
        "Do you have any other symptoms you'd like to discuss?",
        "Is there anything else about your health that you're concerned about?"
    ]
    
    follow_up = follow_up_questions[len(conversation["message_history"]) % len(follow_up_questions)]
    
    return jsonify({
        "response": result["advice"],
        "analysis": result,
        "is_medical": True,
        "follow_up": follow_up
    })

@app.route("/api/update_patient_info", methods=["POST"])
def update_patient_info():
    """Update patient information for an existing conversation"""
    data = request.json or {}
    conversation_id = data.get("conversation_id")
    
    if not conversation_id:
        return jsonify({"error": "No conversation ID provided"}), 400
    
    conversation = active_conversations.get(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    # Update patient info
    age = data.get("age")
    gender = data.get("gender")
    patient_name = data.get("patient_name", "").strip()
    
    conversation["patient_info"].update({
        "age": age,
        "gender": gender,
        "patient_name": patient_name
    })
    
    # Update session in database
    update_session_patient_info(
        conversation["session_id"],
        age=(int(age) if age and str(age).isdigit() else None),
        gender=(gender or None),
        patient_name=(patient_name or None)
    )
    
    return jsonify({"success": True, "message": "Patient information updated"})

@app.route("/api/conversation/<conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    """Get conversation history"""
    conversation = active_conversations.get(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    return jsonify({
        "conversation_id": conversation_id,
        "session_id": conversation["session_id"],
        "patient_info": conversation["patient_info"],
        "message_history": conversation["message_history"],
        "created_at": conversation["created_at"].isoformat()
    })

@app.route("/api/end_conversation", methods=["POST"])
def end_conversation():
    """End a conversation and close the session"""
    data = request.json or {}
    conversation_id = data.get("conversation_id")
    
    if not conversation_id:
        return jsonify({"error": "No conversation ID provided"}), 400
    
    conversation = active_conversations.get(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    # Close the session in database
    close_session(conversation["session_id"])
    
    # Remove from active conversations
    del active_conversations[conversation_id]
    
    return jsonify({"success": True, "message": "Conversation ended"})

@app.route("/check", methods=["POST"])
def check():
    """Legacy endpoint for single symptom check (for backward compatibility)"""
    data = request.json or {}
    age = data.get("age")
    gender = data.get("gender")
    patient_name = (data.get("patient_name","") or "").strip()
    symptoms = (data.get("symptoms","") or "").strip()
    use_api = data.get("use_api", "mock")

    if not symptoms:
        return jsonify({"error":"Please enter symptoms."}), 400

    # create session and log user message
    session_id = create_session(
        start_time=datetime.utcnow(),
        age=(int(age) if age and str(age).isdigit() else None),
        gender=(gender or None),
        patient_name=(patient_name or None)
    )
    if patient_name:
        log_message(session_id, "meta", f"patient_name:{patient_name}")
    log_message(session_id, "user", symptoms)

    # quick red-flag handling
    if has_red_flag(symptoms):
        logger.info(f"Red flag detected for session {session_id}")
        result = {
            "triage": "🚨 Emergency — seek immediate care",
            "conditions": [{"name": "Potential emergency condition", "probability": 0.8}],
            "advice": "Symptoms indicate possible emergency. Call emergency services or go to nearest ER immediately.",
            "selfcare": ["Do not delay - go to emergency department"],
            "warning": [
                "Severe chest pain or pressure",
                "Difficulty breathing or shortness of breath", 
                "Loss of consciousness or sudden confusion"
            ],
            "summary": "Immediate emergency care is recommended based on the symptoms you provided.",
            "patient_name": patient_name,
            "red_flag": True
        }
        log_result(session_id, "redflag", result)
        log_message(session_id, "bot", result["advice"])
        close_session(session_id)
        return jsonify({"session_id": session_id, "result": result})

    # Call chosen API
    logger.info(f"Calling API: {use_api} for session {session_id}")
    
    if use_api == "deepseek" and DEEPSEEK_API_AVAILABLE:
        result = call_deepseek(symptoms, age=age, gender=gender)
        api_name = "deepseek"
    else:
        result = call_symptom_api_mock(symptoms, age=age, gender=gender)
        api_name = "mock"

    # Ensure all required keys exist
    required_keys = ["triage", "conditions", "advice", "selfcare", "warning", "summary"]
    for key in required_keys:
        result.setdefault(key, "")
        
    if not result.get("selfcare"):
        result["selfcare"] = ["Stay hydrated and rest."]
    if not result.get("warning"):
        result["warning"] = ["Seek medical help if symptoms worsen."]
    if not result.get("summary"):
        top_condition = result.get("conditions", [{}])[0].get("name") if result.get("conditions") else None
        if top_condition:
            result["summary"] = f"Most likely: {top_condition}. {result.get('advice', 'Follow up with a physician if unsure.')}"
        else:
            result["summary"] = "Please consult with a healthcare provider for proper diagnosis."
            
    result["patient_name"] = patient_name

    # Log and finish
    log_result(session_id, api_name, result)
    log_message(session_id, "bot", result.get("advice",""))
    close_session(session_id)

    logger.info(f"Session {session_id} completed successfully")
    return jsonify({"session_id": session_id, "result": result})

@app.route("/history", methods=["GET"])
def history():
    try:
        rows = get_sessions(100)
        sessions = []
        for r in rows:
            sessions.append({
                "id": r[0],
                "session_hash": r[1],
                "start_time": r[2],
                "age": r[3],
                "gender": r[4],
                "patient_name": r[5] if len(r) > 5 else None
            })
        return render_template("history.html", sessions=sessions)
    except Exception as e:
        logger.error(f"Error loading history: {e}")
        return render_template("history.html", sessions=[])

@app.route("/history/<int:session_id>", methods=["GET"])
def view_session(session_id):
    try:
        messages = get_messages_for_session(session_id)
        results = get_results_for_session(session_id)
        return render_template("session_view.html", session_id=session_id, messages=messages, results=results)
    except Exception as e:
        logger.error(f"Error viewing session {session_id}: {e}")
        return render_template("session_view.html", session_id=session_id, messages=[], results=[])

@app.route("/conversation/<int:session_id>", methods=["GET"])
def view_conversation(session_id):
    """View full conversation for a session"""
    try:
        conversation = get_conversation_history(session_id)
        return render_template("conversation_view.html", 
                             session_id=session_id, 
                             conversation=conversation)
    except Exception as e:
        logger.error(f"Error viewing conversation {session_id}: {e}")
        return render_template("conversation_view.html", 
                             session_id=session_id, 
                             conversation=[])

# Health check endpoints
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "deepseek_api_available": DEEPSEEK_API_AVAILABLE,
        "active_conversations": len(active_conversations)
    })

@app.route("/debug/api-status", methods=["GET"])
def api_status():
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    return jsonify({
        "deepseek_api_key_set": bool(deepseek_key),
        "deepseek_key_length": len(deepseek_key) if deepseek_key else 0,
        "deepseek_api_available": DEEPSEEK_API_AVAILABLE,
        "environment_loaded": True,
        "active_conversations": len(active_conversations)
    })

# Clean up old conversations (basic implementation)
def cleanup_old_conversations():
    """Remove conversations older than 24 hours"""
    current_time = datetime.utcnow()
    expired_conversations = []
    
    for conv_id, conv_data in active_conversations.items():
        if (current_time - conv_data["created_at"]).total_seconds() > 24 * 3600:  # 24 hours
            expired_conversations.append(conv_id)
    
    for conv_id in expired_conversations:
        close_session(active_conversations[conv_id]["session_id"])
        del active_conversations[conv_id]
    
    if expired_conversations:
        logger.info(f"Cleaned up {len(expired_conversations)} expired conversations")

if __name__ == "__main__":
    # Clean up on startup
    cleanup_old_conversations()
>>>>>>> c90d239 (Initial commit)
    app.run(debug=True, host="0.0.0.0", port=5000)