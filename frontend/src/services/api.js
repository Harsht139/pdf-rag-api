const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const handleResponse = async (response) => {
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'An error occurred');
  }
  return data;
};

export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/upload`, {
    method: 'POST',
    body: formData,
  });
  
  return handleResponse(response);
};

export const ingestFromUrl = async (url) => {
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/ingest/url?url=${encodeURIComponent(url)}`, {
    method: 'POST',
  });
  
  return handleResponse(response);
};

export const getDocument = async (documentId) => {
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}`);
  return handleResponse(response);
};

export const listDocuments = async () => {
  const response = await fetch(`${API_BASE_URL}/api/v1/documents`);
  return handleResponse(response);
};

export const deleteDocument = async (documentId) => {
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}`, {
    method: 'DELETE',
  });
  
  return handleResponse(response);
};

export const sendChatMessage = async (messages, documentId) => {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      messages,
      document_id: documentId,
    }),
  });
  
  return handleResponse(response);
};
