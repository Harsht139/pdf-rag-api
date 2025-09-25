const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function uploadPdfFile(file) {
  const form = new FormData();
  form.append('file', file);
  
  const res = await fetch(`${BASE_URL}/api/v1/documents/upload`, {
    method: 'POST',
    // Don't set Content-Type for FormData, let the browser set it with the correct boundary
    body: form,
  });
  
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Upload failed');
  }
  return res.json();
}

export async function uploadPdfLink(url) {
  const res = await fetch(`${BASE_URL}/api/v1/documents/upload_link`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ pdf_url: url }),
  });
  
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Upload link failed');
  }
  return res.json();
}
