const API_BASE_URL = ''; // Using proxy in development

/**
 * Generic API request handler with enhanced error handling
 */
async function request(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // Remove content-type for FormData
  if (options.body instanceof FormData) {
    delete headers['Content-Type'];
  }

  const config = {
    ...options,
    headers,
    credentials: 'include', // Include cookies in requests
  };

  console.log(`[API] ${options.method || 'GET'} ${endpoint}`);

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
    
    // Check if response is JSON
    const contentType = response.headers.get('content-type');
    let data;
    
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      const text = await response.text();
      console.error('Non-JSON response:', text);
      throw new Error(`Unexpected response format: ${text.substring(0, 100)}...`);
    }
    
    if (!response.ok) {
      console.error('API Error:', {
        status: response.status,
        statusText: response.statusText,
        url: response.url,
        data
      });
      throw new Error(data.message || `API request failed with status ${response.status}`);
    }
    
    return data;
  } catch (error) {
    console.error('API request failed:', {
      endpoint,
      error: error.message,
      stack: error.stack
    });
    throw error;
  }
}

// API methods
export const api = {
  // Health check
  getHealth: () => request('/api/health'),
  
  // Example API methods - update these based on your actual endpoints
  uploadPdf: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    return request('/api/upload', {
      method: 'POST',
      body: formData,
      // Remove Content-Type header to let the browser set it with the correct boundary
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  // Add more API methods as needed
  processPdf: (pdfId) => 
    request(`/api/process_pdf/${pdfId}`, {
      method: 'POST',
    }),
  
  queryPdf: (query, pdfId) =>
    request(`/api/query`, {
      method: 'POST',
      body: JSON.stringify({ query, pdf_id: pdfId }),
    }),
};
