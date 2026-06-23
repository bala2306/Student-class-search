import type { CourseResult } from "../api/client";
import CourseResultList from "./CourseResultList";
import LoadingDots from "./LoadingDots";

interface Props {
  text?: string;
  courses?: CourseResult[];
  loading?: boolean;
  error?: string;
}

export default function AssistantMessage({ text, courses, loading, error }: Props) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm flex-shrink-0">
        🎓
      </div>
      <div className="flex-1 space-y-3 max-w-full">
        {loading && (
          <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3">
            <LoadingDots />
          </div>
        )}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}
        {text && !loading && (
          <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-gray-800 leading-relaxed">
            {text}
          </div>
        )}
        {courses && courses.length > 0 && !loading && (
          <CourseResultList courses={courses} />
        )}
      </div>
    </div>
  );
}
