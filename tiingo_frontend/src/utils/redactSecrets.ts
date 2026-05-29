const SECRET_QUERY_PATTERN = /(api_key|apikey|token|secret|password)=[^&\s"']+/gi;

export function redactSecretsInText(text: string): string {
  return text.replace(SECRET_QUERY_PATTERN, '$1=[REDACTED]');
}

export function redactJobPayload(value: unknown): unknown {
  if (value == null) {
    return value;
  }
  if (typeof value === 'string') {
    return redactSecretsInText(value);
  }
  if (Array.isArray(value)) {
    return value.map((item) => redactJobPayload(item));
  }
  if (typeof value === 'object') {
    const record = value as Record<string, unknown>;
    const next: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(record)) {
      next[key] = redactJobPayload(item);
    }
    return next;
  }
  return value;
}

export function formatRedactedJobJson(value: unknown): string {
  return JSON.stringify(redactJobPayload(value), null, 2);
}
