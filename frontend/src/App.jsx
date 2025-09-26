import { useState } from 'react';
import { Toaster } from './components/ui/toaster';
import PdfUpload from './components/PdfUpload';
import { uploadPdfFile, uploadPdfLink } from './api/apiClient';
import ChatBox from './components/ChatBox';
import { FileText, Loader2 } from 'lucide-react';
import './index.css';

function App() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadedPdf, setUploadedPdf] = useState(null);
  const [chatHistory, setChatHistory] = useState([
    {
      role: 'assistant',
      content: 'Hello! Upload a PDF document to get started.',
      timestamp: new Date().toISOString(),
    },
  ]);

  const handlePdfUpload = async (source) => {
    try {
      console.log('Starting upload with source:', source);
      setIsProcessing(true);
      let result;
      if (source instanceof File) {
        console.log('Uploading file:', source.name);
        result = await uploadPdfFile(source);
        setUploadedPdf({
          name: source.name,
          size: source.size,
          uploadedAt: new Date().toISOString(),
          documentId: result.document_id,
          filePath: result.file_path,
          publicUrl: result.public_url,
        });
      } else if (typeof source === 'string') {
        result = await uploadPdfLink(source);
        setUploadedPdf({
          name: source,
          size: 0,
          uploadedAt: new Date().toISOString(),
          documentId: result.document_id,
          filePath: result.file_path,
          publicUrl: result.public_url,
        });
      }

      // Add success message
      setChatHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Stored your document.',
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (error) {
      console.error('Error uploading PDF:', error);
      // Add error message
      setChatHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, there was an error processing your document. Please try again.',
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSendMessage = async (message) => {
    // Add user message to chat
    const userMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    setChatHistory((prev) => [...prev, userMessage]);
    setIsProcessing(true);

    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // Add bot response
      setChatHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `This is a simulated response to: "${message}"`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (error) {
      console.error('Error sending message:', error);
      // Add error message
      setChatHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, there was an error processing your message. Please try again.',
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Toaster />
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8 flex items-center">
          <FileText className="h-8 w-8 text-indigo-600 mr-3" />
          <h1 className="text-2xl font-bold text-gray-900">PDF RAG Chat</h1>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* PDF Upload Section */}
          <div className="w-full lg:w-1/3">
            <div className="bg-white rounded-lg shadow-md p-6 h-full">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900">Upload PDF</h2>
                {uploadedPdf && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Ready
                  </span>
                )}
              </div>

              <PdfUpload onUpload={handlePdfUpload} isProcessing={isProcessing} />

              {uploadedPdf && (
                <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-100">
                  <div className="flex items-start">
                    <FileText className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                    <div className="ml-3 flex-1">
                      <p className="text-sm font-medium text-gray-900 truncate">{uploadedPdf.name}</p>
                      <p className="text-xs text-gray-500">
                        {Math.round(uploadedPdf.size / 1024)} KB • {new Date(uploadedPdf.uploadedAt).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Chat Section */}
          <div className="w-full lg:w-2/3">
            <div className="bg-white rounded-lg shadow-md p-6 h-full">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900">Chat</h2>
                {isProcessing && (
                  <span className="inline-flex items-center text-sm text-gray-500">
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Processing...
                  </span>
                )}
              </div>

              <ChatBox
                chatHistory={chatHistory}
                onSendMessage={handleSendMessage}
                isProcessing={isProcessing}
              />
            </div>
          </div>
        </div>
      </main>

      <Toaster />
    </div>
  );
}

export default App;
