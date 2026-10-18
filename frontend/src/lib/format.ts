export { clsx as cn } from "clsx";

export type ScoreTier = "hot" | "warm" | "cold" | "low";

// Пороги из базы знаний: rag_docs/system/system_search_guide.md
export function scoreTier(score: number): ScoreTier {
  if (score >= 80) return "hot";
  if (score >= 50) return "warm";
  if (score >= 30) return "cold";
  return "low";
}

export const TIER_LABEL: Record<ScoreTier, string> = {
  hot: "Горячий",
  warm: "Тёплый",
  cold: "Холодный",
  low: "Слабый",
};

export const SEGMENT_LABEL: Record<string, string> = {
  installer: "Монтаж",
  designer: "Проектирование",
  contractor: "Генподряд",
  industrial: "Промышленность",
};

const SOURCE_LABEL: Record<string, string> = {
  egr_nalog_ru: "ФНС",
  dadata: "DaData",
  dgis: "2ГИС",
  "2gis": "2ГИС",
  zakupki: "Госзакупки",
  industry_registry: "АВОК",
  demo: "Демо",
};

export function sourceLabels(source: string): string[] {
  return [...new Set(source.split("+").map((s) => SOURCE_LABEL[s] ?? s))];
}

export function isDemoLead(source: string): boolean {
  return source.split("+").includes("demo");
}

export function segmentLabel(segment: string): string {
  return SEGMENT_LABEL[segment] ?? segment;
}

export function pluralize(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

/** «ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "ВЕНТ"» → «ООО "ВЕНТ"» */
export function shortCompanyName(name: string): string {
  return name
    .replace(/^ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ/i, "ООО")
    .replace(/^АКЦИОНЕРНОЕ ОБЩЕСТВО/i, "АО")
    .replace(/^ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО/i, "ПАО")
    .trim();
}
