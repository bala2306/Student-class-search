import type { CoEnrollResult } from "../api/client";
import { useStudySquad } from "../context/StudySquadContext";

interface Props {
  items: CoEnrollResult[];
}

export default function CoEnrollList({ items }: Props) {
  const { addCourse, selectedCourses } = useStudySquad();

  if (items.length === 0) {
    return (
      <p className="text-xs text-gray-400 px-4 py-2">No co-enrollment data yet.</p>
    );
  }

  return (
    <div className="space-y-1 px-4">
      {items.map((item) => {
        const isAdded = selectedCourses.some((c) => c.code === item.course_code);
        const hasCoEnrollmentScore =
          item.score_source === "coenrollment" && item.frequency > 0;
        const pct = Math.round(item.frequency * 100);
        return (
          <div
            key={item.course_code}
            className={`flex items-center gap-3 p-2.5 rounded-lg border ${
              item.has_time_conflict ? "border-red-200 bg-red-50" : "border-gray-100 bg-white"
            }`}
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="font-mono text-xs font-bold text-gray-800">{item.course_code}</span>
                {item.has_time_conflict && (
                  <span className="text-xs bg-red-100 text-red-600 px-1.5 rounded">conflict</span>
                )}
              </div>
              <p className="text-xs text-gray-600 truncate">{item.title}</p>
              {item.day_of_week && item.start_time && (
                <p className="text-xs text-gray-400">
                  {item.day_of_week} {item.start_time.slice(0, 5)}–{item.end_time?.slice(0, 5)}
                </p>
              )}
              {hasCoEnrollmentScore ? (
                <div className="mt-1 flex items-center gap-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                    <div
                      className="bg-blue-500 h-1.5 rounded-full"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500">{pct}%</span>
                  {item.co_occurrence_count > 0 && (
                    <span className="text-xs text-gray-400">
                      {item.co_occurrence_count} peers
                    </span>
                  )}
                </div>
              ) : (
                <p className="mt-1 text-xs text-gray-400">Catalog match</p>
              )}
            </div>
            <button
              onClick={() =>
                addCourse({
                  code: item.course_code,
                  title: item.title,
                  credits: item.credits ?? 3,
                  day_of_week: item.day_of_week,
                  start_time: item.start_time,
                  end_time: item.end_time,
                })
              }
              disabled={isAdded}
              className={`text-xs px-2.5 py-1 rounded-lg font-medium transition-colors ${
                isAdded
                  ? "bg-green-100 text-green-700 cursor-default"
                  : "bg-blue-600 text-white hover:bg-blue-700"
              }`}
            >
              {isAdded ? "Added" : "+ Add"}
            </button>
          </div>
        );
      })}
    </div>
  );
}
