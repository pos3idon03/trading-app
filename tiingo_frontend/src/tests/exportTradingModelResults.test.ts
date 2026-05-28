import { describe, expect, it } from 'vitest';
import {
  buildResultsExportFilename,
  sanitizeExportFilename,
} from '../utils/exportTradingModelResults';

describe('sanitizeExportFilename', () => {
  it('replaces unsafe characters and collapses whitespace', () => {
    expect(sanitizeExportFilename(' AAPL/GB model ')).toBe('AAPL-GB_model');
  });

  it('strips quotes and pipes', () => {
    expect(sanitizeExportFilename('foo|bar"bazz')).toBe('foo-bar-bazz');
  });

  it('returns empty string for whitespace-only input', () => {
    expect(sanitizeExportFilename('   ')).toBe('');
  });
});

describe('buildResultsExportFilename', () => {
  it('builds png filename from symbol and model name', () => {
    expect(buildResultsExportFilename('AAPL', 'AAPL GB full features', 'png')).toBe(
      'AAPL_AAPL_GB_full_features_results.png',
    );
  });

  it('falls back when symbol and name sanitize to empty', () => {
    expect(buildResultsExportFilename('///', '???', 'png')).toBe('asset_model_results.png');
  });

  it('supports pdf extension for print workflows', () => {
    expect(buildResultsExportFilename('MSFT', 'MSFT model', 'pdf')).toBe(
      'MSFT_MSFT_model_results.pdf',
    );
  });
});
