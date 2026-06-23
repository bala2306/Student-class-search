import type { SelectedCourse } from "../context/StudySquadContext";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const LABELS: Record<string, string> = {
  Monday: "Mon",
  Tuesday: "Tue",
  Wednesday: "Wed",
  Thursday: "Thu",
  Friday: "Fri",
};

interface Props {
  courses: SelectedCourse[];
}

export default function ScheduleHeatmap({ courses }: Props) {
  const counts = DAYS.map((day) => ({
    day,
    count: courses.filter((course) => course.day_of_week === day).length,
  }));
  const max = Math.max(...counts.map((item) => item.count), 0);

  if (max === 0) {
    return null;
  }

  return (
    <div className="px-4 space-y-2">
      <div>
        <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
          Schedule Heatmap
        </h3>
        <p className="text-xs text-gray-400">Darker days have more selected courses.</p>
      </div>
      <div className="grid grid-cols-5 gap-1.5">
        {counts.map(({ day, count }) => {
          const intensity = max > 0 ? count / max : 0;
          return (
            <div
              key={day}
              className="rounded-lg border border-emerald-100 px-1.5 py-2 text-center"
              style={{
                backgroundColor: `rgba(16, 185, 129, ${0.08 + intensity * 0.72})`,
              }}
              title={`${day}: ${count} selected course${count === 1 ? "" : "s"}`}
            >
              <p className={`text-xs font-semibold ${count ? "text-emerald-950" : "text-gray-400"}`}>
                {LABELS[day]}
              </p>
              <p className={`text-[10px] ${count ? "text-emerald-900" : "text-gray-400"}`}>
                {count}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
