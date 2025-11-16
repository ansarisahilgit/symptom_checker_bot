# test_fix.py
try:
    from symptom_api import call_deepseek, call_symptom_api_mock, has_red_flag
    print("✅ All imports successful!")
    
    # Test mock function
    result = call_symptom_api_mock("fever and cough")
    print("✅ Mock function works:", result["triage"])
    
    # Test deepseek function (will use mock due to API issues)
    result2 = call_deepseek("headache")
    print("✅ DeepSeek function works:", result2["triage"])
    
except ImportError as e:
    print("❌ Import error:", e)
except Exception as e:
    print("❌ Other error:", e)