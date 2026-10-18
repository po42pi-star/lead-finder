import { describe, expect, it } from "vitest";
import { isDemoLead, pluralize, scoreTier, shortCompanyName, sourceLabels } from "./format";

describe("scoreTier", () => {
  it("использует пороги из базы знаний: 80 / 50 / 30", () => {
    expect(scoreTier(80)).toBe("hot");
    expect(scoreTier(79)).toBe("warm");
    expect(scoreTier(50)).toBe("warm");
    expect(scoreTier(30)).toBe("cold");
    expect(scoreTier(29)).toBe("low");
  });
});

describe("sourceLabels", () => {
  it("переводит составной источник в читаемые названия без дублей", () => {
    expect(sourceLabels("egr_nalog_ru+dadata+dadata")).toEqual(["ФНС", "DaData"]);
  });
});

describe("isDemoLead", () => {
  it("распознаёт демо-компании", () => {
    expect(isDemoLead("demo")).toBe(true);
    expect(isDemoLead("egr_nalog_ru+dadata")).toBe(false);
  });
});

describe("shortCompanyName", () => {
  it("сокращает организационно-правовую форму", () => {
    expect(shortCompanyName('ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "ВЕНТ"')).toBe('ООО "ВЕНТ"');
  });
});

describe("pluralize", () => {
  it("склоняет по правилам русского языка", () => {
    const word = (n: number) => pluralize(n, "компания", "компании", "компаний");
    expect([1, 2, 5, 11, 21, 22].map(word)).toEqual([
      "компания",
      "компании",
      "компаний",
      "компаний",
      "компания",
      "компании",
    ]);
  });
});
