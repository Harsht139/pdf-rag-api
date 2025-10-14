import { createClient } from '@supabase/supabase-js';

// Get environment variables
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://lkmmjxsasuegjjbaenne.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxrbW1qeHNhc3VlZ2pqYmFlbm5lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgyNzMzMTcsImV4cCI6MjA3Mzg0OTMxN30.PPJaj8M-G3p6XNisO1RDqCQ7BwU9PfgozDASITtNi2Y';

// Debug log
console.log('Initializing Supabase with URL:', supabaseUrl);

// Initialize Supabase client with minimal configuration
const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false,
    detectSessionInUrl: false
  }
});

// Add WebSocket error handling
const _supabase = supabase;
Object.defineProperty(window, 'supabase', {
  get() {
    return _supabase;
  },
  set() {}
});

// Set up auth state change listener
supabase.auth.onAuthStateChange((event, session) => {
  console.log('Supabase auth state changed:', event, session);
});

// Test the connection
async function testConnection() {
  try {
    const { data, error } = await supabase.from('documents').select('*').limit(1);
    if (error) throw error;
    console.log('Supabase connection test successful');
  } catch (error) {
    console.error('Supabase connection test failed:', error);
  }
}

testConnection();

export { supabase };
