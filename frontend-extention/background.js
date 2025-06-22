// Background script for handling extension lifecycle
class BackgroundService {
  constructor() {
    this.setupEventListeners();
  }

  setupEventListeners() {
    // Handle extension installation
    chrome.runtime.onInstalled.addListener((details) => {
      if (details.reason === 'install') {
        console.log('Customer Support Extension installed');
        this.showWelcomeNotification();
      }
    });

    // Handle tab updates
    chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
      if (changeInfo.status === 'complete' && tab.url) {
        this.handleTabUpdate(tab);
      }
    });

    // Handle messages from content scripts and popup
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      this.handleMessage(request, sender, sendResponse);
      return true;
    });
  }

  showWelcomeNotification() {
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon48.png',
      title: 'AI Customer Support Assistant',
      message: 'Extension installed! Click the icon to start getting help with customer support.'
    });
  }

  handleTabUpdate(tab) {
    // Store current tab info for context
    chrome.storage.local.set({
      currentTab: {
        url: tab.url,
        title: tab.title,
        timestamp: Date.now()
      }
    });
  }

  handleMessage(request, sender, sendResponse) {
    switch (request.action) {
      case 'getTabInfo':
        this.getTabInfo(sendResponse);
        break;
      case 'storeKnowledgeBase':
        this.storeKnowledgeBase(request.data, sendResponse);
        break;
      case 'getKnowledgeBase':
        this.getKnowledgeBase(request.domain, sendResponse);
        break;
      default:
        sendResponse({ error: 'Unknown action' });
    }
  }

  async getTabInfo(sendResponse) {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      sendResponse({ success: true, tab: tab });
    } catch (error) {
      sendResponse({ success: false, error: error.message });
    }
  }

  async storeKnowledgeBase(data, sendResponse) {
    try {
      const domain = new URL(data.url).hostname;
      const key = `knowledge_${domain}`;
      
      await chrome.storage.local.set({
        [key]: {
          ...data,
          timestamp: Date.now(),
          version: '1.0'
        }
      });
      
      sendResponse({ success: true });
    } catch (error) {
      sendResponse({ success: false, error: error.message });
    }
  }

  async getKnowledgeBase(domain, sendResponse) {
    try {
      const key = `knowledge_${domain}`;
      const result = await chrome.storage.local.get([key]);
      
      if (result[key]) {
        sendResponse({ success: true, data: result[key] });
      } else {
        sendResponse({ success: false, message: 'No knowledge base found' });
      }
    } catch (error) {
      sendResponse({ success: false, error: error.message });
    }
  }
}

// Initialize background service
new BackgroundService();