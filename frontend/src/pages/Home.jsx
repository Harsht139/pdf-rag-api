import React, { useState, useEffect } from 'react';
import PdfUpload from '../components/PdfUpload';
import ChatBox from '../components/ChatBox';
import { getDocument } from '../services/api';

const Home = () => {
  const [documentId, setDocumentId] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [documentUrl, setDocumentUrl] = useState('');

  const handleUploadSuccess = (documentData) => {
    try {
      setDocumentId(documentData.id);
      setDocumentUrl(documentData.file_url);
    } catch (error) {
      console.error('Error handling document:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleUploadStart = () => {
    setIsProcessing(true);
    setDocumentUrl('');
  };

  return (
    <div className="flex flex-col md:flex-row gap-6 w-full">
      <div className="w-full md:w-1/2 space-y-6">
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Upload PDF</h2>
          <PdfUpload
            onUploadStart={handleUploadStart}
            onUploadSuccess={handleUploadSuccess}
            isProcessing={isProcessing}
          />
          {isProcessing && (
            <p className="mt-4 text-sm text-gray-500">Processing document...</p>
          )}
        </div>

        {documentUrl && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Uploaded Document</h2>
            <div className="flex items-center space-x-2">
              <svg
                className="w-6 h-6 text-red-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                />
              </svg>
              <a
                href={documentUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 hover:underline font-medium text-lg"
              >
                View PDF in New Tab
              </a>
            </div>
            <div className="mt-2 text-sm text-gray-500">
              <p>Click the link above to view the document in a new tab.</p>
            </div>
          </div>
        )}
      </div>

      <div className="w-full md:w-1/2">
        <div className="bg-gray-100 rounded-lg shadow-md p-6 h-full">
          <h2 className="text-xl font-semibold mb-4">Chat with your PDF</h2>
          <ChatBox documentId={documentId} isProcessing={isProcessing} />
        </div>
      </div>
    </div>
  );
};

export default Home;
