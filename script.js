// static/script.js - Chatbot Version
document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const chatMessages = document.getElementById("chatMessages");
  const chatInput = document.getElementById("chatInput");
  const sendButton = document.getElementById("sendButton");
  const typingIndicator = document.getElementById("typingIndicator");
  const analysisResults = document.getElementById("analysisResults");
  const loadingOverlay = document.getElementById("loadingOverlay");
  const toast = document.getElementById("toast");
  const apiStatusAlert = document.getElementById("apiStatusAlert");
  const quickSymptoms = document.querySelectorAll(".symptom-chip");

  // State
  let currentSessionId = null;
  let isAnalyzing = false;

  // Initialize
  checkApiStatus();
  setupEventListeners();

  function checkApiStatus() {
    fetch('/debug/api-status')
      .then(response => response.json())
      .then(data => {
        const apiSelector = document.getElementById('use_api');
        const deepseekOption = apiSelector ? apiSelector.querySelector('option[value="deepseek"]') : null;
        
        if (!data.deepseek_api_available) {
          if (apiStatusAlert) {
            apiStatusAlert.classList.remove("hidden");
          }
          
          if (deepseekOption) {
            deepseekOption.disabled = true;
            deepseekOption.textContent = 'DeepSeek Medical AI (Currently Unavailable)';
          }
        }
      })
      .catch(error => {
        console.error('Error checking API status:', error);
        if (apiStatusAlert) {
          apiStatusAlert.classList.remove("hidden");
          apiStatusAlert.innerHTML = '<strong>Note:</strong> Unable to verify API status. Using mock data for demonstration.';
        }
      });
  }

  function setupEventListeners() {
    // Send message on button click
    sendButton.addEventListener("click", sendMessage);
    
    // Send message on Enter key (but allow Shift+Enter for new line)
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
    
    // Enable/disable send button based on input
    chatInput.addEventListener("input", () => {
      sendButton.disabled = chatInput.value.trim().length === 0;
    });
    
    // Auto-resize textarea
    chatInput.addEventListener("input", autoResizeTextarea);
    
    // Quick symptom buttons
    quickSymptoms.forEach(chip => {
      chip.addEventListener("click", () => {
        const symptom = chip.getAttribute("data-symptom");
        chatInput.value = `I have ${symptom}`;
        sendButton.disabled = false;
        chatInput.focus();
        autoResizeTextarea();
      });
    });
  }

  function autoResizeTextarea() {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
  }

  function sendMessage() {
    const message = chatInput.value.trim();
    if (!message || isAnalyzing) return;

    // Add user message to chat
    addMessage("user", message);
    chatInput.value = "";
    sendButton.disabled = true;
    autoResizeTextarea();
    
    // Show typing indicator
    showTypingIndicator();
    
    // Get patient info
    const age = document.getElementById("age").value;
    const gender = document.getElementById("gender").value;
    const patient_name = document.getElementById("patient_name").value.trim();
    
    // Analyze the message
    analyzeMessage(message, age, gender, patient_name);
  }

  function analyzeMessage(message, age, gender, patient_name) {
    isAnalyzing = true;
    
    // Determine if this is a medical query
    const medicalKeywords = [
      'pain', 'hurt', 'sick', 'fever', 'cough', 'headache', 'nausea', 
      'vomit', 'dizzy', 'rash', 'swollen', 'bleed', 'breath', 'chest',
      'stomach', 'throat', 'cold', 'flu', 'symptom', 'feel'
    ];
    
    const isMedicalQuery = medicalKeywords.some(keyword => 
      message.toLowerCase().includes(keyword)
    );

    if (!isMedicalQuery) {
      // General conversation
      setTimeout(() => {
        hideTypingIndicator();
        const responses = [
          "I'm here to help with medical concerns. Could you describe any symptoms you're experiencing?",
          "I specialize in symptom assessment. Please tell me about any health issues you're having.",
          "For medical assistance, please describe your symptoms and I'll do my best to help."
        ];
        const response = responses[Math.floor(Math.random() * responses.length)];
        addMessage("bot", response);
        isAnalyzing = false;
      }, 1000);
      return;
    }

    // Medical query - proceed with analysis
    showLoading(true);

    fetch("/check", {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: JSON.stringify({ 
        age: age || null, 
        gender: gender || null, 
        symptoms: message, 
        use_api: "mock", // Force mock for now due to API issues
        patient_name: patient_name || null 
      })
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      return response.json();
    })
    .then(result => {
      hideTypingIndicator();
      showLoading(false);
      
      if (result.error) {
        addMessage("bot", `I encountered an error: ${result.error}`);
        return;
      }

      // Store session ID for follow-up questions
      currentSessionId = result.session_id;
      
      // Add bot response with analysis
      const analysis = result.result;
      addMessage("bot", analysis.advice || "I've analyzed your symptoms.");
      
      // Show detailed analysis results
      displayAnalysisResults(analysis);
      
      // Add follow-up suggestion
      setTimeout(() => {
        addMessage("bot", "Is there anything else you'd like to know about your symptoms or would you like to describe additional symptoms?");
      }, 500);
      
    })
    .catch(error => {
      hideTypingIndicator();
      showLoading(false);
      console.error("Analysis error:", error);
      addMessage("bot", "I'm sorry, I encountered an error while analyzing your symptoms. Please try again.");
      showToast("Analysis failed: " + error.message, "error");
    })
    .finally(() => {
      isAnalyzing = false;
    });
  }

  function addMessage(sender, text) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${sender}-message`;
    
    const time = new Date().toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
    
    messageDiv.innerHTML = `
      <div>${text}</div>
      <div class="message-time">${time}</div>
    `;
    
    chatMessages.appendChild(messageDiv);
    
    // Remove welcome message if it's the first user message
    const welcomeMessage = chatMessages.querySelector(".welcome-message");
    if (welcomeMessage && sender === "user") {
      welcomeMessage.remove();
    }
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function showTypingIndicator() {
    typingIndicator.style.display = "block";
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function hideTypingIndicator() {
    typingIndicator.style.display = "none";
  }

  function displayAnalysisResults(analysis) {
    const resultsHTML = `
      <div class="card triage-card ${getTriageClass(analysis.triage)}">
        <div class="triage-header">
          <h2>Assessment Result</h2>
          <div class="triage-badge">${analysis.triage || 'Not specified'}</div>
        </div>
        <p class="triage-description">${analysis.advice || 'No specific advice available.'}</p>
      </div>

      <div class="card">
        <div class="card-header">
          <h3>Possible Conditions</h3>
          <small class="muted">Based on your symptoms</small>
        </div>
        <div class="conditions">
          ${renderConditions(analysis.conditions)}
        </div>
      </div>

      <div class="card two-col">
        <div class="selfcare-section">
          <div class="section-header">
            <h3>Self-Care Recommendations</h3>
          </div>
          <ul class="collapsible">
            ${renderListItems(analysis.selfcare, 'No specific self-care recommendations.')}
          </ul>
        </div>
        <div class="warning-section">
          <div class="section-header">
            <h3>⚠️ Warning Signs</h3>
          </div>
          <ul class="collapsible danger">
            ${renderListItems(analysis.warning, 'No specific warning signs listed.')}
          </ul>
        </div>
      </div>

      <div class="card">
        <h3>Summary</h3>
        <p class="summary">${analysis.summary || 'No summary available.'}</p>
      </div>
    `;
    
    analysisResults.innerHTML = resultsHTML;
    analysisResults.classList.remove("hidden");
    
    // Scroll to results
    analysisResults.scrollIntoView({ behavior: "smooth" });
  }

  function getTriageClass(triage) {
    if (!triage) return 'triage-routine';
    
    const triageLower = triage.toLowerCase();
    if (triageLower.includes('emergency') || triageLower.includes('urgent') || triageLower.includes('immediate')) {
      return 'triage-emergency';
    } else if (triageLower.includes('gp') || triageLower.includes('doctor') || triageLower.includes('within')) {
      return 'triage-urgent';
    } else {
      return 'triage-routine';
    }
  }

  function renderConditions(conditions) {
    if (!conditions || conditions.length === 0) {
      return '<p class="muted">No specific conditions identified.</p>';
    }
    
    return conditions.map(condition => {
      const probability = Math.round((condition.probability || 0) * 100);
      return `
        <div class="condition-item">
          <div class="condition-name">${condition.name}</div>
          <div class="condition-probability">
            <div class="probability-bar">
              <div class="probability-fill" style="width: ${probability}%"></div>
            </div>
            <span class="probability-text">${probability}%</span>
          </div>
        </div>
      `;
    }).join('');
  }

  function renderListItems(items, fallback) {
    if (!items || items.length === 0) {
      return `<li class="muted">${fallback}</li>`;
    }
    
    return items.map(item => `<li>${item}</li>`).join('');
  }

  function showLoading(on = true) {
    if (loadingOverlay) {
      loadingOverlay.classList.toggle("hidden", !on);
    }
  }

  function showToast(msg, type = "info", duration = 3500) {
    if (!toast) return;
    
    toast.textContent = msg;
    toast.className = `toast ${type}`;
    toast.classList.remove("hidden");
    
    setTimeout(() => {
      toast.classList.add("hidden");
    }, duration);
  }

  // Make functions available globally for any future enhancements
  window.addMessage = addMessage;
  window.sendMessage = sendMessage;
});