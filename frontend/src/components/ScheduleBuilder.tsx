import type { SelectedCourse } from "../context/StudySquadContext";
import { useStudySquad } from "../context/StudySquadContext";

function hasConflict(a: SelectedCourse, b: SelectedCourse) {
  if (!a.day_of_week || !b.day_of_week || a.day_of_week !== b.day_of_week) return false;
  const aStart = a.start_time ?? "00:00";
  const aEnd = a.end_time ?? "00:00";
  const bStart = b.start_time ?? "00:00";
  const bEnd = b.end_time ?? "00:00";
  return aStart < bEnd && bStart < aEnd;
}

interface Props {
  courses: SelectedCourse[];
}

export default function ScheduleBuilder({ courses }: Props) {
  const { removeCourse } = useStudySquad();

  if (courses.length === 0) {
    return (
      <p className="text-xs text-gray-400 px-4 py-2">
        No courses added yet. Click "Add to Semester" on any course card.
      </p>
    );
  }

  const conflictPairs = new Set<string>();
  for (let i = 0; i < courses.length; i++) {
    for (let j = i + 1; j < courses.length; j++) {
      if (hasConflict(courses[i], courses[j])) {
        conflictPairs.add(courses[i].code);
        conflictPairs.add(courses[j].code);
      }
    }
  }

  return (
    <div className="space-y-1.5 px-4">
      {courses.map((c) => {
        const conflict = conflictPairs.has(c.code);
        return (
          <div
            key={c.code}
            className={`flex items-center gap-2 p-2.5 rounded-lg border ${
              conflict ? "border-red-200 bg-red-50" : "border-gray-100 bg-white"
            }`}
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="font-mono text-xs font-bold text-gray-800">{c.code}</span>
                {c.credits && (
                  <span className="text-xs bg-gray-100 text-gray-600 px-1.5 rounded">{c.credits} cr</span>
                )}
                {conflict && (
                  <span className="text-xs bg-red-100 text-red-600 px-1.5 rounded">⚠ conflict</span>
                )}
              </div>
              <p className="text-xs text-gray-600 truncate">{c.title}</p>
              {c.day_of_week && c.start_time && (
                <p className="text-xs text-gray-400">
                  {c.day_of_week} {c.start_time.slice(0, 5)}–{c.end_time?.slice(0, 5)}
                </p>
              )}
            </div>
            <button
              onClick={() => removeCourse(c.code)}
              className="text-gray-400 hover:text-red-500 transition-colors text-sm"
              title="Remove"
            >
              ✕
            </button>
          </div>
        );
      })}
    </div>
  );
}
