import { useState } from 'react';
import PdfUpload from '../components/PdfUpload';
import ChatBox from '../components/ChatBox';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '../components/ui/card';
import { FileText, CheckCircle, Loader2, Bot, Upload, BookOpen, MessageCircle, Info } from 'lucide-react';

const Home = () => {
  const [uploadedPdf, setUploadedPdf] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [chatHistory, setChatHistory] = useState([
    {
      role: 'assistant',
      content: 'Hello! Upload a PDF and I\'ll help you analyze its content.',
      timestamp: new Date().toISOString()
    }
  ]);

  const handlePdfUpload = async (file) => {
    setIsProcessing(true);
    setUploadedPdf({
      name: file.name,
      size: file.size,
      status: 'uploading'
    });

    // Simulate processing delay
    setTimeout(() => {
      setUploadedPdf(prev => ({
        ...prev,
        status: 'ready'
      }));

      // Add a welcome message when PDF is processed
      setChatHistory(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `I've processed your PDF "${file.name}". You can now ask me questions about it!`,
          timestamp: new Date().toISOString()
        }
      ]);

      setIsProcessing(false);
    }, 1500);
  };

  const handleSendMessage = async (message) => {
    // Add user message to chat
    const userMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    };

    setChatHistory(prev => [...prev, userMessage]);

    // Simulate AI response
    setTimeout(() => {
      const response = {
        role: 'assistant',
        content: `This is a simulated response to: "${message}"`,
        timestamp: new Date().toISOString()
      };
      setChatHistory(prev => [...prev, response]);
    }, 1000);
  };

  // Make the container fit the content without scrolling
  const containerHeight = 'auto';

  return (
    <div className="min-h-screen bg-gray-50 p-4 overflow-hidden">
      <header className="mb-4 text-center">
        <h1 className="text-xl font-bold text-gray-900">PDF Chat Assistant</h1>
        <p className="text-gray-600 text-sm">Upload a PDF and chat with its contents</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-7xl mx-auto h-[80vh] min-h-[600px] px-4">
        {/* How It Works */}
        <Card className="flex flex-col shadow-md border border-gray-100">
          <CardHeader className="p-4 border-b">
            <CardTitle className="flex items-center gap-2 text-base font-semibold text-gray-800">
              <BookOpen className="h-4 w-4 text-blue-600" />
              How It Works
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-4 flex-1">
            <div className="relative pl-8">
              <div className="absolute left-0 top-0 h-6 w-6 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-medium">
                1
              </div>
              <h3 className="text-sm font-medium text-gray-900">Upload PDF</h3>
              <p className="text-xs text-gray-500 mt-0.5">Max 10MB file size</p>
            </div>

            <div className="h-px bg-gray-100 my-2"></div>

            <div className="relative pl-8">
              <div className="absolute left-0 top-0 h-6 w-6 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-medium">
                2
              </div>
              <h3 className="text-sm font-medium text-gray-900">Processing</h3>
              <p className="text-xs text-gray-500 mt-0.5">Takes a few seconds</p>
            </div>

            <div className="h-px bg-gray-100 my-2"></div>

            <div className="relative pl-8">
              <div className="absolute left-0 top-0 h-6 w-6 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-medium">
                3
              </div>
              <h3 className="text-sm font-medium text-gray-900">Start Chatting</h3>
              <p className="text-xs text-gray-500 mt-0.5">Ask about your document</p>
            </div>
          </CardContent>
        </Card>

        {/* PDF Upload Section */}
        <Card className="flex flex-col shadow-md border border-gray-100">
          <CardHeader className="p-4 border-b">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base font-semibold text-gray-800">
                <Upload className="h-4 w-4 text-blue-600" />
                Upload PDF
              </CardTitle>
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                Max 10MB
              </span>
            </div>
          </CardHeader>
          <CardContent className="p-4 flex-1 flex flex-col">
            <div className="flex-1">
              <PdfUpload
                onUpload={handlePdfUpload}
                isProcessing={isProcessing}
                className="text-sm"
              />

              {uploadedPdf && (
                <div className="mt-3 p-3 bg-blue-50 rounded-lg border border-blue-100 text-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 overflow-hidden">
                      <FileText className="h-4 w-4 text-blue-600 flex-shrink-0" />
                      <div className="min-w-0">
                        <p className="font-medium text-gray-900 truncate">
                          {uploadedPdf.name}
                        </p>
                        <p className="text-gray-500 text-xs">
                          {Math.round(uploadedPdf.size / 1024)} KB
                        </p>
                      </div>
                    </div>
                    {uploadedPdf.status === 'ready' ? (
                      <div className="flex items-center text-green-600 text-xs font-medium">
                        <CheckCircle className="h-3.5 w-3.5 mr-1.5" />
                        <span>Ready</span>
                      </div>
                    ) : (
                      <div className="flex items-center text-blue-600 text-xs font-medium">
                        <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                        <span>Processing</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Chat Section */}
        <Card className="flex flex-col shadow-md border border-gray-100">
          <CardHeader className="p-4 border-b">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <CardTitle className="flex items-center gap-2 text-base font-semibold text-gray-800">
                    <MessageCircle className="h-4 w-4 text-blue-600" />
                    Chat with your PDF
                  </CardTitle>
                  <div className="group relative">
                    <Info className="h-3.5 w-3.5 text-gray-400 hover:text-gray-600 cursor-help" />
                    <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block w-48 bg-gray-800 text-white text-xs p-2 rounded shadow-lg">
                      Ask questions about your uploaded PDF document and get instant answers.
                    </div>
                  </div>
                </div>
                <CardDescription className="text-xs mt-1">
                  {uploadedPdf
                    ? <span>Ask about <span className="font-medium text-gray-700">{uploadedPdf.name.split('.')[0]}</span></span>
                    : 'Upload a PDF to start chatting'}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0 flex-1 flex flex-col">
            <ChatBox
              chatHistory={chatHistory}
              isProcessing={!uploadedPdf || uploadedPdf.status !== 'ready' || isProcessing}
              onSendMessage={handleSendMessage}
              className="flex-1"
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Home;
