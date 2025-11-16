<<<<<<< HEAD
# symptom_api.py
import os
import requests
import json
from datetime import datetime

RED_FLAGS = [
    "chest pain",
    "difficulty breathing",
    "loss of consciousness",
    "severe bleeding", 
    "sudden numbness",
    "severe headache",
    "shortness of breath",
    "persistent vomiting"
]

def has_red_flag(symptoms_text):
    s = (symptoms_text or "").lower()
    return any(flag in s for flag in RED_FLAGS)

def call_symptom_api_mock(symptoms_text, age=None, gender=None):
    s = (symptoms_text or "").lower()
    
    # Enhanced mock responses for better chatbot interaction
    if "chest pain" in s and ("breath" in s or "dizzy" in s):
        return {
            "triage": "🚨 Emergency — seek immediate care",
            "conditions": [
                {"name": "Possible heart attack or cardiac issue", "probability": 0.75},
                {"name": "Severe anxiety or panic attack", "probability": 0.15},
                {"name": "Pulmonary embolism", "probability": 0.10}
            ],
            "advice": "This could be a medical emergency. Call emergency services immediately. Do not drive yourself.",
            "selfcare": ["Sit down and try to stay calm", "Chew aspirin if available and not allergic", "Loosen tight clothing"],
            "warning": ["Chest pressure or pain", "Pain spreading to arm/jaw", "Difficulty breathing", "Nausea or dizziness"],
            "summary": "Chest pain with breathing difficulties requires immediate emergency evaluation."
        }
    elif "fever" in s and "cough" in s and "sore throat" in s:
        return {
            "triage": "See GP within 24-48 hours",
            "conditions": [
                {"name": "Viral upper respiratory infection", "probability": 0.65},
                {"name": "Influenza (flu)", "probability": 0.25},
                {"name": "Strep throat", "probability": 0.10}
            ],
            "advice": "Rest, stay hydrated, use throat lozenges. Monitor temperature. Consider seeing a doctor if symptoms worsen.",
            "selfcare": ["Drink warm tea with honey", "Gargle salt water", "Use humidifier", "Rest adequately"],
            "warning": ["Fever over 102°F", "Difficulty swallowing", "Rash develops", "Symptoms worsen after 3 days"],
            "summary": "Symptoms suggest common respiratory infection; see doctor if no improvement in 3 days."
        }
    elif "fever" in s and "cough" in s:
        return {
            "triage": "See GP within 24–48 hours; urgent if breathing worsens",
            "conditions": [
                {"name": "Common cold / viral upper respiratory infection", "probability": 0.55},
                {"name": "Influenza (flu)", "probability": 0.30},
                {"name": "Acute bronchitis", "probability": 0.10}
            ],
            "advice": "Rest, stay hydrated; consider paracetamol for fever. Monitor breathing closely.",
            "selfcare": ["Drink warm fluids and rest.", "Take paracetamol for fever (follow dosing).", "Gargle warm salt water."],
            "warning": ["Difficulty breathing", "High fever >3 days", "Bluish lips or chest pain"],
            "summary": "Your symptoms suggest a viral respiratory infection; monitor breathing closely and see GP if worsening."
        }
    elif "headache" in s and "stiff neck" in s:
        return {
            "triage": "See doctor immediately",
            "conditions": [{"name":"Meningitis (possible)","probability":0.45},{"name":"Migraine","probability":0.35}],
            "advice": "Seek immediate medical attention; this could be serious.",
            "selfcare": ["Avoid bright lights", "Do not delay medical evaluation"],
            "warning": ["High fever with neck stiffness", "Seizures or loss of consciousness"],
            "summary": "Severe headache with neck stiffness can indicate a serious condition. Please seek urgent care."
        }
    elif "rash" in s and "fever" in s:
        return {
            "triage": "See GP within 24 hours",
            "conditions": [
                {"name": "Viral exanthem", "probability": 0.50},
                {"name": "Allergic reaction", "probability": 0.30},
                {"name": "Bacterial infection", "probability": 0.15}
            ],
            "advice": "Avoid scratching, monitor for spreading. Identify potential allergens.",
            "selfcare": ["Apply cool compresses", "Use calamine lotion", "Avoid new soaps/detergents"],
            "warning": ["Rash spreads rapidly", "Difficulty breathing", "Swelling of face/tongue"],
            "summary": "Rash with fever could be viral or allergic; medical evaluation recommended."
        }
    elif "stomach pain" in s and "vomiting" in s:
        return {
            "triage": "See GP within 24 hours",
            "conditions": [
                {"name": "Gastroenteritis", "probability": 0.60},
                {"name": "Food poisoning", "probability": 0.25},
                {"name": "Indigestion", "probability": 0.10}
            ],
            "advice": "Rest, clear fluids only for 24 hours, then bland diet.",
            "selfcare": ["Sip clear fluids", "BRAT diet (bananas, rice, applesauce, toast)", "Rest"],
            "warning": ["Severe abdominal pain", "Blood in vomit/stool", "Dehydration signs"],
            "summary": "Likely stomach bug or food poisoning; seek care if symptoms worsen or persist."
        }
    elif "back pain" in s and "fever" in s:
        return {
            "triage": "See GP within 24 hours",
            "conditions": [
                {"name": "Kidney infection", "probability": 0.40},
                {"name": "Muscular strain", "probability": 0.35},
                {"name": "Urinary tract infection", "probability": 0.20}
            ],
            "advice": "Drink plenty of fluids and rest. See doctor for proper diagnosis.",
            "selfcare": ["Apply heat pad", "Stay hydrated", "Gentle stretching if muscular"],
            "warning": ["High fever", "Pain spreading", "Difficulty urinating"],
            "summary": "Back pain with fever could indicate infection; medical evaluation recommended."
        }
    else:
        return {
            "triage": "Self-care / monitor",
            "conditions": [
                {"name":"Allergic rhinitis or mild viral illness","probability":0.45},
                {"name":"Indigestion","probability":0.20},
                {"name":"Stress-related symptoms","probability":0.15}
            ],
            "advice": "Monitor symptoms; use OTC medicines as needed. Consult doctor if symptoms persist.",
            "selfcare": ["Rest and stay hydrated.", "Avoid allergens.", "Practice stress reduction techniques."],
            "warning": ["High or prolonged fever", "Severe dehydration", "Symptoms worsen after 3 days"],
            "summary": "Symptoms likely mild and manageable at home; seek care if they worsen."
        }

def call_deepseek(symptoms_text, age=None, gender=None):
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
    
    if not API_KEY:
        print("❌ DEEPSEEK_API_KEY not found in environment")
        return call_symptom_api_mock(symptoms_text, age, gender)
    
    print(f"🔑 API Key found: {API_KEY[:8]}...")
    
    url = "https://api.deepseek.com/chat/completions"
    
    prompt = f"""Analyze these symptoms and provide medical triage advice in JSON format only:

SYMPTOMS: {symptoms_text}
AGE: {age or 'Not specified'}
GENDER: {gender or 'Not specified'}

Return ONLY valid JSON with this exact structure:
{{
  "triage": "string (e.g., 'Self-care', 'See GP within 24-48 hours', 'Emergency care needed')",
  "conditions": [{{"name": "condition name", "probability": 0.0}}],
  "advice": "string with general advice", 
  "selfcare": ["tip 1", "tip 2"],
  "warning": ["warning sign 1", "warning sign 2"],
  "summary": "string with brief summary"
}}

Be conservative and recommend medical care when uncertain."""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a medical triage assistant. Provide responses in valid JSON format only, no additional text."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 800,
        "stream": False
    }

    try:
        print(f"🔍 Calling DeepSeek API with symptoms: {symptoms_text[:50]}...")
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        print(f"📡 Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ API Error {response.status_code}: {response.text}")
            return call_symptom_api_mock(symptoms_text, age, gender)
        
        data = response.json()
        print("✅ Received API response")
        
        # Extract the response content
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"]
            print(f"📝 Raw response: {content[:200]}...")
            
            # Try to parse JSON from the response
            try:
                # Clean the response - remove markdown code blocks if present
                content_clean = content.replace('```json', '').replace('```', '').strip()
                parsed = json.loads(content_clean)
                
                # Validate required fields
                required_fields = ["triage", "conditions", "advice", "selfcare", "warning", "summary"]
                if all(field in parsed for field in required_fields):
                    print("✅ Successfully parsed JSON response")
                    return parsed
                else:
                    print("❌ Missing required fields in API response")
                    missing = [field for field in required_fields if field not in parsed]
                    print(f"Missing fields: {missing}")
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse error: {e}")
                print(f"Trying to extract JSON from response...")
                
                # Try to find JSON in the text
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    json_str = content[start:end+1]
                    try:
                        parsed = json.loads(json_str)
                        if "triage" in parsed:
                            print("✅ Extracted JSON from text response")
                            return parsed
                    except:
                        pass
                
                print("❌ Could not parse JSON from response")
                
        print("❌ Invalid response format from API")
        return call_symptom_api_mock(symptoms_text, age, gender)
        
    except requests.exceptions.Timeout:
        print("❌ API request timed out")
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - check internet connection")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    # Fallback to mock data
=======
# symptom_api.py
import os
import requests
import json
from datetime import datetime

RED_FLAGS = [
    "chest pain",
    "difficulty breathing",
    "loss of consciousness",
    "severe bleeding", 
    "sudden numbness",
    "severe headache",
    "shortness of breath",
    "persistent vomiting"
]

def has_red_flag(symptoms_text):
    s = (symptoms_text or "").lower()
    return any(flag in s for flag in RED_FLAGS)

def call_symptom_api_mock(symptoms_text, age=None, gender=None):
    s = (symptoms_text or "").lower()
    
    # Enhanced mock responses for better chatbot interaction
    if "chest pain" in s and ("breath" in s or "dizzy" in s):
        return {
            "triage": "🚨 Emergency — seek immediate care",
            "conditions": [
                {"name": "Possible heart attack or cardiac issue", "probability": 0.75},
                {"name": "Severe anxiety or panic attack", "probability": 0.15},
                {"name": "Pulmonary embolism", "probability": 0.10}
            ],
            "advice": "This could be a medical emergency. Call emergency services immediately. Do not drive yourself.",
            "selfcare": ["Sit down and try to stay calm", "Chew aspirin if available and not allergic", "Loosen tight clothing"],
            "warning": ["Chest pressure or pain", "Pain spreading to arm/jaw", "Difficulty breathing", "Nausea or dizziness"],
            "summary": "Chest pain with breathing difficulties requires immediate emergency evaluation."
        }
    elif "fever" in s and "cough" in s and "sore throat" in s:
        return {
            "triage": "See GP within 24-48 hours",
            "conditions": [
                {"name": "Viral upper respiratory infection", "probability": 0.65},
                {"name": "Influenza (flu)", "probability": 0.25},
                {"name": "Strep throat", "probability": 0.10}
            ],
            "advice": "Rest, stay hydrated, use throat lozenges. Monitor temperature. Consider seeing a doctor if symptoms worsen.",
            "selfcare": ["Drink warm tea with honey", "Gargle salt water", "Use humidifier", "Rest adequately"],
            "warning": ["Fever over 102°F", "Difficulty swallowing", "Rash develops", "Symptoms worsen after 3 days"],
            "summary": "Symptoms suggest common respiratory infection; see doctor if no improvement in 3 days."
        }
    elif "fever" in s and "cough" in s:
        return {
            "triage": "See GP within 24–48 hours; urgent if breathing worsens",
            "conditions": [
                {"name": "Common cold / viral upper respiratory infection", "probability": 0.55},
                {"name": "Influenza (flu)", "probability": 0.30},
                {"name": "Acute bronchitis", "probability": 0.10}
            ],
            "advice": "Rest, stay hydrated; consider paracetamol for fever. Monitor breathing closely.",
            "selfcare": ["Drink warm fluids and rest.", "Take paracetamol for fever (follow dosing).", "Gargle warm salt water."],
            "warning": ["Difficulty breathing", "High fever >3 days", "Bluish lips or chest pain"],
            "summary": "Your symptoms suggest a viral respiratory infection; monitor breathing closely and see GP if worsening."
        }
    elif "headache" in s and "stiff neck" in s:
        return {
            "triage": "See doctor immediately",
            "conditions": [{"name":"Meningitis (possible)","probability":0.45},{"name":"Migraine","probability":0.35}],
            "advice": "Seek immediate medical attention; this could be serious.",
            "selfcare": ["Avoid bright lights", "Do not delay medical evaluation"],
            "warning": ["High fever with neck stiffness", "Seizures or loss of consciousness"],
            "summary": "Severe headache with neck stiffness can indicate a serious condition. Please seek urgent care."
        }
    elif "rash" in s and "fever" in s:
        return {
            "triage": "See GP within 24 hours",
            "conditions": [
                {"name": "Viral exanthem", "probability": 0.50},
                {"name": "Allergic reaction", "probability": 0.30},
                {"name": "Bacterial infection", "probability": 0.15}
            ],
            "advice": "Avoid scratching, monitor for spreading. Identify potential allergens.",
            "selfcare": ["Apply cool compresses", "Use calamine lotion", "Avoid new soaps/detergents"],
            "warning": ["Rash spreads rapidly", "Difficulty breathing", "Swelling of face/tongue"],
            "summary": "Rash with fever could be viral or allergic; medical evaluation recommended."
        }
    elif "stomach pain" in s and "vomiting" in s:
        return {
            "triage": "See GP within 24 hours",
            "conditions": [
                {"name": "Gastroenteritis", "probability": 0.60},
                {"name": "Food poisoning", "probability": 0.25},
                {"name": "Indigestion", "probability": 0.10}
            ],
            "advice": "Rest, clear fluids only for 24 hours, then bland diet.",
            "selfcare": ["Sip clear fluids", "BRAT diet (bananas, rice, applesauce, toast)", "Rest"],
            "warning": ["Severe abdominal pain", "Blood in vomit/stool", "Dehydration signs"],
            "summary": "Likely stomach bug or food poisoning; seek care if symptoms worsen or persist."
        }
    elif "back pain" in s and "fever" in s:
        return {
            "triage": "See GP within 24 hours",
            "conditions": [
                {"name": "Kidney infection", "probability": 0.40},
                {"name": "Muscular strain", "probability": 0.35},
                {"name": "Urinary tract infection", "probability": 0.20}
            ],
            "advice": "Drink plenty of fluids and rest. See doctor for proper diagnosis.",
            "selfcare": ["Apply heat pad", "Stay hydrated", "Gentle stretching if muscular"],
            "warning": ["High fever", "Pain spreading", "Difficulty urinating"],
            "summary": "Back pain with fever could indicate infection; medical evaluation recommended."
        }
    else:
        return {
            "triage": "Self-care / monitor",
            "conditions": [
                {"name":"Allergic rhinitis or mild viral illness","probability":0.45},
                {"name":"Indigestion","probability":0.20},
                {"name":"Stress-related symptoms","probability":0.15}
            ],
            "advice": "Monitor symptoms; use OTC medicines as needed. Consult doctor if symptoms persist.",
            "selfcare": ["Rest and stay hydrated.", "Avoid allergens.", "Practice stress reduction techniques."],
            "warning": ["High or prolonged fever", "Severe dehydration", "Symptoms worsen after 3 days"],
            "summary": "Symptoms likely mild and manageable at home; seek care if they worsen."
        }

def call_deepseek(symptoms_text, age=None, gender=None):
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
    
    if not API_KEY:
        print("❌ DEEPSEEK_API_KEY not found in environment")
        return call_symptom_api_mock(symptoms_text, age, gender)
    
    print(f"🔑 API Key found: {API_KEY[:8]}...")
    
    url = "https://api.deepseek.com/chat/completions"
    
    prompt = f"""Analyze these symptoms and provide medical triage advice in JSON format only:

SYMPTOMS: {symptoms_text}
AGE: {age or 'Not specified'}
GENDER: {gender or 'Not specified'}

Return ONLY valid JSON with this exact structure:
{{
  "triage": "string (e.g., 'Self-care', 'See GP within 24-48 hours', 'Emergency care needed')",
  "conditions": [{{"name": "condition name", "probability": 0.0}}],
  "advice": "string with general advice", 
  "selfcare": ["tip 1", "tip 2"],
  "warning": ["warning sign 1", "warning sign 2"],
  "summary": "string with brief summary"
}}

Be conservative and recommend medical care when uncertain."""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a medical triage assistant. Provide responses in valid JSON format only, no additional text."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 800,
        "stream": False
    }

    try:
        print(f"🔍 Calling DeepSeek API with symptoms: {symptoms_text[:50]}...")
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        print(f"📡 Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ API Error {response.status_code}: {response.text}")
            return call_symptom_api_mock(symptoms_text, age, gender)
        
        data = response.json()
        print("✅ Received API response")
        
        # Extract the response content
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"]
            print(f"📝 Raw response: {content[:200]}...")
            
            # Try to parse JSON from the response
            try:
                # Clean the response - remove markdown code blocks if present
                content_clean = content.replace('```json', '').replace('```', '').strip()
                parsed = json.loads(content_clean)
                
                # Validate required fields
                required_fields = ["triage", "conditions", "advice", "selfcare", "warning", "summary"]
                if all(field in parsed for field in required_fields):
                    print("✅ Successfully parsed JSON response")
                    return parsed
                else:
                    print("❌ Missing required fields in API response")
                    missing = [field for field in required_fields if field not in parsed]
                    print(f"Missing fields: {missing}")
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse error: {e}")
                print(f"Trying to extract JSON from response...")
                
                # Try to find JSON in the text
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    json_str = content[start:end+1]
                    try:
                        parsed = json.loads(json_str)
                        if "triage" in parsed:
                            print("✅ Extracted JSON from text response")
                            return parsed
                    except:
                        pass
                
                print("❌ Could not parse JSON from response")
                
        print("❌ Invalid response format from API")
        return call_symptom_api_mock(symptoms_text, age, gender)
        
    except requests.exceptions.Timeout:
        print("❌ API request timed out")
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - check internet connection")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    # Fallback to mock data
>>>>>>> c90d239 (Initial commit)
    return call_symptom_api_mock(symptoms_text, age, gender)