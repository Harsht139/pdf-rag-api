import { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Progress } from './ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Upload, Link as LinkIcon, Loader2, FileText } from 'lucide-react';

const PdfUpload = ({ onUpload, isProcessing }) => {
  const [file, setFile] = useState(null);
  const [url, setUrl] = useState('');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      if (selectedFile.type === 'application/pdf') {
        if (selectedFile.size > 10 * 1024 * 1024) { // 10MB limit
          setError('File size should be less than 10MB');
        } else {
          setFile(selectedFile);
          setError('');
        }
      } else {
        setError('Please upload a valid PDF file');
      }
    }
  };

  const handleUrlSubmit = (e) => {
    e.preventDefault();
    if (url) {
      handleSubmit('url', url);
    } else {
      setError('Please enter a valid URL');
    }
  };

  const handleFileSubmit = (e) => {
    e.preventDefault();
    if (file) {
      handleSubmit('file', file);
    } else {
      setError('Please select a PDF file');
    }
  };

  const handleSubmit = async (method, source) => {
    setError('');

    try {
      // Simulate upload progress
      if (method === 'file') {
        const interval = setInterval(() => {
          setProgress(prev => {
            if (prev >= 90) {
              clearInterval(interval);
              return 90;
            }
            return prev + 10;
          });
        }, 200);

        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1500));
        clearInterval(interval);
        setProgress(100);
      }

      // Call the parent handler with the source (file or URL)
      onUpload(source);

      // Reset form
      if (method === 'file') {
        // Keep the file reference but reset the input
        const fileInput = document.querySelector('input[type="file"]');
        if (fileInput) fileInput.value = '';
      } else {
        setUrl('');
      }
    } catch (err) {
      setError(err.message || 'An error occurred while uploading');
    } finally {
      if (method === 'file') {
        setTimeout(() => setProgress(0), 1000);
      }
    }
  };

  return (
    <div className="space-y-3">
      <Tabs defaultValue="file" className="w-full">
        <TabsList className="grid w-full grid-cols-2 h-8">
          <TabsTrigger value="file" className="flex items-center gap-1.5 text-xs">
            <Upload className="h-3 w-3" />
            Upload File
          </TabsTrigger>
          <TabsTrigger value="url" className="flex items-center gap-1.5 text-xs">
            <LinkIcon className="h-3 w-3" />
            From URL
          </TabsTrigger>
        </TabsList>

        <TabsContent value="file" className="mt-3">
          <form onSubmit={handleFileSubmit} className="space-y-3">
            <div className="space-y-2">
              <div className="flex items-center justify-center w-full">
                <label className="flex flex-col items-center justify-center w-full h-20 border border-dashed rounded-md cursor-pointer bg-gray-50 hover:bg-gray-100 transition-colors border-gray-300">
                  <div className="flex flex-col items-center justify-center px-3 py-2 text-center">
                    <Upload className="h-4 w-4 mb-1 text-gray-500" />
                    <p className="text-xs text-gray-600">
                      <span className="font-medium">Click to upload</span> or drag and drop
                    </p>
                    <p className="text-[10px] text-gray-500">PDF (max. 10MB)</p>
                  </div>
                  <input
                    type="file"
                    className="hidden"
                    accept=".pdf"
                    onChange={handleFileChange}
                    disabled={isProcessing}
                  />
                </label>
              </div>

              {file && (
                <div className="flex items-center justify-between p-1.5 bg-gray-50 rounded text-xs">
                  <div className="flex items-center space-x-1.5 overflow-hidden">
                    <FileText className="h-3.5 w-3.5 text-gray-500 flex-shrink-0" />
                    <span className="font-medium text-gray-700 truncate">
                      {file.name}
                    </span>
                  </div>
                  <span className="text-gray-500">
                    {(file.size / (1024 * 1024)).toFixed(1)} MB
                  </span>
                </div>
              )}
            </div>

            {progress > 0 && progress < 100 && (
              <div className="space-y-1">
                <Progress value={progress} className="h-1.5" />
                <p className="text-[10px] text-gray-500 text-right">
                  Uploading... {progress}%
                </p>
              </div>
            )}

            <Button
              type="submit"
              className="w-full h-8 text-xs"
              disabled={!file || isProcessing}
              size="sm"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                  Uploading...
                </>
              ) : (
                'Upload PDF'
              )}
            </Button>
          </form>
        </TabsContent>

        <TabsContent value="url" className="mt-3">
          <form onSubmit={handleUrlSubmit} className="space-y-3">
            <div className="space-y-1.5">
              <Input
                type="url"
                placeholder="Enter PDF URL"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={isProcessing}
                className="h-8 text-xs"
              />
              <p className="text-[10px] text-gray-500">
                Enter a direct URL to a PDF file
              </p>
            </div>
            <Button
              type="submit"
              className="w-full h-8 text-xs"
              disabled={!url || isProcessing}
              size="sm"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                  Processing...
                </>
              ) : (
                'Load from URL'
              )}
            </Button>
          </form>
        </TabsContent>
      </Tabs>

      {error && (
        <div className="mt-2 p-2 text-xs text-red-600 bg-red-50 rounded">
          {error}
        </div>
      )}
    </div>
  );
};

export default PdfUpload;
