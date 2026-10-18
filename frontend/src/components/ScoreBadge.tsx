import { cn, scoreTier, TIER_LABEL, type ScoreTier } from "../lib/format";

const TIER_STYLES: Record<ScoreTier, { ring: string; text: string; pill: string }> = {
  hot: { ring: "stroke-hot", text: "text-hot", pill: "bg-red-50 text-red-700" },
  warm: { ring: "stroke-warm", text: "text-amber-600", pill: "bg-amber-50 text-amber-700" },
  cold: { ring: "stroke-cold", text: "text-blue-600", pill: "bg-blue-50 text-blue-700" },
  low: { ring: "stroke-low", text: "text-slate-500", pill: "bg-slate-100 text-slate-600" },
};

/** Круговой индикатор скоринга 0–100 с подписью уровня */
export function ScoreBadge({ score, size = "md" }: { score: number; size?: "md" | "lg" }) {
  const tier = scoreTier(score);
  const styles = TIER_STYLES[tier];
  const dimension = size === "lg" ? 64 : 48;
  const stroke = size === "lg" ? 5 : 4;
  const radius = (dimension - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - Math.min(score, 100) / 100);

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: dimension, height: dimension }}>
        <svg width={dimension} height={dimension} className="-rotate-90">
          <circle
            cx={dimension / 2}
            cy={dimension / 2}
            r={radius}
            fill="none"
            strokeWidth={stroke}
            className="stroke-slate-100"
          />
          <circle
            cx={dimension / 2}
            cy={dimension / 2}
            r={radius}
            fill="none"
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className={cn(styles.ring, "transition-[stroke-dashoffset] duration-500")}
          />
        </svg>
        <span
          className={cn(
            "absolute inset-0 flex items-center justify-center font-semibold tabular-nums",
            size === "lg" ? "text-lg" : "text-sm",
            styles.text,
          )}
        >
          {score}
        </span>
      </div>
      <span className={cn("rounded px-1.5 py-px text-[10px] font-semibold uppercase tracking-wide", styles.pill)}>
        {TIER_LABEL[tier]}
      </span>
    </div>
  );
}
