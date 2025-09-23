import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import PdfUpload from './PdfUpload';

describe('PdfUpload', () => {
  beforeEach(() => {
    // jsdom doesn't implement createObjectURL; stub if used later
    global.URL.createObjectURL = vi.fn();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('calls onUpload with File when submitting device upload', async () => {
    const onUpload = vi.fn();
    render(<PdfUpload onUpload={onUpload} isProcessing={false} />);

    const input = screen.getByLabelText(/Click to upload/i).parentElement.querySelector('input[type="file"]');
    const file = new File([new Uint8Array([1, 2, 3])], 'doc.pdf', { type: 'application/pdf' });
    await fireEvent.change(input, { target: { files: [file] } });

    const submit = screen.getByRole('button', { name: /Upload PDF/i });
    await fireEvent.click(submit);

    // Advance timers enough for simulated progress to hit callback
    await act(async () => {
      for (let i = 0; i < 10; i++) {
        vi.advanceTimersByTime(200);
      }
    });

    await waitFor(() => expect(onUpload).toHaveBeenCalled(), { timeout: 6000 });
    expect(onUpload.mock.calls[0][0]).toBeInstanceOf(File);
  });

  it('calls onUpload with URL when submitting url upload', async () => {
    const onUpload = vi.fn();
    render(<PdfUpload onUpload={onUpload} isProcessing={false} />);

    const urlTab = screen.getByRole('tab', { name: /From URL/i });
    await fireEvent.click(urlTab);

    const input = await screen.findByPlaceholderText(/Enter PDF URL/i);
    await fireEvent.change(input, { target: { value: 'https://example.com/a.pdf' } });

    const submit = screen.getByRole('button', { name: /Load from URL/i });
    await fireEvent.click(submit);

    await waitFor(() => expect(onUpload).toHaveBeenCalled(), { timeout: 3000 });
    expect(onUpload.mock.calls[0][0]).toBe('https://example.com/a.pdf');
  });
});
