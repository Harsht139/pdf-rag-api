import React, { useState } from 'react';
import PdfUpload from '../components/PdfUpload';
import ChatBox from '../components/ChatBox';

const Home = () => {
  const [documentId, setDocumentId] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleUploadSuccess = (docId) => {
    setDocumentId(docId);
    setIsProcessing(false);
  };

  const handleUploadStart = () => {
    setIsProcessing(true);
  };

  return (
    <div className="flex flex-col md:flex-row gap-6 w-full">
      <div className="w-full md:w-1/2">
        <div className="bg-white rounded-lg shadow-md p-6 h-full">
          <h2 className="text-xl font-semibold mb-4">Upload PDF</h2>
          <PdfUpload
            onUploadStart={handleUploadStart}
            onUploadSuccess={handleUploadSuccess}
            isProcessing={isProcessing}
          />
          {isProcessing && (
            <p className="mt-4 text-sm text-gray-500">Processing document...</p>
          )}
          {documentId && !isProcessing && (
            <p className="mt-4 text-sm text-green-600">Document ready for chat!</p>
          )}
        </div>
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
