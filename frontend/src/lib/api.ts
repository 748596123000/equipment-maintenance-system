import axios from "axios";
import { useAuthStore } from "@/stores/auth-store";

/**
 * Get CSRF token from meta tag
 * The token should be set by the backend when rendering the page
 */
export function getCsrfToken(): string | null {
  const metaTag = document.querySelector('meta[name="csrf-token"]');
  return metaTag?.getAttribute('content') || null;
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  timeout: 60000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // Add CSRF token to headers if available
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      config.headers['X-CSRF-Token'] = csrfToken;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    const d = response.data;
    if (d && typeof d === "object" && "code" in d && "data" in d) {
      (response as any)._rawCode = d.code;
      (response as any)._rawMessage = d.message;
      response.data = d.data;
    }
    return response;
  },
  (error) => {
    if (error.response) {
      const d = error.response.data;
      if (d && typeof d === "object" && "code" in d && "data" in d) {
        error.response.data = {
          ...d.data,
          _code: d.code,
          _message: d.message,
          detail: d.message || d.detail,
        };
      }
    }
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      if (!window.location.pathname.includes('/login')) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export async function downloadFile(url: string, filename: string): Promise<void> {
  const token = useAuthStore.getState().token;
  const fullUrl = url.startsWith('/') ? url : `/upload/${url}/download`;

  const response = await axios.get(fullUrl, {
    responseType: 'blob',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    baseURL: api.defaults.baseURL,
  });

  const blob = new Blob([response.data]);
  const downloadUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = downloadUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(downloadUrl);
}

export { api };
