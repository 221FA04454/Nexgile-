export function parseApiError(data, status) {
  const message = data?.error?.message || data?.detail || data?.message || `Request failed (${status})`;
  const error = new Error(message);
  error.status = status;
  error.code = data?.error?.code || (status === 401 ? "UNAUTHORIZED" : status === 403 ? "FORBIDDEN" : "HTTP_ERROR");
  error.requestId = data?.error?.request_id;
  return error;
}
