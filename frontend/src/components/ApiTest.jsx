import { useEffect, useState } from 'react';
import { api } from '../services/api';

const ApiTest = () => {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [requestDetails, setRequestDetails] = useState({
    method: 'GET',
    endpoint: '/api/health',
    response: null,
    status: null,
    headers: {}
  });

  const testEndpoint = async (method = 'GET', endpoint = '/api/health') => {
    setLoading(true);
    setError(null);
    
    try {
      console.log(`Testing ${method} ${endpoint}`);
      const response = await fetch(endpoint, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
      });

      let data;
      const contentType = response.headers.get('content-type');
      
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      setRequestDetails({
        method,
        endpoint,
        response: data,
        status: response.status,
        headers: Object.fromEntries(response.headers.entries())
      });

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      setHealth(data);
    } catch (err) {
      console.error('Test failed:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    testEndpoint();
  }, []);

  const formatJson = (obj) => {
    try {
      return JSON.stringify(obj, null, 2);
    } catch (e) {
      return String(obj);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto mt-10 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">API Connection Tester</h2>
      
      <div className="mb-6 p-4 bg-blue-50 rounded-md">
        <h3 className="font-semibold mb-2">Test Endpoint</h3>
        <div className="flex gap-2 mb-2">
          <select 
            className="border rounded px-3 py-1"
            value={requestDetails.method}
            onChange={(e) => setRequestDetails(prev => ({...prev, method: e.target.value}))}
          >
            <option value="GET">GET</option>
            <option value="POST">POST</option>
          </select>
          <input
            type="text"
            className="flex-1 border rounded px-3 py-1"
            value={requestDetails.endpoint}
            onChange={(e) => setRequestDetails(prev => ({...prev, endpoint: e.target.value}))}
            placeholder="/api/endpoint"
          />
          <button 
            onClick={() => testEndpoint(requestDetails.method, requestDetails.endpoint)}
            className="bg-blue-500 text-white px-4 py-1 rounded hover:bg-blue-600"
            disabled={loading}
          >
            {loading ? 'Testing...' : 'Test'}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center p-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-2 text-gray-600">Connecting to API...</p>
        </div>
      ) : error ? (
        <div className="p-4 mb-6 bg-red-50 border-l-4 border-red-500">
          <h3 className="font-bold text-red-700">Error</h3>
          <p className="text-red-600">{error}</p>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="p-4 bg-green-50 border-l-4 border-green-500">
            <h3 className="font-bold text-green-700">✓ Connection Successful</h3>
            <p className="text-green-600">API is responding correctly</p>
          </div>

          <div>
            <h3 className="font-semibold mb-2">Response Status: {requestDetails.status}</h3>
            <div className="bg-gray-50 p-3 rounded overflow-x-auto">
              <pre className="text-sm">{formatJson(requestDetails.response)}</pre>
            </div>
          </div>

          <div>
            <h3 className="font-semibold mb-2">Response Headers</h3>
            <div className="bg-gray-50 p-3 rounded overflow-x-auto">
              <pre className="text-sm">{formatJson(requestDetails.headers)}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ApiTest;
