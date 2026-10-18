import { useEffect, useState } from "react";
import { BarChart3, Bot, Search, Wind } from "lucide-react";
import { api } from "./lib/api";
import { cn } from "./lib/format";
import type { AnalyticsReport, ChatContext, Lead } from "./lib/types";
import { SearchPage } from "./features/search/SearchPage";
import { AnalyticsPage } from "./features/analytics/AnalyticsPage";
import { ChatPanel } from "./features/chat/ChatPanel";

type Page = "search" | "analytics";

const NAV: { id: Page; label: string; icon: React.ReactNode }[] = [
  { id: "search", label: "Поиск", icon: <Search className="size-4" /> },
  { id: "analytics", label: "Аналитика", icon: <BarChart3 className="size-4" /> },
];

export default function App() {
  const [page, setPage] = useState<Page>("search");
  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const [reports, setReports] = useState<AnalyticsReport[]>([]);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatContext, setChatContext] = useState<ChatContext>({ page: "search" });

  useEffect(() => {
    api
      .health()
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false));
  }, []);

  useEffect(() => {
    setChatContext((c) => ({ ...c, page }));
  }, [page]);

  async function runAnalytics(leads: Lead[]) {
    setPage("analytics");
    setAnalyticsLoading(true);
    setAnalyticsError(null);
    try {
      const response = await api.runAnalytics(leads.map((l) => l.lead_id));
      setReports(response.reports);
    } catch (e) {
      setAnalyticsError(e instanceof Error ? e.message : "Аналитика недоступна");
    } finally {
      setAnalyticsLoading(false);
    }
  }

  function askAbout(target: { lead_id: string; segment: string; score: number; company_name: string }) {
    setChatContext({
      lead_id: target.lead_id,
      segment: target.segment,
      score: target.score,
      company_name: target.company_name,
      page,
    });
    setChatOpen(true);
  }

  return (
    <div className="flex h-full">
      <nav className="flex w-56 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="flex items-center gap-2.5 px-5 py-5">
          <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-sm">
            <Wind className="size-5" />
          </div>
          <div>
            <div className="text-sm font-semibold leading-tight text-slate-900">Lead Finder</div>
            <div className="text-[11px] text-slate-500">для НЕВАТОМ</div>
          </div>
        </div>

        <div className="flex-1 space-y-0.5 px-3">
          {NAV.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setPage(item.id)}
              className={cn(
                "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                page === item.id
                  ? "bg-brand-50 text-brand-700"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
              )}
            >
              {item.icon}
              {item.label}
              {item.id === "analytics" && reports.length > 0 && (
                <span className="ml-auto rounded-full bg-brand-600 px-1.5 text-[10px] text-white">
                  {reports.length}
                </span>
              )}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setChatOpen((v) => !v)}
            className={cn(
              "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              chatOpen ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
            )}
          >
            <Bot className="size-4" />
            Ассистент
          </button>
        </div>

        <div className="m-3 rounded-lg bg-slate-50 p-3 text-[11px] text-slate-500">
          <div className="flex items-center gap-1.5 font-medium text-slate-700">
            <span
              className={cn(
                "size-2 rounded-full",
                backendOk === null ? "bg-slate-300" : backendOk ? "bg-emerald-500" : "bg-red-500",
              )}
            />
            {backendOk === false ? "Сервер недоступен" : "Пилотная версия"}
          </div>
          <p className="mt-1">
            {backendOk === false
              ? "Запустите бэкенд: ./start.sh"
              : "База знаний сгенерирована по открытым данным"}
          </p>
        </div>
      </nav>

      <main className="min-w-0 flex-1">
        <div className={cn("h-full", page !== "search" && "hidden")}>
          <SearchPage onAnalytics={runAnalytics} onAsk={askAbout} />
        </div>
        <div className={cn("h-full", page !== "analytics" && "hidden")}>
          <AnalyticsPage
            reports={reports}
            loading={analyticsLoading}
            error={analyticsError}
            onGoSearch={() => setPage("search")}
            onAsk={askAbout}
          />
        </div>
      </main>

      {!chatOpen && (
        <button
          type="button"
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 z-30 flex items-center gap-2 rounded-full bg-slate-900 py-3 pl-4 pr-5 text-sm font-medium text-white shadow-lg transition-transform hover:scale-105"
        >
          <Bot className="size-4" />
          Ассистент
        </button>
      )}

      <ChatPanel
        open={chatOpen}
        context={chatContext}
        onClose={() => setChatOpen(false)}
        onClearContext={() => setChatContext({ page })}
      />
    </div>
  );
}
