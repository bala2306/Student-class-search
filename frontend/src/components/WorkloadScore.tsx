import type { WorkloadInsight } from "../api/client";

interface Props {
  courses: { credits: number }[];
  insight: WorkloadInsight | null;
}

export default function WorkloadScore({ courses, insight }: Props) {
  const fallbackTotal = courses.reduce((sum, c) => sum + (c.credits ?? 0), 0);
  const total = insight ? insight.total_credits : fallbackTotal;
  const tier = insight?.workload_tier ?? "calculating";
  const percentile = insight?.workload_percentile ?? 0;
  const pct = Math.round(percentile * 100);
  const hasDatasetBaseline = Boolean(insight && tier !== "unknown");

  return (
    <div className="mx-4 rounded-xl border border-gray-100 bg-white p-3.5 shadow-sm space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
            Semester Workload
          </p>
          <div className="mt-1 flex items-end gap-1.5">
            <span className="text-3xl font-bold leading-none text-gray-950">{total}</span>
            <span className="pb-0.5 text-sm text-gray-500">credits</span>
          </div>
        </div>
        <div className="rounded-lg bg-gray-50 px-2.5 py-1 text-right">
          <p className="text-sm font-semibold capitalize text-gray-900">{tier}</p>
          <p className="text-[10px] uppercase tracking-wide text-gray-400">load</p>
        </div>
      </div>

      {hasDatasetBaseline ? (
        <>
          <div className="h-2 rounded-full bg-gray-200">
            <div
              className="h-2 rounded-full bg-emerald-500 transition-all duration-300"
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="text-xs leading-5 text-gray-500">
            Heavier than <span className="font-semibold text-gray-800">{pct}%</span> of peer schedules in
            the enrollment dataset.
          </p>
        </>
      ) : (
        <p className="text-xs text-gray-500">Dataset workload baseline unavailable.</p>
      )}
    </div>
  );
}
