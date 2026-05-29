import { describe, expect, it } from 'vitest';
import { formatRedactedJobJson, redactSecretsInText } from '../utils/redactSecrets';

describe('redactSecrets', () => {
  it('redacts api_key query params in text', () => {
    const raw = 'error at https://api.example.com?api_key=secret123&file_type=json';
    expect(redactSecretsInText(raw)).not.toContain('secret123');
    expect(redactSecretsInText(raw)).toContain('api_key=[REDACTED]');
  });

  it('redacts nested job result strings', () => {
    const json = formatRedactedJobJson({
      T10Y2Y: { status: 'error', error: 'failed api_key=leaked' },
    });
    expect(json).not.toContain('leaked');
    expect(json).toContain('api_key=[REDACTED]');
  });
});
