import { useMemo } from "react";
import type { CourseResult } from "../api/client";
import { useStudySquad } from "../context/StudySquadContext";

interface Props {
  course: CourseResult;
}

const SUBJECT_COLORS: Record<string, string> = {
  "Computer Science": "bg-blue-100 text-blue-800",
  "Mathematics": "bg-green-100 text-green-800",
  "Statistics": "bg-purple-100 text-purple-800",
  "Physics": "bg-orange-100 text-orange-800",
};

function subjectColor(subject: string) {
  return SUBJECT_COLORS[subject] ?? "bg-gray-100 text-gray-700";
}

function decodeHtml(value: string | null | undefined) {
  if (!value) return "";
  const textarea = document.createElement("textarea");
  textarea.innerHTML = value;
  return textarea.value;
}

export default function CourseCard({ course }: Props) {
  const { setAnchor, addCourse, selectedCourses } = useStudySquad();
  const title = useMemo(() => decodeHtml(course.title), [course.title]);
  const description = useMemo(() => decodeHtml(course.description), [course.description]);

  const isAdded = selectedCourses.some((c) => c.code === course.course_code);

  function handleAddToSemester() {
    setAnchor({ ...course, title });
    addCourse({
      code: course.course_code,
      title,
      credits: course.credits ?? 3,
      day_of_week: course.day_of_week,
      start_time: course.start_time,
      end_time: course.end_time,
    });
  }

  return (
    <div className="border border-gray-200 rounded-xl bg-white p-4 space-y-2 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-sm font-bold text-gray-800">{course.course_code}</span>
            {course.graph_context && (
              <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full">
                {course.graph_context.replace(/_/g, " ")}
              </span>
            )}
          </div>
          <p className="text-sm font-medium text-gray-900 mt-0.5 truncate">{title}</p>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium whitespace-nowrap ${subjectColor(course.subject)}`}>
          {course.subject}
        </span>
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
        {course.course_level && <span>Level {course.course_level}</span>}
        {course.credits && <span>{course.credits} cr</span>}
        {course.instructor_name && <span>👤 {course.instructor_name}</span>}
        {course.day_of_week && course.start_time && (
          <span>🕐 {course.day_of_week} {course.start_time.slice(0, 5)}–{course.end_time?.slice(0, 5)}</span>
        )}
        {course.room && course.building && <span>📍 {course.building} {course.room}</span>}
        {course.semester && <span>{course.semester}</span>}
      </div>

      {description && (
        <p className="course-description text-xs text-gray-500" title={description}>
          {description}
        </p>
      )}

      <div className="flex gap-2 pt-1">
        <button
          onClick={handleAddToSemester}
          disabled={isAdded}
          className={`w-full text-xs py-1.5 rounded-lg font-medium transition-colors ${
            isAdded
              ? "bg-green-100 text-green-700 cursor-default"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }`}
        >
          {isAdded ? "Added to Semester" : "Add to Semester"}
        </button>
      </div>
    </div>
  );
}
