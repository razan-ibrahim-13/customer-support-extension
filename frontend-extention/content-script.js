// Enhanced Website Analyzer with deep scraping capabilities
class AdvancedWebsiteAnalyzer {
  constructor() {
    this.supportSections = {};
    this.crawledUrls = new Set();
    this.maxDepth = 3;
    this.currentDepth = 0;
    
    this.supportPatterns = [
      '/help', '/support', '/faq', '/contact', '/customer-service',
      '/documentation', '/docs', '/knowledge-base', '/help-center',
      '/cancellation', '/refund', '/billing', '/terms', '/policy'
    ];
    
    this.contentTypes = {
      faq: ['faq', 'frequently asked', 'common questions'],
      policy: ['policy', 'terms', 'conditions', 'agreement'],
      contact: ['contact', 'support', 'help', 'customer service'],
      billing: ['billing', 'payment', 'subscription', 'pricing'],
      cancellation: ['cancel', 'cancellation', 'unsubscribe', 'terminate'],
      refund: ['refund', 'return', 'money back', 'reimbursement']
    };
  }

  async performDeepAnalysis() {
    try {
      console.log('Starting deep website analysis...');
      
      // Phase 1: Analyze current page
      const currentPageData = await this.analyzeCurrentPage();
      
      // Phase 2: Discover support links
      const supportLinks = await this.discoverSupportLinks();
      
      // Phase 3: Crawl discovered links
      const crawledContent = await this.crawlSupportPages(supportLinks);
      
      // Phase 4: Process and structure content
      const structuredData = await this.processAndStructureContent(crawledContent);
      
      // Phase 5: Extract actionable information
      const actionableData = await this.extractActionableInformation(structuredData);
      
      return {
        currentPage: currentPageData,
        supportSections: structuredData,
        actionableInfo: actionableData,
        crawlStats: {
          pagesAnalyzed: this.crawledUrls.size,
          contentTypes: Object.keys(structuredData),
          timestamp: new Date().toISOString()
        }
      };
      
    } catch (error) {
      console.error('Deep analysis error:', error);
      return { error: error.message };
    }
  }

  async discoverSupportLinks() {
    const links = new Set();
    const baseUrl = window.location.origin;
    
    // Method 1: Find links in navigation
    const navLinks = this.findNavigationLinks();
    navLinks.forEach(link => links.add(link));
    
    // Method 2: Check sitemap.xml
    try {
      const sitemapLinks = await this.checkSitemap(baseUrl);
      sitemapLinks.forEach(link => links.add(link));
    } catch (error) {
      console.log('Sitemap not accessible:', error.message);
    }
    
    // Method 3: Check robots.txt
    try {
      const robotsLinks = await this.checkRobotsTxt(baseUrl);
      robotsLinks.forEach(link => links.add(link));
    } catch (error) {
      console.log('Robots.txt not accessible:', error.message);
    }
    
    // Method 4: Common URL patterns
    const commonLinks = this.generateCommonSupportUrls(baseUrl);
    commonLinks.forEach(link => links.add(link));
    
    return Array.from(links);
  }

  findNavigationLinks() {
    const links = [];
    const allLinks = document.querySelectorAll('a[href]');
    
    allLinks.forEach(link => {
      const href = link.getAttribute('href');
      const text = link.textContent.toLowerCase().trim();
      const url = this.resolveUrl(href);
      
      // Check if link is support-related
      if (this.isSupportRelated(url, text)) {
        links.push({
          url: url,
          text: text,
          type: this.categorizeLink(url, text),
          location: this.getLinkLocation(link)
        });
      }
    });
    
    return links;
  }

  async checkSitemap(baseUrl) {
    const sitemapUrls = [`${baseUrl}/sitemap.xml`, `${baseUrl}/sitemap_index.xml`];
    const links = [];
    
    for (const sitemapUrl of sitemapUrls) {
      try {
        const response = await fetch(sitemapUrl);
        if (response.ok) {
          const text = await response.text();
          const parser = new DOMParser();
          const xmlDoc = parser.parseFromString(text, 'text/xml');
          
          const urls = xmlDoc.querySelectorAll('url loc, sitemap loc');
          urls.forEach(urlElement => {
            const url = urlElement.textContent;
            if (this.isSupportRelated(url, '')) {
              links.push({
                url: url,
                source: 'sitemap',
                type: this.categorizeLink(url, '')
              });
            }
          });
        }
      } catch (error) {
        console.log(`Could not fetch ${sitemapUrl}:`, error.message);
      }
    }
    
    return links;
  }

  async crawlSupportPages(supportLinks) {
    const crawledContent = {};
    const maxConcurrent = 3; // Respect server resources
    
    // Process links in batches
    for (let i = 0; i < supportLinks.length; i += maxConcurrent) {
      const batch = supportLinks.slice(i, i + maxConcurrent);
      
      const batchPromises = batch.map(async (linkInfo) => {
        if (this.crawledUrls.has(linkInfo.url)) {
          return null;
        }
        
        try {
          const content = await this.crawlSinglePage(linkInfo.url);
          this.crawledUrls.add(linkInfo.url);
          
          return {
            url: linkInfo.url,
            type: linkInfo.type,
            content: content,
            metadata: {
              crawledAt: new Date().toISOString(),
              linkText: linkInfo.text,
              source: linkInfo.source || 'navigation'
            }
          };
        } catch (error) {
          console.error(`Error crawling ${linkInfo.url}:`, error.message);
          return null;
        }
      });
      
      const batchResults = await Promise.all(batchPromises);
      
      // Add successful results to crawled content
      batchResults.forEach(result => {
        if (result) {
          crawledContent[result.url] = result;
        }
      });
      
      // Small delay between batches to be respectful
      if (i + maxConcurrent < supportLinks.length) {
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
    
    return crawledContent;
  }

  async crawlSinglePage(url) {
    // Note: In a real extension, you'd need to use chrome.tabs.create or 
    // send messages to background script for cross-origin requests
    
    return new Promise((resolve, reject) => {
      // Send message to background script to fetch content
      chrome.runtime.sendMessage({
        action: 'fetchPageContent',
        url: url
      }, (response) => {
        if (response && response.success) {
          resolve(this.extractContentFromHtml(response.html));
        } else {
          reject(new Error(response?.error || 'Failed to fetch content'));
        }
      });
    });
  }

  extractContentFromHtml(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    
    // Remove unwanted elements
    const unwantedSelectors = [
      'script', 'style', 'nav', 'header', 'footer', 
      '.advertisement', '.ads', '.sidebar', '.menu'
    ];
    
    unwantedSelectors.forEach(selector => {
      const elements = doc.querySelectorAll(selector);
      elements.forEach(el => el.remove());
    });
    
    // Extract structured content
    const content = {
      title: this.extractTitle(doc),
      headings: this.extractHeadings(doc),
      paragraphs: this.extractParagraphs(doc),
      lists: this.extractLists(doc),
      tables: this.extractTables(doc),
      forms: this.extractForms(doc),
      contactInfo: this.extractContactInfo(doc),
      metadata: this.extractMetadata(doc)
    };
    
    return content;
  }

  processAndStructureContent(crawledContent) {
    const structured = {};
    
    Object.entries(crawledContent).forEach(([url, pageData]) => {
      const processed = {
        url: url,
        type: pageData.type,
        title: pageData.content.title,
        sections: this.identifyContentSections(pageData.content),
        policies: this.extractPolicies(pageData.content),
        procedures: this.extractProcedures(pageData.content),
        contactInfo: pageData.content.contactInfo,
        lastUpdated: pageData.metadata.crawledAt
      };
      
      structured[pageData.type] = structured[pageData.type] || [];
      structured[pageData.type].push(processed);
    });
    
    return structured;
  }

  extractActionableInformation(structuredData) {
    const actionable = {
      cancellation: {
        steps: [],
        requirements: [],
        deadlines: [],
        contactMethods: []
      },
      refunds: {
        policies: [],
        timeframes: [],
        procedures: [],
        exceptions: []
      },
      billing: {
        paymentMethods: [],
        cycles: [],
        issues: [],
        contacts: []
      },
      contact: {
        emails: [],
        phones: [],
        hours: [],
        departments: []
      }
    };
    
    // Process each content type
    Object.entries(structuredData).forEach(([type, pages]) => {
      pages.forEach(page => {
        this.extractActionableFromPage(page, actionable);
      });
    });
    
    return actionable;
  }

  // Utility methods
  isSupportRelated(url, text) {
    const combined = (url + ' ' + text).toLowerCase();
    const supportKeywords = [
      'help', 'support', 'faq', 'contact', 'customer', 'service',
      'documentation', 'docs', 'knowledge', 'cancel', 'refund',
      'billing', 'payment', 'terms', 'policy', 'privacy'
    ];
    
    return supportKeywords.some(keyword => combined.includes(keyword));
  }

  categorizeLink(url, text) {
    const combined = (url + ' ' + text).toLowerCase();
    
    for (const [category, keywords] of Object.entries(this.contentTypes)) {
      if (keywords.some(keyword => combined.includes(keyword))) {
        return category;
      }
    }
    
    return 'general';
  }

  resolveUrl(href) {
    if (href.startsWith('http')) {
      return href;
    } else if (href.startsWith('/')) {
      return window.location.origin + href;
    } else {
      return new URL(href, window.location.href).href;
    }
  }

  // Additional extraction methods...
  extractTitle(doc) {
    return doc.querySelector('title')?.textContent?.trim() || '';
  }

  extractHeadings(doc) {
    const headings = [];
    const headingElements = doc.querySelectorAll('h1, h2, h3, h4, h5, h6');
    
    headingElements.forEach(heading => {
      headings.push({
        level: parseInt(heading.tagName[1]),
        text: heading.textContent.trim(),
        id: heading.id || null
      });
    });
    
    return headings;
  }

  extractParagraphs(doc) {
    const paragraphs = [];
    const pElements = doc.querySelectorAll('p');
    
    pElements.forEach(p => {
      const text = p.textContent.trim();
      if (text.length > 20) { // Filter out short/empty paragraphs
        paragraphs.push(text);
      }
    });
    
    return paragraphs;
  }

  extractLists(doc) {
    const lists = [];
    const listElements = doc.querySelectorAll('ul, ol');
    
    listElements.forEach(list => {
      const items = Array.from(list.querySelectorAll('li')).map(li => 
        li.textContent.trim()
      );
      
      if (items.length > 0) {
        lists.push({
          type: list.tagName.toLowerCase(),
          items: items
        });
      }
    });
    
    return lists;
  }

  extractContactInfo(doc) {
    const contactInfo = {};
    const bodyText = doc.body.textContent;
    
    // Extract emails
    const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
    contactInfo.emails = [...new Set(bodyText.match(emailRegex) || [])];
    
    // Extract phone numbers  
    const phoneRegex = /(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}/g;
    contactInfo.phones = [...new Set(bodyText.match(phoneRegex) || [])];
    
    // Extract business addresses
    const addressElements = doc.querySelectorAll('[class*="address"], [class*="location"]');
    contactInfo.addresses = Array.from(addressElements).map(el => 
      el.textContent.trim()
    ).filter(addr => addr.length > 10);
    
    return contactInfo;
  }
}

// Initialize enhanced analyzer
const enhancedAnalyzer = new AdvancedWebsiteAnalyzer();

// Enhanced message listener
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'performDeepAnalysis') {
    enhancedAnalyzer.performDeepAnalysis()
      .then(data => {
        sendResponse({ success: true, data: data });
      })
      .catch(error => {
        console.error('Deep analysis error:', error);
        sendResponse({ success: false, error: error.message });
      });
    
    return true; // Keep message channel open
  }
  
  // Keep original analyze message for backward compatibility
  if (request.action === 'analyzeWebsite') {
    enhancedAnalyzer.analyzeCurrentPage()
      .then(data => {
        sendResponse({ success: true, data: data });
      })
      .catch(error => {
        sendResponse({ success: false, error: error.message });
      });
    
    return true;
  }
});