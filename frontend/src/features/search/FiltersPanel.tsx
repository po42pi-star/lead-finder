import { useState } from "react";
import { Check, ChevronDown, MapPin, RotateCcw, Search, Tag } from "lucide-react";
import { Button, Input, Skeleton } from "../../components/ui";
import { cn } from "../../lib/format";
import type { ExtraFields, FiltersMeta, SearchFilters } from "../../lib/types";

// Поля, вынесенные наверх панели; остальные дополнительные — под «Ещё параметры»
const PRIMARY_FIELDS: (keyof ExtraFields)[] = ["geography", "keywords"];

export const PRESETS: { label: string; filters: Partial<ExtraFields>; checkboxes: string[] }[] = [
  {
    label: "Монтажники вентиляции, Самара",
    filters: { geography: "Самарская область", keywords: "монтаж вентиляции" },
    checkboxes: ["vent_mount", "age_2y"],
  },
  {
    label: "Проектировщики ОВиК, Москва",
    filters: { geography: "Москва", keywords: "проектирование ОВиК" },
    checkboxes: ["ovik_design", "has_sro"],
  },
  {
    label: "Климатические системы, Урал",
    filters: { geography: "Свердловская область", keywords: "климатические системы" },
    checkboxes: ["vent_mount", "commercial_build"],
  },
];

interface FiltersPanelProps {
  meta: FiltersMeta | null;
  filters: SearchFilters;
  loading: boolean;
  onChange: (filters: SearchFilters) => void;
  onSubmit: () => void;
  onReset: () => void;
}

export function FiltersPanel({ meta, filters, loading, onChange, onSubmit, onReset }: FiltersPanelProps) {
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({ profile: true });
  const [showExtra, setShowExtra] = useState(false);

  const setExtra = (key: keyof ExtraFields, value: string) =>
    onChange({ ...filters, extra: { ...filters.extra, [key]: value } });

  const toggleCheckbox = (id: string) =>
    onChange({
      ...filters,
      checkboxes: filters.checkboxes.includes(id)
        ? filters.checkboxes.filter((c) => c !== id)
        : [...filters.checkboxes, id],
    });

  if (!meta) {
    return (
      <div className="space-y-3 p-5">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  const fieldMeta = Object.fromEntries(meta.extra_fields.map((f) => [f.id, f]));
  const secondaryFields = meta.extra_fields.filter((f) => !PRIMARY_FIELDS.includes(f.id));
  const filledSecondary = secondaryFields.filter((f) => filters.extra[f.id]?.trim()).length;

  return (
    <form
      className="flex h-full flex-col"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <div className="flex-1 space-y-5 overflow-y-auto p-5">
        <div className="space-y-3">
          <Field label="Регион" icon={<MapPin className="size-4" />}>
            <Input
              value={filters.extra.geography}
              placeholder={fieldMeta.geography?.placeholder}
              onChange={(e) => setExtra("geography", e.target.value)}
            />
          </Field>
          <Field label="Что ищем" icon={<Tag className="size-4" />}>
            <Input
              value={filters.extra.keywords}
              placeholder={fieldMeta.keywords?.placeholder}
              onChange={(e) => setExtra("keywords", e.target.value)}
            />
          </Field>
        </div>

        {meta.checkbox_groups.map((group) => {
          const selectedCount = group.items.filter((i) => filters.checkboxes.includes(i.id)).length;
          const open = openGroups[group.id] ?? false;
          return (
            <section key={group.id}>
              <button
                type="button"
                className="flex w-full items-center justify-between text-left"
                onClick={() => setOpenGroups((s) => ({ ...s, [group.id]: !open }))}
              >
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {group.title}
                  {selectedCount > 0 && (
                    <span className="ml-2 rounded-full bg-brand-600 px-1.5 py-px text-[10px] text-white">
                      {selectedCount}
                    </span>
                  )}
                </span>
                <ChevronDown className={cn("size-4 text-slate-400 transition-transform", open && "rotate-180")} />
              </button>
              {open && (
                <div className="mt-2.5 flex flex-wrap gap-1.5 animate-fade-in">
                  {group.items.map((item) => {
                    const active = filters.checkboxes.includes(item.id);
                    return (
                      <button
                        key={item.id}
                        type="button"
                        aria-pressed={active}
                        title={item.label}
                        onClick={() => toggleCheckbox(item.id)}
                        className={cn(
                          "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-left text-xs transition-colors",
                          active
                            ? "border-brand-500 bg-brand-50 font-medium text-brand-700"
                            : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50",
                        )}
                      >
                        {active && <Check className="size-3" />}
                        {shortLabel(item.label)}
                      </button>
                    );
                  })}
                </div>
              )}
            </section>
          );
        })}

        <section>
          <button
            type="button"
            className="flex w-full items-center justify-between text-left"
            onClick={() => setShowExtra((v) => !v)}
          >
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Ещё параметры
              {filledSecondary > 0 && (
                <span className="ml-2 rounded-full bg-brand-600 px-1.5 py-px text-[10px] text-white">
                  {filledSecondary}
                </span>
              )}
            </span>
            <ChevronDown className={cn("size-4 text-slate-400 transition-transform", showExtra && "rotate-180")} />
          </button>
          {showExtra && (
            <div className="mt-3 space-y-3 animate-fade-in">
              {secondaryFields.map((field) => (
                <Field key={field.id} label={field.label} hint={field.hint}>
                  <Input
                    value={filters.extra[field.id]}
                    placeholder={field.placeholder}
                    onChange={(e) => setExtra(field.id, e.target.value)}
                  />
                </Field>
              ))}
            </div>
          )}
        </section>
      </div>

      <div className="flex gap-2 border-t border-slate-200 bg-white p-4">
        <Button
          type="submit"
          variant="primary"
          className="flex-1"
          loading={loading}
          icon={<Search className="size-4" />}
        >
          {loading ? "Ищем компании…" : "Найти компании"}
        </Button>
        <Button variant="ghost" onClick={onReset} title="Сбросить фильтры" aria-label="Сбросить фильтры">
          <RotateCcw className="size-4" />
        </Button>
      </div>
    </form>
  );
}

function Field({
  label,
  hint,
  icon,
  children,
}: {
  label: string;
  hint?: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-slate-700">
        {icon && <span className="text-slate-400">{icon}</span>}
        {label}
      </span>
      {children}
      {hint && <span className="mt-1 block text-[11px] text-slate-400">{hint}</span>}
    </label>
  );
}

/** Убираем пояснения в скобках, чтобы чипы были компактными; полный текст — в title */
function shortLabel(label: string): string {
  return label.replace(/\s*\(.*?\)\s*/g, " ").replace(/\s+—.*$/, "").trim();
}
