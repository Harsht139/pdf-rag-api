import React, { useState, useRef, useEffect } from 'react';
import { sendChatMessage } from '../services/api';
import { useDocumentStatus } from '../hooks/useDocumentStatus';

// Sample initial messages
const initialMessages = [
  {
    id: 1,
    role: 'assistant',
    content: 'Hello! Upload a PDF or provide a URL to get started. Then you can ask me questions about the document.',
    timestamp: new Date(Date.now() - 60000)
  }
];

const ChatBox = ({ documentId }) => {
  const { notification, clearNotification, lastUpdated, status } = useDocumentStatus(documentId);
  const isProcessing = status === 'processing' || status === 'uploading';
  const isReady = status === 'completed';
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || !documentId) return;

    // Add user message
    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    const currentInput = input; // keep a copy for fallbacks
    setInput('');
    setIsLoading(true);

    try {
      // Call the actual API
      const response = await sendChatMessage(
        updatedMessages.map(({ role, content }) => ({ role, content })),
        documentId
      );

      // Add assistant's response
      const responseText =
        (response && typeof response.message === 'string' && response.message) ||
        (response && response.message && response.message.content) ||
        '';

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: responseText && responseText.trim().length > 0
          ? responseText
          : getDummyResponse(currentInput),
        timestamp: new Date(),
        sources: Array.isArray(response?.sources) ? response.sources : []
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      // Add error message
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Simple function to generate dummy responses
  const getDummyResponse = (input) => {
    const responses = [
      "Based on the document, this is a sample response to your query about '" + input + "'.",
      "The document mentions that " + input + " is an important concept with several key aspects to consider.",
      "I found relevant information about " + input + ". Would you like me to elaborate on any specific aspect?",
      "The document provides detailed insights about " + input + ". Let me know if you'd like me to go deeper into this topic.",
      "I've analyzed the document and can provide information about " + input + ". What specific details are you interested in?"
    ];
    return responses[Math.floor(Math.random() * responses.length)];
  };

  const formatTime = (date) => {
    if (!(date instanceof Date)) {
      date = new Date(date);
    }
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="flex flex-col h-[500px] max-h-[70vh]">
      {/* Notification Banner */}
      {notification && (
        <div
          className={`p-3 mb-2 rounded-md ${
            notification.type === 'success'
              ? 'bg-green-100 text-green-800 border border-green-200'
              : notification.type === 'error'
                ? 'bg-red-100 text-red-800 border border-red-200'
                : 'bg-blue-100 text-blue-800 border border-blue-200'
          }`}
        >
          <div className="flex justify-between items-start">
            <div className="flex-1">
              <p className="font-medium">{notification.message}</p>
              {lastUpdated && (
                <p className="text-xs opacity-70 mt-1">
                  Last updated: {new Date(lastUpdated).toLocaleString()}
                </p>
              )}
            </div>
            <button
              onClick={clearNotification}
              className="ml-4 text-lg leading-none opacity-50 hover:opacity-100 focus:outline-none"
              aria-label="Dismiss notification"
            >
              &times;
            </button>
          </div>
        </div>
      )}
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 mb-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-xs md:max-w-md lg:max-w-lg xl:max-w-xl rounded-lg px-4 py-2 ${
                message.role === 'user'
                  ? 'bg-blue-500 text-white rounded-tr-none'
                  : 'bg-gray-200 text-gray-900 rounded-tl-none'
              }`}
            >
              <p className="text-sm">{message.content}</p>
              <p className={`text-xs mt-1 text-right ${
                message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
              }`}>
                {formatTime(message.timestamp)}
              </p>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-200 text-gray-900 rounded-lg px-4 py-2 rounded-tl-none">
              <div className="flex space-x-2">
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="mt-auto">
        <div className="flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={!documentId ? 'Upload a document to start chatting' : isProcessing ? 'Processing document...' : 'Type your question...'}
            className="flex-1 border border-gray-300 rounded-l-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
            disabled={!documentId || isProcessing || !isReady}
          />
          <button
            type="submit"
            disabled={!input.trim() || !documentId || isProcessing || isLoading || !isReady}
            className={`px-4 py-2 rounded-r-lg text-white ${
              !input.trim() || !documentId || isProcessing || isLoading || !isReady
                ? 'bg-blue-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
            }`}
            title={!isReady ? 'Document processing is not complete yet' : ''}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M10.293 5.293a1 1 0 011.414 0l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414-1.414L12.586 11H5a1 1 0 110-2h7.586l-2.293-2.293a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
        {!documentId && (
          <p className="text-xs text-gray-500 mt-2 text-center">
            Please upload a PDF or enter a URL to enable the chat
          </p>
        )}
      </form>
    </div>
  );
};

export default ChatBox;
