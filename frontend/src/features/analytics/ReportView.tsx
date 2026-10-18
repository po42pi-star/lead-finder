import { useState } from "react";
import {
  AlertTriangle,
  Banknote,
  Briefcase,
  Check,
  CheckCircle2,
  ClipboardCopy,
  ClipboardList,
  Cog,
  FileSpreadsheet,
  Lightbulb,
  MapPin,
  MessageCircleQuestion,
  MessageSquare,
  ShieldAlert,
  Swords,
  UserRound,
  XCircle,
} from "lucide-react";
import { Badge, Button, Card } from "../../components/ui";
import { ScoreBadge } from "../../components/ScoreBadge";
import { api } from "../../lib/api";
import { cn, segmentLabel, shortCompanyName } from "../../lib/format";
import type { AnalyticsBlock, AnalyticsReport, Confidence, RecommendedQuestion } from "../../lib/types";

const BLOCK_ICONS: Record<string, React.ReactNode> = {
  financial: <Banknote className="size-4" />,
  tenders: <Briefcase className="size-4" />,
  technical: <Cog className="size-4" />,
  contacts: <UserRound className="size-4" />,
  risks: <ShieldAlert className="size-4" />,
};

type TabId = "questions" | "product_hypotheses" | "checklist" | "competitors";

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: "questions", label: "Вопросы для звонка", icon: <MessageCircleQuestion className="size-4" /> },
  { id: "product_hypotheses", label: "Что предложить", icon: <Lightbulb className="size-4" /> },
  { id: "checklist", label: "Чек-лист", icon: <ClipboardList className="size-4" /> },
  { id: "competitors", label: "Конкуренты", icon: <Swords className="size-4" /> },
];

interface ReportViewProps {
  report: AnalyticsReport;
  inWork: boolean;
  onInWork: () => void;
  onAsk: () => void;
}

export function ReportView({ report, inWork, onInWork, onAsk }: ReportViewProps) {
  const [tab, setTab] = useState<TabId>("questions");

  return (
    <div className="space-y-5 animate-fade-in">
      <Card className="flex flex-wrap items-center gap-5 p-5">
        <ScoreBadge score={report.score} size="lg" />
        <div className="min-w-0 flex-1">
          <h2 className="text-xl font-semibold text-slate-900">{shortCompanyName(report.company_name)}</h2>
          <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-slate-500">
            <span className="inline-flex items-center gap-1">
              <MapPin className="size-3.5" />
              {report.region || "Регион не указан"}
            </span>
            <Badge tone="brand">{segmentLabel(report.segment)}</Badge>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" icon={<MessageSquare className="size-3.5" />} onClick={onAsk}>
            Спросить ассистента
          </Button>
          <Button
            size="sm"
            icon={<FileSpreadsheet className="size-3.5" />}
            onClick={() => api.exportAnalytics([report.report_id], "xlsx")}
          >
            Excel
          </Button>
          <Button
            size="sm"
            variant={inWork ? "secondary" : "primary"}
            disabled={inWork}
            icon={inWork ? <Check className="size-3.5" /> : undefined}
            onClick={onInWork}
          >
            {inWork ? "В работе" : "Взять в работу"}
          </Button>
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Object.entries(report.mandatory).map(([key, block]) => (
          <BlockCard key={key} icon={BLOCK_ICONS[key]} block={block} />
        ))}
      </div>

      <Card>
        <div className="flex gap-1 overflow-x-auto border-b border-slate-200 px-3">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={cn(
                "-mb-px inline-flex items-center gap-1.5 whitespace-nowrap border-b-2 px-3 py-3 text-sm font-medium transition-colors",
                tab === t.id
                  ? "border-brand-600 text-brand-700"
                  : "border-transparent text-slate-500 hover:text-slate-900",
              )}
            >
              {t.icon}
              {t.label}
              {t.id === "questions" && (
                <span className="rounded-full bg-slate-100 px-1.5 text-xs text-slate-600">
                  {report.questions.length}
                </span>
              )}
            </button>
          ))}
        </div>
        <div className="p-5">
          {tab === "questions" ? (
            <QuestionList questions={report.questions} />
          ) : (
            <ItemList block={report.optional[tab] as AnalyticsBlock | undefined} />
          )}
        </div>
      </Card>
    </div>
  );
}

function ConfidenceIcon({ level }: { level: Confidence }) {
  if (level === "ok") return <CheckCircle2 className="size-4 shrink-0 text-emerald-500" />;
  if (level === "warning") return <AlertTriangle className="size-4 shrink-0 text-amber-500" />;
  return <XCircle className="size-4 shrink-0 text-slate-300" />;
}

function BlockCard({ icon, block }: { icon?: React.ReactNode; block: AnalyticsBlock }) {
  return (
    <Card className="p-4">
      <div className="mb-3 flex items-center gap-2">
        <span className="flex size-7 items-center justify-center rounded-lg bg-slate-100 text-slate-600">{icon}</span>
        <h3 className="text-sm font-semibold text-slate-900">{block.title}</h3>
      </div>
      {block.summary && <p className="mb-2.5 text-sm font-medium text-slate-700">{block.summary.replace(/^❌\s*/, "")}</p>}
      <ul className="space-y-2">
        {block.items.map((item, i) => (
          <li key={i} className="flex gap-2 text-xs text-slate-600">
            <ConfidenceIcon level={item.confidence} />
            <span>{item.text.replace(/^[✅⚠️❌]\s*/u, "")}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function ItemList({ block }: { block?: AnalyticsBlock }) {
  if (!block?.items?.length) return <p className="text-sm text-slate-500">Данных пока нет</p>;
  return (
    <ul className="space-y-2.5">
      {block.items.map((item, i) => (
        <li key={i} className="flex gap-2.5 text-sm text-slate-700">
          <ConfidenceIcon level={item.confidence} />
          {item.text.replace(/^[•\s]+/, "")}
        </li>
      ))}
    </ul>
  );
}

function QuestionList({ questions }: { questions: RecommendedQuestion[] }) {
  const [used, setUsed] = useState<Set<string>>(
    () => new Set(questions.filter((q) => q.used_in_call).map((q) => q.question_id)),
  );
  const [copied, setCopied] = useState(false);

  async function toggle(id: string) {
    const next = !used.has(id);
    setUsed((prev) => {
      const s = new Set(prev);
      if (next) s.add(id);
      else s.delete(id);
      return s;
    });
    await api.markQuestionUsed(id, next).catch(() => undefined);
  }

  function copyAll() {
    navigator.clipboard.writeText(questions.map((q, i) => `${i + 1}. ${q.text}`).join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs text-slate-500">
          Отмечайте вопросы, которые задали на звонке — это улучшает подбор для следующих лидов
        </p>
        <Button
          size="sm"
          variant="ghost"
          icon={copied ? <Check className="size-3.5" /> : <ClipboardCopy className="size-3.5" />}
          onClick={copyAll}
        >
          {copied ? "Скопировано" : "Скопировать все"}
        </Button>
      </div>
      <ol className="divide-y divide-slate-100">
        {questions.map((q, i) => {
          const isUsed = used.has(q.question_id);
          return (
            <li key={q.question_id}>
              <button
                type="button"
                onClick={() => toggle(q.question_id)}
                className="group flex w-full items-start gap-3 py-2.5 text-left"
              >
                <span
                  className={cn(
                    "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-md border text-[10px] font-semibold transition-colors",
                    isUsed
                      ? "border-emerald-500 bg-emerald-500 text-white"
                      : "border-slate-300 text-slate-400 group-hover:border-slate-400",
                  )}
                >
                  {isUsed ? <Check className="size-3" /> : i + 1}
                </span>
                <span className={cn("flex-1 text-sm", isUsed ? "text-slate-400 line-through" : "text-slate-800")}>
                  {q.text}
                </span>
                {q.methodology_tag && (
                  <Badge className="hidden sm:inline-flex">{q.methodology_tag.split("_")[0]}</Badge>
                )}
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
