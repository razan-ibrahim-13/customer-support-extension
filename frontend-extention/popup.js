// Global state
let currentDomain = '';
let knowledgeBase = {};
let isAnalyzing = false;

// Initialize extension
document.addEventListener('DOMContentLoaded', async () => {
  await initializeExtension();
});

document.querySelectorAll('.suggestion-btn').forEach(button => {
  button.addEventListener('click', (event) => {
    const question = event.target.getAttribute('data-question');
    if (question) {
      askQuestion(question);
    }
  });
});

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('userInput').addEventListener('keypress', handleKeyPress);
  document.querySelectorAll('.suggestion-btn').forEach(button => {
    button.addEventListener('click', (event) => {
      const question = event.target.getAttribute('data-question');
      if (question) {
        askQuestion(question);
      }
    });
});
});

async function initializeExtension() {
  try {
    // Get current tab information
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    currentDomain = new URL(tab.url).hostname;
    
    // Update status
    updateStatus(`📍 Analyzing ${currentDomain}...`);
    
    // Start documentation analysis
    await analyzeWebsite(tab.url);
    
  } catch (error) {
    console.error('Initialization error:', error);
    updateStatus('❌ Error initializing assistant');
  }
}

async function analyzeWebsite(url) {
  isAnalyzing = true;
  
  try {
    // Send message to content script to start analysis
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    chrome.tabs.sendMessage(tab.id, {
      action: 'analyzeWebsite',
      url: url
    }, (response) => {
      if (response && response.success) {
        knowledgeBase = response.data;
        updateStatus(`✅ Found ${Object.keys(knowledgeBase).length} support sections`);
        isAnalyzing = false;
      } else {
        updateStatus('⚠️ Limited documentation found');
        isAnalyzing = false;
      }
    });
    
  } catch (error) {
    console.error('Analysis error:', error);
    updateStatus('❌ Analysis failed');
    isAnalyzing = false;
  }
}

function updateStatus(message) {
  document.getElementById('status').innerHTML = `<div>${message}</div>`;
}

function askQuestion(question) {
  document.getElementById('userInput').value = question;
  handleUserInput();
}

function handleKeyPress(event) {
  if (event.key === 'Enter') {
    handleUserInput();
  }
}

async function handleUserInput() {
  const input = document.getElementById('userInput');
  const question = input.value.trim();
  
  if (!question) return;
  
  // Clear input
  input.value = '';
  
  // Add user message to chat
  addMessage(question, 'user');
  
  // Show loading
  document.getElementById('loading').style.display = 'block';
  
  try {
    // Process the question
    const answer = await processQuestion(question);
    addMessage(answer, 'bot');
  } catch (error) {
    addMessage('Sorry, I encountered an error processing your question. Please try again.', 'bot');
  }
  
  // Hide loading
  document.getElementById('loading').style.display = 'none';
}

async function processQuestion(question) {
  // Simple keyword matching for now (we'll enhance this later)
  const keywords = {
    cancel: ['cancel', 'cancellation', 'unsubscribe', 'stop'],
    refund: ['refund', 'money back', 'return', 'reimburse'],
    contact: ['contact', 'support', 'help', 'phone', 'email'],
    billing: ['billing', 'payment', 'charge', 'invoice', 'cost']
  };
  
  const questionLower = question.toLowerCase();
  let category = 'general';
  
  // Determine question category
  for (const [cat, words] of Object.entries(keywords)) {
    if (words.some(word => questionLower.includes(word))) {
      category = cat;
      break;
    }
  }
  
  // Generate response based on category and knowledge base
  return generateResponse(category, question);
}

function generateResponse(category, question) {
  const responses = {
    cancel: `Based on the website's documentation, here are the typical cancellation steps:
    
1. Log into your account
2. Go to Account Settings or Billing section
3. Look for "Cancel Subscription" or similar option
4. Follow the cancellation process

*Note: This is general guidance. Please check the specific cancellation policy on this website for exact steps.*

Would you like me to help you find the exact cancellation page?`,

    refund: `Regarding refunds, most websites have these common policies:

- **Digital products**: Usually 30-day money-back guarantee
- **Physical items**: Typically 30-60 days from delivery
- **Subscriptions**: Pro-rated refunds may apply

To request a refund:
1. Contact customer support
2. Provide your order/transaction number
3. Explain the reason for the refund request

*Please check this website's specific refund policy for exact terms and conditions.*`,

    contact: `Here are common ways to contact support:

📧 **Email**: Look for support@${currentDomain} or help@${currentDomain}
📞 **Phone**: Check the footer or contact page for phone numbers
💬 **Live Chat**: Many sites have chat widgets (usually bottom-right corner)
📝 **Contact Form**: Usually found in Help or Contact sections

I can help you locate the specific contact information for this website.`,

    billing: `For billing questions, you typically need to:

1. **Check your account**: Log in and go to billing/payment section
2. **Review invoices**: Look for transaction history or receipts
3. **Update payment info**: Modify cards or payment methods
4. **Contact billing support**: For specific payment issues

Most billing issues can be resolved through your account dashboard or by contacting support directly.`,

    general: `I'm here to help with customer support questions! I can assist with:

- Cancellations and refunds
- Billing and payment issues
- Contact information
- Account management
- General support policies

Please ask me a specific question about any of these topics, and I'll do my best to help based on this website's documentation.`
  };
  
  return responses[category] || responses.general;
}

function addMessage(message, type) {
  const chatContainer = document.getElementById('chatContainer');
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${type}-message`;
  messageDiv.innerHTML = message.replace(/\n/g, '<br>');
  
  chatContainer.appendChild(messageDiv);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}