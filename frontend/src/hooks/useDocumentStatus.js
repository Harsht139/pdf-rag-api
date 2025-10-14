import { useState, useEffect, useRef, useCallback } from 'react';
import { supabase } from '../services/supabase';

export function useDocumentStatus(documentId) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [notification, setNotification] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const pollingRef = useRef(null);
  const channelRef = useRef(null);

  // Stop polling function
  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      console.log('Stopping polling...');
      clearInterval(pollingRef.current);
      pollingRef.current = null;
      console.log('Polling stopped');
      return true;
    }
    return false;
  }, []);

  // Handle status updates
  const handleStatusUpdate = useCallback((payload) => {
    console.log('Status update received:', payload);
    
    // Get the new status from the payload, handling both realtime updates and direct status strings
    let newStatus = null;
    
    if (typeof payload === 'string') {
      newStatus = payload.toLowerCase();
    } else if (payload?.new?.status) {
      newStatus = payload.new.status.toLowerCase();
    } else if (payload?.status) {
      newStatus = payload.status.toLowerCase();
    }
    
    if (!newStatus) {
      console.warn('No status found in payload:', payload);
      return;
    }
    
    console.log(`Status changed from ${status} to ${newStatus}`);
    
    // Always update the status and timestamp
    setStatus(newStatus);
    setLastUpdated(new Date().toISOString());
    
    // Set notification for status changes
    if (newStatus === 'completed') {
      console.log('Document processing completed, stopping polling');
      stopPolling();
      setNotification({
        type: 'success',
        message: '✅ Document processing completed! You can now chat with your document.'
      });
    } else if (newStatus === 'failed') {
      console.log('Document processing failed, stopping polling');
      stopPolling();
      setNotification({
        type: 'error',
        message: `❌ ${payload?.new?.error_message || payload?.error_message || 'Document processing failed. Please try again.'}`
      });
    } else if (newStatus === 'processing') {
      console.log('Document processing started');
      setNotification({
        type: 'info',
        message: '⏳ Document is being processed. This may take a few moments...'
      });
    } else if (newStatus === 'uploading') {
      setNotification({
        type: 'info',
        message: '📤 Uploading document...'
      });
    }
    
    // For any other status, make sure polling is running
    if (!pollingRef.current) {
      console.log('Starting polling for status updates');
      pollingRef.current = setInterval(fetchDocumentStatus, 2000);
    }
  }, [stopPolling]);

  // Function to fetch document status
  const fetchDocumentStatus = useCallback(async () => {
    if (!documentId) return;
    
    try {
      console.log('Fetching document status for:', documentId);
      const { data, error } = await supabase
        .from('documents')
        .select('status, error_message')
        .eq('id', documentId)
        .single();

      if (error) {
        console.error('Error fetching document status:', error);
        throw error;
      }
      
      if (!data) {
        console.warn('No document found with ID:', documentId);
        return;
      }
      
      console.log('Current status from fetch:', data.status);
      handleStatusUpdate({
        status: data.status,
        error_message: data.error_message
      });
    } catch (err) {
      console.error('Error in fetchDocumentStatus:', err);
      setError(err.message);
      
      // If there's an error, try to update the UI to reflect this
      setNotification({
        type: 'error',
        message: '❌ Error checking document status. Please refresh the page.'
      });
    }
  }, [documentId, handleStatusUpdate]);

  // Set up polling
  useEffect(() => {
    if (!documentId) return;

    // Don't start polling if already in terminal state
    if (status === 'completed' || status === 'failed') {
      console.log('Skipping polling start - already in terminal state:', status);
      return;
    }

    // Initial fetch
    console.log('Starting polling for document:', documentId);
    fetchDocumentStatus();

    // Set up polling
    pollingRef.current = setInterval(fetchDocumentStatus, 3000);
    console.log('Polling started');

    // Clean up
    return () => {
      console.log('Cleaning up polling');
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [documentId, fetchDocumentStatus, status]);

  // Set up realtime subscription (will use WebSocket if available)
  useEffect(() => {
    if (!documentId) return;
    
    console.log('Setting up realtime subscription for document:', documentId);
    
    const channel = supabase
      .channel(`document-${documentId}`)
      .on('postgres_changes', {
        event: '*',
        schema: 'public',
        table: 'documents',
        filter: `id=eq.${documentId}`
      }, (payload) => {
        console.log('Realtime update received:', payload);
        if (payload.eventType === 'UPDATE' && payload.new) {
          handleStatusUpdate({
            status: payload.new.status,
            error_message: payload.new.error_message
          });
        }
      })
      .subscribe(status => {
        console.log('Subscription status:', status);
        if (status === 'CHANNEL_ERROR') {
          console.error('Error with realtime subscription');
          setNotification({
            type: 'error',
            message: '❌ Error connecting to realtime updates. Some features may not work.'
          });
        } else if (status === 'SUBSCRIBED') {
          console.log('Successfully subscribed to document updates');
        }
      });
    
    channelRef.current = channel;
    
    // Clean up on unmount
    return () => {
      if (channelRef.current) {
        console.log('Unsubscribing from realtime updates');
        channelRef.current.unsubscribe();
        channelRef.current = null;
      }
    };
  }, [documentId]);

  // Clear notification after a delay
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => {
        setNotification(null);
      }, 10000); // Clear after 10 seconds

      return () => clearTimeout(timer);
    }
  }, [notification]);

  return { 
    status, 
    error, 
    notification, 
    lastUpdated,
    clearNotification: () => setNotification(null) 
  };
}
