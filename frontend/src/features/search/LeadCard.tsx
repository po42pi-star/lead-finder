import { useState } from "react";
import {
  Building2,
  ChevronDown,
  Globe,
  Mail,
  MapPin,
  MessageSquare,
  Phone,
  Sparkles,
  UserRound,
  Users,
} from "lucide-react";
import { Badge, Button, Checkbox } from "../../components/ui";
import { ScoreBadge } from "../../components/ScoreBadge";
import { cn, isDemoLead, segmentLabel, shortCompanyName, sourceLabels } from "../../lib/format";
import type { Lead } from "../../lib/types";

interface LeadCardProps {
  lead: Lead;
  selected: boolean;
  selectionDisabled: boolean;
  onToggle: (selected: boolean) => void;
  onAnalytics: () => void;
  onAsk: () => void;
}

export function LeadCard({
  lead,
  selected,
  selectionDisabled,
  onToggle,
  onAnalytics,
  onAsk,
}: LeadCardProps) {
  const [expanded, setExpanded] = useState(false);
  const demo = isDemoLead(lead.source);

  return (
    <article
      className={cn(
        "group rounded-xl border bg-white p-4 shadow-xs transition-all animate-fade-in",
        selected ? "border-brand-500 ring-3 ring-brand-100" : "border-slate-200 hover:border-slate-300 hover:shadow-sm",
      )}
    >
      <div className="flex gap-4">
        <div className="pt-1">
          <Checkbox
            label={`Выбрать ${lead.company_name}`}
            checked={selected}
            onChange={(value) => (!selectionDisabled || !value) && onToggle(value)}
          />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate text-[15px] font-semibold text-slate-900" title={lead.company_name}>
              {shortCompanyName(lead.company_name)}
            </h3>
            {demo && <Badge tone="amber">Демо-данные</Badge>}
          </div>

          <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
            <Meta icon={<MapPin className="size-3.5" />}>{lead.region || "Регион не указан"}</Meta>
            <Meta icon={<Building2 className="size-3.5" />}>{segmentLabel(lead.segment)}</Meta>
            {lead.inn && <Meta>ИНН {lead.inn}</Meta>}
            {lead.employees != null && (
              <Meta icon={<Users className="size-3.5" />}>{lead.employees} сотр.</Meta>
            )}
            {lead.turnover_mln != null && <Meta>Оборот {lead.turnover_mln} млн ₽</Meta>}
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs">
            {lead.contact_name && (
              <Meta icon={<UserRound className="size-3.5" />} strong>
                {lead.contact_name}
              </Meta>
            )}
            {lead.contact_phone && (
              <a href={`tel:${lead.contact_phone}`} className="hover:text-brand-600">
                <Meta icon={<Phone className="size-3.5" />}>{lead.contact_phone}</Meta>
              </a>
            )}
            {lead.contact_email && (
              <a href={`mailto:${lead.contact_email}`} className="hover:text-brand-600">
                <Meta icon={<Mail className="size-3.5" />}>{lead.contact_email}</Meta>
              </a>
            )}
            {lead.website && (
              <a href={lead.website} target="_blank" rel="noreferrer" className="hover:text-brand-600">
                <Meta icon={<Globe className="size-3.5" />}>{lead.website.replace(/^https?:\/\//, "")}</Meta>
              </a>
            )}
            {!lead.contact_name && !lead.contact_phone && !lead.contact_email && (
              <span className="text-slate-400">Контакты ЛПР не найдены</span>
            )}
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button size="sm" variant="primary" icon={<Sparkles className="size-3.5" />} onClick={onAnalytics}>
              Аналитика
            </Button>
            <Button size="sm" icon={<MessageSquare className="size-3.5" />} onClick={onAsk}>
              Спросить ассистента
            </Button>
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-900"
            >
              Почему {lead.score} баллов
              <ChevronDown className={cn("size-3.5 transition-transform", expanded && "rotate-180")} />
            </button>
          </div>

          {expanded && (
            <div className="mt-3 rounded-lg bg-slate-50 p-3 animate-fade-in">
              {lead.score_breakdown.length === 0 ? (
                <p className="text-xs text-slate-500">Ни один критерий скоринга не подтвердился</p>
              ) : (
                <ul className="space-y-1.5">
                  {lead.score_breakdown.map((item) => (
                    <li key={item.reason} className="flex items-center justify-between gap-3 text-xs">
                      <span className="text-slate-700">{item.reason}</span>
                      <span
                        className={cn(
                          "font-semibold tabular-nums",
                          item.delta >= 0 ? "text-emerald-600" : "text-red-600",
                        )}
                      >
                        {item.delta > 0 ? "+" : ""}
                        {item.delta}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-2 border-t border-slate-200 pt-2 text-[11px] text-slate-400">
                Источники: {sourceLabels(lead.source).join(", ")}
              </p>
            </div>
          )}
        </div>

        <ScoreBadge score={lead.score} />
      </div>
    </article>
  );
}

function Meta({
  icon,
  strong,
  children,
}: {
  icon?: React.ReactNode;
  strong?: boolean;
  children: React.ReactNode;
}) {
  return (
    <span className={cn("inline-flex items-center gap-1", strong ? "font-medium text-slate-700" : "")}>
      {icon && <span className="text-slate-400">{icon}</span>}
      {children}
    </span>
  );
}
