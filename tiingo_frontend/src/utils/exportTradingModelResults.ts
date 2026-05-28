import html2canvas from 'html2canvas';

export const TRADING_MODEL_RESULTS_PRINT_ROOT_ID = 'trading-model-results-print-root';
export const TRADING_MODEL_RESULTS_PRINT_BODY_CLASS = 'trading-model-results-printing';

const EXPORT_BACKGROUND = '#0f172a';

export function sanitizeExportFilename(value: string): string {
  return value
    .trim()
    .replace(/[/\\?%*:|"<>]/g, '-')
    .replace(/\s+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^-+|-+$/g, '');
}

export function buildResultsExportFilename(
  symbol: string,
  modelName: string,
  ext: 'png' | 'pdf',
): string {
  const safeSymbol = sanitizeExportFilename(symbol) || 'asset';
  const safeName = sanitizeExportFilename(modelName) || 'model';
  return `${safeSymbol}_${safeName}_results.${ext}`;
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function exportElementAsPng(element: HTMLElement, filename: string): Promise<void> {
  const canvas = await html2canvas(element, {
    backgroundColor: EXPORT_BACKGROUND,
    scale: 2,
    useCORS: true,
    logging: false,
  });

  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob((value) => resolve(value), 'image/png');
  });

  if (!blob) {
    throw new Error('Failed to create PNG export.');
  }

  downloadBlob(blob, filename);
}

export function printElement(element: HTMLElement): void {
  if (!element.id) {
    element.id = TRADING_MODEL_RESULTS_PRINT_ROOT_ID;
  }

  const cleanup = () => {
    document.body.classList.remove(TRADING_MODEL_RESULTS_PRINT_BODY_CLASS);
    window.removeEventListener('afterprint', cleanup);
  };

  document.body.classList.add(TRADING_MODEL_RESULTS_PRINT_BODY_CLASS);
  window.addEventListener('afterprint', cleanup);
  window.print();
}
