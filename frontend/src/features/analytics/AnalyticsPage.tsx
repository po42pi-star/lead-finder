import { useState } from "react";
import { BarChart3, FileSpreadsheet, Search } from "lucide-react";
import { Button, EmptyState, ErrorBanner, Skeleton } from "../../components/ui";
import { ScoreBadge } from "../../components/ScoreBadge";
import { api } from "../../lib/api";
import { cn, shortCompanyName } from "../../lib/format";
import type { AnalyticsReport } from "../../lib/types";
import { ReportView } from "./ReportView";

interface AnalyticsPageProps {
  reports: AnalyticsReport[];
  loading: boolean;
  error: string | null;
  onGoSearch: () => void;
  onAsk: (report: AnalyticsReport) => void;
}

export function AnalyticsPage({ reports, loading, error, onGoSearch, onAsk }: AnalyticsPageProps) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const [inWork, setInWork] = useState<Set<string>>(new Set());

  const active = reports.find((r) => r.report_id === activeId) ?? reports[0];

  async function markInWork(report: AnalyticsReport) {
    await api.markInWork([report.lead_id]);
    setInWork((prev) => new Set(prev).add(report.lead_id));
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex items-center gap-3 border-b border-slate-200 bg-white/80 px-6 py-3 backdrop-blur">
        <div className="mr-auto">
          <h1 className="text-lg font-semibold text-slate-900">Аналитика и подготовка к звонку</h1>
          <p className="text-xs text-slate-500">
            Профиль компании, вопросы по SPIN/MEDDIC и что предложить — до 5 компаний за раз
          </p>
        </div>
        {reports.length > 1 && (
          <Button
            size="sm"
            icon={<FileSpreadsheet className="size-3.5" />}
            onClick={() => api.exportAnalytics(reports.map((r) => r.report_id), "xlsx")}
          >
            Выгрузить все в Excel
          </Button>
        )}
      </header>

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-6 pt-5 pb-28">
          {error && <ErrorBanner message={error} />}

          {loading && (
            <div className="space-y-4">
              <Skeleton className="h-24 w-full rounded-xl" />
              <div className="grid gap-4 md:grid-cols-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <Skeleton key={i} className="h-36 rounded-xl" />
                ))}
              </div>
            </div>
          )}

          {!loading && !error && reports.length === 0 && (
            <EmptyState
              icon={<BarChart3 className="size-6" />}
              title="Пока нет отчётов"
              description="Найдите компании на вкладке «Поиск» и нажмите «Аналитика» на карточке — или отметьте до 5 компаний и запустите анализ пачкой."
              action={
                <Button variant="primary" icon={<Search className="size-4" />} onClick={onGoSearch}>
                  Перейти к поиску
                </Button>
              }
            />
          )}

          {!loading && reports.length > 1 && (
            <div className="mb-5 flex gap-2 overflow-x-auto pb-1">
              {reports.map((r) => (
                <button
                  key={r.report_id}
                  type="button"
                  onClick={() => setActiveId(r.report_id)}
                  className={cn(
                    "flex shrink-0 items-center gap-3 rounded-xl border bg-white py-2 pl-2 pr-4 text-left transition-colors",
                    r.report_id === active?.report_id
                      ? "border-brand-500 ring-3 ring-brand-100"
                      : "border-slate-200 hover:border-slate-300",
                  )}
                >
                  <div className="scale-75">
                    <ScoreBadge score={r.score} />
                  </div>
                  <div>
                    <div className="max-w-48 truncate text-sm font-medium text-slate-900">
                      {shortCompanyName(r.company_name)}
                    </div>
                    <div className="text-xs text-slate-500">{r.region || "—"}</div>
                  </div>
                </button>
              ))}
            </div>
          )}

          {!loading && active && (
            <ReportView
              key={active.report_id}
              report={active}
              inWork={inWork.has(active.lead_id)}
              onInWork={() => markInWork(active)}
              onAsk={() => onAsk(active)}
            />
          )}
        </div>
      </div>
    </div>
  );
}
