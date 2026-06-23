import { useState } from "react";
import type { CourseResult } from "../api/client";
import CourseCard from "./CourseCard";

interface Props {
  courses: CourseResult[];
}

const VISIBLE_COURSE_LIMIT = 3;

export default function CourseResultList({ courses }: Props) {
  const [expanded, setExpanded] = useState(false);
  const visibleCourses = expanded ? courses : courses.slice(0, VISIBLE_COURSE_LIMIT);
  const hiddenCount = Math.max(courses.length - VISIBLE_COURSE_LIMIT, 0);

  return (
    <div className="space-y-2">
      {visibleCourses.map((c) => (
        <CourseCard key={`${c.course_code}-${c.day_of_week}`} course={c} />
      ))}
      {hiddenCount > 0 && (
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
          className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          {expanded ? "Show fewer courses" : `Show ${hiddenCount} more courses`}
        </button>
      )}
    </div>
  );
}
