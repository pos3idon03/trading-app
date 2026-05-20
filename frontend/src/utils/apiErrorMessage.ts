type ValidationErrorItem = {
  loc?: (string | number)[];
  msg?: string;
};

function fieldFromLoc(loc: (string | number)[] | undefined): string | null {
  if (!loc?.length) return null;
  const parts = loc.filter((part): part is string => part !== 'body' && typeof part === 'string');
  return parts.length > 0 ? parts[parts.length - 1] : null;
}

function normalizeValidationMessage(msg: string): string {
  return msg.replace(/^Value error,\s*/i, '');
}

function formatValidationItem(item: ValidationErrorItem): string {
  const msg = item.msg ? normalizeValidationMessage(item.msg) : 'Validation failed';
  const field = fieldFromLoc(item.loc);
  return field ? `${field}: ${msg}` : msg;
}

/** Turn FastAPI `detail` payloads into a user-facing error string. */
export function formatApiErrorDetail(detail: unknown): string | null {
  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => formatValidationItem(item as ValidationErrorItem))
      .filter(Boolean);
    return messages.length > 0 ? messages.join('; ') : null;
  }
  if (detail && typeof detail === 'object' && 'msg' in detail) {
    return formatValidationItem(detail as ValidationErrorItem);
  }
  return null;
}

export function getApiErrorMessage(data: unknown, fallback = 'Unknown error'): string {
  if (data && typeof data === 'object' && 'detail' in data) {
    const formatted = formatApiErrorDetail((data as { detail: unknown }).detail);
    if (formatted) return formatted;
  }
  return fallback;
}
