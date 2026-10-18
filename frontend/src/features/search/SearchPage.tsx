import { useEffect, useMemo, useState } from "react";
import { FileSpreadsheet, FileText, Info, SearchX, Sparkles, Telescope, X } from "lucide-react";
import { Button, EmptyState, ErrorBanner, Select, Skeleton } from "../../components/ui";
import { api } from "../../lib/api";
import { isDemoLead, pluralize } from "../../lib/format";
import type {
  ExtraFields,
  FiltersMeta,
  GroupOption,
  Lead,
  LeadGroup,
  SearchFilters,
  SearchResponse,
  SortOption,
} from "../../lib/types";
import { FiltersPanel, PRESETS } from "./FiltersPanel";
import { LeadCard } from "./LeadCard";

const MAX_ANALYTICS = 5;

const EMPTY_EXTRA: ExtraFields = {
  geography: "",
  keywords: "",
  adjacent_industries: "",
  exclude_keywords: "",
  min_turnover_mln: "",
  activity_period: "",
  project_types: "",
  technical_requirements: "",
  contact_channels: "",
  search_comment: "",
};

const EMPTY_FILTERS: SearchFilters = { checkboxes: [], extra: EMPTY_EXTRA };

interface SearchPageProps {
  onAnalytics: (leads: Lead[]) => void;
  onAsk: (lead: Lead) => void;
}

export function SearchPage({ onAnalytics, onAsk }: SearchPageProps) {
  const [meta, setMeta] = useState<FiltersMeta | null>(null);
  const [filters, setFilters] = useState<SearchFilters>(EMPTY_FILTERS);
  const [sortBy, setSortBy] = useState<SortOption>("score_desc");
  const [groupBy, setGroupBy] = useState<GroupOption>("none");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selected, setSelected] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .filtersMeta()
      .then(setMeta)
      .catch(() => setError("Не удалось загрузить фильтры. Бэкенд запущен?"));
  }, []);

  async function runSearch(nextFilters = filters, nextSort = sortBy, nextGroup = groupBy) {
    setLoading(true);
    setError(null);
    setSelected([]);
    try {
      const response = await api.runSearch(nextFilters, nextSort, nextGroup);
      setResult(response);
      setLeads(response.leads);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Поиск не удался");
    } finally {
      setLoading(false);
    }
  }

  async function loadMore() {
    if (!result) return;
    setLoadingMore(true);
    try {
      const response = await api.loadMore(
        result.session_id,
        leads.map((l) => l.lead_id),
        sortBy,
        groupBy,
      );
      setLeads((prev) => [...prev, ...response.leads]);
      setResult({ ...response, shown_count: leads.length + response.leads.length });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось догрузить результаты");
    } finally {
      setLoadingMore(false);
    }
  }

  function applyPreset(preset: (typeof PRESETS)[number]) {
    const next = { checkboxes: preset.checkboxes, extra: { ...EMPTY_EXTRA, ...preset.filters } };
    setFilters(next);
    runSearch(next);
  }

  async function changeView(nextSort: SortOption, nextGroup: GroupOption) {
    setSortBy(nextSort);
    setGroupBy(nextGroup);
    if (!result) return;
    // Пересортировка по уже сохранённой выдаче, без повторного опроса реестров
    setLoading(true);
    try {
      const response = await api.loadMore(result.session_id, [], nextSort, nextGroup);
      setResult({ ...response, session_id: result.session_id });
      setLeads(response.leads);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось пересортировать");
    } finally {
      setLoading(false);
    }
  }

  const groups: LeadGroup[] | null = useMemo(() => {
    if (groupBy === "none" || !result?.groups) return null;
    const ids = new Set(leads.map((l) => l.lead_id));
    return result.groups
      .map((g) => ({ ...g, leads: g.leads.filter((l) => ids.has(l.lead_id)) }))
      .filter((g) => g.leads.length > 0);
  }, [groupBy, result, leads]);

  const hasDemo = leads.some((l) => isDemoLead(l.source));
  const selectedIds = new Set(selected.map((l) => l.lead_id));

  const toggle = (lead: Lead, value: boolean) =>
    setSelected((prev) => (value ? [...prev, lead] : prev.filter((l) => l.lead_id !== lead.lead_id)));

  const renderCard = (lead: Lead) => (
    <LeadCard
      key={lead.lead_id}
      lead={lead}
      selected={selectedIds.has(lead.lead_id)}
      selectionDisabled={selected.length >= MAX_ANALYTICS}
      onToggle={(v) => toggle(lead, v)}
      onAnalytics={() => onAnalytics([lead])}
      onAsk={() => onAsk(lead)}
    />
  );

  return (
    <div className="flex h-full min-h-0">
      <aside className="w-[340px] shrink-0 border-r border-slate-200 bg-white">
        <FiltersPanel
          meta={meta}
          filters={filters}
          loading={loading}
          onChange={setFilters}
          onSubmit={() => runSearch()}
          onReset={() => setFilters(EMPTY_FILTERS)}
        />
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-slate-200 bg-white/80 px-6 py-3 backdrop-blur">
          <h1 className="text-lg font-semibold text-slate-900">Поиск потенциальных клиентов</h1>
          <div className="mt-1 flex min-h-8 flex-wrap items-center gap-2">
            <p className="mr-auto text-xs text-slate-500">
              {result
                ? `Показано ${result.shown_count} из ${result.total_count} ${pluralize(result.total_count, "компании", "компаний", "компаний")}`
                : "ФНС · DaData · 2ГИС · Госзакупки · АВОК"}
            </p>
            {result && (
              <>
                <Select
                  aria-label="Сортировка"
                  value={sortBy}
                  onChange={(e) => changeView(e.target.value as SortOption, groupBy)}
                >
                  {meta?.sort_options.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.label}
                    </option>
                  ))}
                </Select>
                <Select
                  aria-label="Группировка"
                  value={groupBy}
                  onChange={(e) => changeView(sortBy, e.target.value as GroupOption)}
                >
                  {meta?.group_options.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.label}
                    </option>
                  ))}
                </Select>
                <Button
                  size="sm"
                  icon={<FileText className="size-3.5" />}
                  onClick={() => api.exportLeads(result.session_id, selected.length ? [...selectedIds] : null, "csv")}
                >
                  CSV
                </Button>
                <Button
                  size="sm"
                  icon={<FileSpreadsheet className="size-3.5" />}
                  onClick={() => api.exportLeads(result.session_id, selected.length ? [...selectedIds] : null, "xlsx")}
                >
                  Excel
                </Button>
              </>
            )}
          </div>
        </header>

        <div className="relative flex-1 overflow-y-auto">
          <div className="mx-auto max-w-4xl space-y-3 px-6 pt-5 pb-28">
            {error && <ErrorBanner message={error} onRetry={() => runSearch()} />}

            {hasDemo && !loading && (
              <div className="flex items-start gap-2.5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                <Info className="mt-0.5 size-4 shrink-0" />
                <span>
                  Реальные источники ничего не нашли по этим фильтрам — показаны <b>демонстрационные компании</b>.
                  Попробуйте упростить запрос.
                </span>
              </div>
            )}

            {loading && <ResultsSkeleton />}

            {!loading && !result && !error && (
              <EmptyState
                icon={<Telescope className="size-6" />}
                title="С чего начнём?"
                description="Задайте регион и вид деятельности слева или выберите готовый сценарий. Система соберёт компании из открытых реестров и оценит каждую по 0–100."
                action={
                  <div className="flex flex-wrap justify-center gap-2">
                    {PRESETS.map((preset) => (
                      <Button key={preset.label} size="sm" onClick={() => applyPreset(preset)}>
                        {preset.label}
                      </Button>
                    ))}
                  </div>
                }
              />
            )}

            {!loading && result && leads.length === 0 && (
              <EmptyState
                icon={<SearchX className="size-6" />}
                title="Ничего не найдено"
                description="Попробуйте убрать часть признаков или расширить регион."
              />
            )}

            {!loading &&
              (groups
                ? groups.map((group) => (
                    <div key={group.key} className="space-y-3">
                      <h2 className="sticky top-0 z-10 -mx-1 bg-slate-50/95 px-1 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500 backdrop-blur">
                        {group.title} · {group.leads.length}
                      </h2>
                      {group.leads.map(renderCard)}
                    </div>
                  ))
                : leads.map(renderCard))}

            {!loading && result?.has_more && (
              <div className="flex justify-center pt-2">
                <Button loading={loadingMore} onClick={loadMore}>
                  Показать ещё
                </Button>
              </div>
            )}
          </div>

          {selected.length > 0 && (
            <div className="sticky bottom-5 z-20 flex justify-center px-6 pb-5 animate-fade-in">
              <div className="flex items-center gap-3 rounded-xl bg-slate-900 py-2 pl-4 pr-2 text-sm text-white shadow-lg">
                <span>
                  Выбрано <b>{selected.length}</b> из {MAX_ANALYTICS}
                </span>
                <Button
                  size="sm"
                  variant="primary"
                  icon={<Sparkles className="size-3.5" />}
                  onClick={() => onAnalytics(selected)}
                >
                  Аналитика по выбранным
                </Button>
                <button
                  type="button"
                  aria-label="Снять выбор"
                  className="rounded-md p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
                  onClick={() => setSelected([])}
                >
                  <X className="size-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function ResultsSkeleton() {
  return (
    <>
      <p className="text-center text-xs text-slate-500">
        Опрашиваем реестры и оцениваем компании — обычно 10–20 секунд
      </p>
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex gap-4 rounded-xl border border-slate-200 bg-white p-4">
          <div className="flex-1 space-y-2.5">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-3 w-3/4" />
            <Skeleton className="h-3 w-1/3" />
            <div className="flex gap-2 pt-1">
              <Skeleton className="h-8 w-24" />
              <Skeleton className="h-8 w-40" />
            </div>
          </div>
          <Skeleton className="size-12 rounded-full" />
        </div>
      ))}
    </>
  );
}
