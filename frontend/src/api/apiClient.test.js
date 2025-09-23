import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { uploadPdfFile, uploadPdfLink } from './apiClient';

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

describe('apiClient', () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('uploads file via multipart to /upload', async () => {
    const mockResponse = { document_id: '123', status: 'pending_storage' };
    fetch.mockResolvedValueOnce(new Response(JSON.stringify(mockResponse), { status: 200 }));

    const blob = new File([new Uint8Array([1, 2, 3])], 'test.pdf', { type: 'application/pdf' });
    const res = await uploadPdfFile(blob);
    expect(res.document_id).toBe('123');

    const call = fetch.mock.calls[0];
    expect(call[0]).toBe(`${BASE}/api/v1/upload`);
    expect(call[1].method).toBe('POST');
    expect(call[1].body).toBeInstanceOf(FormData);
  });

  it('uploads link via JSON to /upload_link', async () => {
    const mockResponse = { document_id: '456', status: 'pending_storage' };
    fetch.mockResolvedValueOnce(new Response(JSON.stringify(mockResponse), { status: 200 }));

    const res = await uploadPdfLink('https://example.com/file.pdf');
    expect(res.document_id).toBe('456');

    const call = fetch.mock.calls[0];
    expect(call[0]).toBe(`${BASE}/api/v1/upload_link`);
    expect(call[1].method).toBe('POST');
    expect(call[1].headers['Content-Type']).toBe('application/json');
    expect(call[1].body).toBeTypeOf('string');
  });
});
