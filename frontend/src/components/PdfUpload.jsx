import React, { useCallback, useState } from 'react';
import { uploadDocument, ingestFromUrl } from '../services/api';

const PdfUpload = ({ onUploadStart, onUploadSuccess, isProcessing }) => {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
  const [url, setUrl] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const uploadedFile = e.dataTransfer.files[0];
      if (uploadedFile.type === 'application/pdf') {
        setFile(uploadedFile);
      } else {
        alert('Please upload a PDF file');
      }
    }
  }, []);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (selectedFile.type === 'application/pdf') {
        setFile(selectedFile);
      } else {
        alert('Please upload a PDF file');
      }
    }
  };

  const handleClick = () => {
    if (!isProcessing) {
      document.getElementById('file-upload').click();
    }
  };

  const handleUrlSubmit = async (e) => {
    e.preventDefault();
    if (!url) return;

    onUploadStart();
    setUploadProgress(50);

    try {
      const data = await ingestFromUrl(url);
      setUploadProgress(100);

      onUploadSuccess({
        id: data.id,
        file_url: data.file_url,
        filename: data.filename,
        status: 'completed'
      });
    } catch (error) {
      console.error('URL processing failed:', error);
      alert(error.message || 'Failed to process URL. Please try again.');
      setUploadProgress(0);
    }
  };

  const handleFileSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    onUploadStart();
    setUploadProgress(50);

    try {
      const data = await uploadDocument(file);
      setUploadProgress(100);

      onUploadSuccess({
        id: data.id,
        file_url: data.file_url,
        filename: data.filename,
        status: 'completed'
      });
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Failed to upload file. Please try again.');
      setUploadProgress(0);
    }
  };

  return (
    <div className="space-y-6">
      {/* File Upload */}
      <div>
        <h3 className="text-md font-medium text-gray-700 mb-2">Upload a PDF</h3>
        <div
          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer ${
            dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400'
          }`}
          onClick={handleClick}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && handleClick()}
        >
          <div className="space-y-2">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="text-xs text-gray-500">PDF (max. 10MB)</p>
            <div>
              <p className="text-sm text-gray-600">
                <span className="font-medium text-blue-600 hover:text-blue-500">
                  Click to upload
                </span>{' '}
                or drag and drop
              </p>
              <p className="text-xs text-gray-500 mt-1">PDF (max. 10MB)</p>
              <input
                id="file-upload"
                name="file-upload"
                type="file"
                className="sr-only"
                accept=".pdf"
                onChange={handleFileChange}
                disabled={isProcessing}
              />
            </div>
          </div>
        </div>
        {file && (
          <div className="mt-2 flex items-center justify-between">
            <p className="text-sm text-gray-600 truncate">{file.name}</p>
            <button
              type="button"
              className="text-red-600 hover:text-red-800 text-sm font-medium"
              onClick={() => setFile(null)}
            >
              Remove
            </button>
          </div>
        )}
        <div className="mt-4">
          <button
            type="button"
            onClick={handleFileSubmit}
            disabled={!file || isProcessing}
            className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
              !file || isProcessing
                ? 'bg-blue-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
            }`}
          >
            {isProcessing ? 'Uploading...' : 'Upload PDF'}
          </button>
        </div>
      </div>

      {/* Divider with "or" */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center" aria-hidden="true">
          <div className="w-full border-t border-gray-300" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-2 bg-white text-gray-500">Or</span>
        </div>
      </div>

      {/* URL Input */}
      <div>
        <h3 className="text-md font-medium text-gray-700 mb-2">Enter PDF URL</h3>
        <form onSubmit={handleUrlSubmit} className="flex space-x-2">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/document.pdf"
            className="flex-1 min-w-0 block w-full px-3 py-2 rounded-md border border-gray-300 shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            disabled={isProcessing}
          />
          <button
            type="submit"
            disabled={!url || isProcessing}
            className={`inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white ${
              !url || isProcessing
                ? 'bg-blue-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
            }`}
          >
            Load
          </button>
        </form>
      </div>

      {/* Progress Bar */}
      {uploadProgress > 0 && uploadProgress < 100 && (
        <div className="mt-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Uploading...</span>
            <span>{Math.round(uploadProgress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            ></div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PdfUpload;
