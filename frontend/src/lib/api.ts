import type {
  AnalyticsReport,
  ChatContext,
  ChatMode,
  ChatResponse,
  FiltersMeta,
  GroupOption,
  SearchFilters,
  SearchResponse,
  SortOption,
} from "./types";

// Все запросы идут через прокси Vite (/api → http://127.0.0.1:8000), адрес сервера в коде не зашит
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";
const USER_ROLE = "rop";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Ошибка сервера (${response.status})`);
  }
  return response.json();
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(body) });
}

async function download(path: string, body: unknown, filename: string): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error("Не удалось выгрузить файл");
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export const api = {
  health: () => request<{ status: string }>("/health"),

  filtersMeta: () => request<FiltersMeta>("/search/filters"),

  runSearch: (filters: SearchFilters, sortBy: SortOption, groupBy: GroupOption) =>
    post<SearchResponse>("/search/run", {
      user_role: USER_ROLE,
      filters,
      sort_by: sortBy,
      group_by: groupBy,
    }),

  loadMore: (sessionId: string, excludeIds: string[], sortBy: SortOption, groupBy: GroupOption) =>
    post<SearchResponse>("/search/more", {
      session_id: sessionId,
      exclude_lead_ids: excludeIds,
      sort_by: sortBy,
      group_by: groupBy,
    }),

  exportLeads: (sessionId: string, leadIds: string[] | null, format: "csv" | "xlsx") =>
    download(
      "/search/export",
      { session_id: sessionId, lead_ids: leadIds, format },
      `leads.${format}`,
    ),

  runAnalytics: (leadIds: string[]) =>
    post<{ reports: AnalyticsReport[] }>("/analytics/run", {
      lead_ids: leadIds,
      user_role: USER_ROLE,
    }),

  markInWork: (leadIds: string[]) =>
    post<{ updated: number }>("/analytics/in-work", { lead_ids: leadIds }),

  markQuestionUsed: (questionId: string, used: boolean) =>
    post<{ ok: boolean }>(`/analytics/questions/${questionId}/used-in-call`, { used }),

  exportAnalytics: (reportIds: string[], format: "csv" | "xlsx") =>
    download("/analytics/export", { report_ids: reportIds, format }, `analytics.${format}`),

  chatSuggestions: async (mode: ChatMode, context: ChatContext): Promise<string[]> => {
    const params = new URLSearchParams({ mode, user_role: USER_ROLE });
    if (context.lead_id) params.set("lead_id", context.lead_id);
    if (context.segment) params.set("segment", context.segment);
    if (context.score != null) params.set("score", String(context.score));
    if (context.page) params.set("page", context.page);
    const body = await request<{ suggestions: string[] }>(`/chat/suggestions?${params}`);
    return body.suggestions;
  },

  chatFeedback: (interactionId: string, feedback: "positive" | "negative") =>
    post<{ ok: boolean }>("/chat/feedback", { interaction_id: interactionId, feedback }),

  clearChat: (sessionId: string) => post<{ ok: boolean }>("/chat/session/clear", { session_id: sessionId }),

  /** Потоковый ответ чата (Server-Sent Events): токены приходят по мере генерации */
  async streamChat(
    payload: { query: string; mode: ChatMode; session_id: string | null; context: ChatContext },
    onToken: (token: string) => void,
  ): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, user_role: USER_ROLE }),
    });
    if (!response.ok || !response.body) throw new Error("Ассистент недоступен");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";
      for (const event of events) {
        if (!event.startsWith("data: ")) continue;
        const data = JSON.parse(event.slice(6));
        if (data.error) throw new Error(data.error);
        if (data.done) return data.response as ChatResponse;
        if (data.token) onToken(data.token);
      }
    }
    throw new Error("Ответ прервался");
  },
};
