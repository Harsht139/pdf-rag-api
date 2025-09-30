import { useState } from 'react';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [pdfUrl, setPdfUrl] = useState('');
  const [uploadedUrl, setUploadedUrl] = useState('');
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file && !pdfUrl) {
      setError('Please select a file or enter a URL');
      return;
    }
    
    setIsLoading(true);
    setError('');
    setSuccess('');
    const formData = new FormData();
    
    try {
      if (file) {
        formData.append('file', file);
        const response = await fetch('http://localhost:8000/upload', {
          method: 'POST',
          body: formData,
          // Don't set Content-Type header, let the browser set it with the correct boundary
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to upload file');
        }
        
        const data = await response.json();
        // Store both the public URL and the file name
        setUploadedUrl(data.file_name);
      } else if (pdfUrl) {
        // Handle URL upload
        const response = await fetch('http://localhost:8000/upload-url', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ url: pdfUrl }),
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to upload from URL');
        }
        
        const data = await response.json();
        // Store the file name for the proxy endpoint
        setUploadedUrl(data.file_name);
        setSuccess('PDF uploaded successfully from URL!');
      }
    } catch (error) {
      console.error('Upload failed:', error);
      setError(error.message || 'Upload failed. Please try again.');
    } finally {
      setIsLoading(false);
      // Clear success/error messages after 5 seconds
      if (success || error) {
        setTimeout(() => {
          setSuccess('');
          setError('');
        }, 5000);
      }
    }
  };

  const handleSendMessage = async () => {
    if (!query.trim() || !uploadedUrl) return;
    
    const userMessage = { text: query, sender: 'user' };
    setMessages(prev => [...prev, userMessage]);
    
    const tempQuery = query;
    setQuery('');
    setIsLoading(true);
    
    try {
      // First, check if we need to process the document
      // This is a placeholder - you'll need to implement this endpoint
      const processResponse = await fetch('http://localhost:8000/process-document', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_url: uploadedUrl
        }),
      });
      
      if (!processResponse.ok) {
        throw new Error('Failed to process document');
      }
      
      // Then send the chat message
      const chatResponse = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          query: tempQuery,
          document_url: uploadedUrl 
        }),
      });
      
      if (!chatResponse.ok) {
        const errorData = await chatResponse.json();
        throw new Error(errorData.detail || 'Failed to get response');
      }
      
      const data = await chatResponse.json();
      setMessages(prev => [...prev, { text: data.answer || 'I received your message but the response format was unexpected.', sender: 'ai' }]);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, { 
        text: 'Sorry, I encountered an error. Please try again.', 
        sender: 'ai' 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <h1>PDF Chat Assistant</h1>
      
      <div className="main-layout">
        <div className="upload-section">
          <h2>Upload PDF</h2>
          <div className="upload-options">
            <div>
              <input type="file" accept=".pdf" onChange={handleFileChange} disabled={!!pdfUrl} />
            </div>
            <div className="or-divider">OR</div>
            <div>
              <input 
                type="text" 
                placeholder="Enter PDF URL" 
                value={pdfUrl}
                onChange={(e) => setPdfUrl(e.target.value)}
                disabled={!!file}
              />
            </div>
          </div>
          <button 
            onClick={handleUpload} 
            disabled={isLoading || (!file && !pdfUrl)}
          >
            {isLoading ? 'Uploading...' : 'Upload'}
          </button>
          
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}
          
          {success && (
            <div className="success-message">
              {success}
            </div>
          )}
          
          {uploadedUrl && (
            <div className="upload-success">
              <p>Document uploaded successfully!</p>
              <a href={`http://localhost:8000/files/${uploadedUrl.split('/').pop()}`} target="_blank" rel="noopener noreferrer">
                View Document
              </a>
            </div>
          )}
        </div>

        <div className="chat-section">
          {uploadedUrl ? (
            <>
              <h2>Chat with your PDF</h2>
              <div className="chat-messages">
                {messages.length === 0 ? (
                  <div className="welcome-message">
                    <p>Ask questions about your PDF document here.</p>
                  </div>
                ) : (
                  messages.map((msg, index) => (
                    <div key={index} className={`message ${msg.sender}`}>
                      {msg.text}
                    </div>
                  ))
                )}
              </div>
              <div className="chat-input">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="Ask a question about the document..."
                  disabled={isLoading}
                />
                <button 
                  onClick={handleSendMessage}
                  disabled={isLoading || !query.trim()}
                >
                  {isLoading ? 'Sending...' : 'Send'}
                </button>
              </div>
            </>
          ) : (
            <div className="upload-prompt">
              <p>Upload a PDF to start chatting about its contents</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
