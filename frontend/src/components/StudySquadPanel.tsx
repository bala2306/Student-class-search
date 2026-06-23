import { useStudySquad } from "../context/StudySquadContext";
import CoEnrollList from "./CoEnrollList";
import ScheduleBuilder from "./ScheduleBuilder";
import WorkloadScore from "./WorkloadScore";
import LoadingDots from "./LoadingDots";
import ScheduleHeatmap from "./ScheduleHeatmap";

export default function StudySquadPanel() {
  const {
    anchorCourse,
    selectedCourses,
    coEnrollData,
    workloadInsight,
    coEnrollLoading,
    coEnrollError,
    clearSemester,
  } = useStudySquad();

  return (
    <div className="flex flex-col overflow-y-auto flex-1 py-4 gap-5">

      {/* Co-enrollment section */}
      <section>
        <div className="flex items-center justify-between px-4 mb-2">
          <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
            {anchorCourse ? `Recommended with ${anchorCourse}` : "Course Suggestions"}
          </h3>
        </div>
        {coEnrollLoading && <div className="px-4"><LoadingDots /></div>}
        {coEnrollError && <p className="text-xs text-red-500 px-4">{coEnrollError}</p>}
        {!coEnrollLoading && !coEnrollError && (
          <CoEnrollList items={coEnrollData} />
        )}
      </section>

      <div className="border-t border-gray-200" />

      {/* Semester builder section */}
      <section>
        <div className="flex items-center justify-between px-4 mb-2">
          <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
            My Semester ({selectedCourses.length} courses)
          </h3>
          {selectedCourses.length > 0 && (
            <button
              onClick={clearSemester}
              className="text-xs text-red-500 hover:text-red-700 transition-colors"
            >
              Clear all
            </button>
          )}
        </div>
        <ScheduleBuilder courses={selectedCourses} />
      </section>

      {/* Workload score */}
      {selectedCourses.length > 0 && (
        <>
          <div className="border-t border-gray-200" />
          <section>
            <div className="px-4 mb-2">
              <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Workload</h3>
            </div>
            <WorkloadScore courses={selectedCourses} insight={workloadInsight} />
          </section>
        </>
      )}

      {selectedCourses.length > 0 && <ScheduleHeatmap courses={selectedCourses} />}
    </div>
  );
}
