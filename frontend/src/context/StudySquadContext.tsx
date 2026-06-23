import { createContext, useCallback, useContext, useState } from "react";
import type { ReactNode } from "react";
import { api, type CoEnrollResult, type CourseResult, type WorkloadInsight } from "../api/client";

export interface SelectedCourse {
  code: string;
  title: string;
  credits: number;
  day_of_week: string | null;
  start_time: string | null;
  end_time: string | null;
}

interface StudySquadState {
  anchorCourse: string | null;
  selectedCourses: SelectedCourse[];
  coEnrollData: CoEnrollResult[];
  workloadInsight: WorkloadInsight | null;
  coEnrollLoading: boolean;
  coEnrollError: string | null;
}

interface StudySquadContextValue extends StudySquadState {
  setAnchor: (course: CourseResult) => void;
  addCourse: (course: SelectedCourse) => void;
  removeCourse: (code: string) => void;
  clearSemester: () => void;
}

const StudySquadContext = createContext<StudySquadContextValue | null>(null);

export function StudySquadProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<StudySquadState>({
    anchorCourse: null,
    selectedCourses: [],
    coEnrollData: [],
    workloadInsight: null,
    coEnrollLoading: false,
    coEnrollError: null,
  });

  const refreshWorkloadInsight = useCallback((courses: SelectedCourse[]) => {
    if (courses.length === 0) {
      return;
    }

    const codes = courses.map((c) => c.code);
    const key = codes.join(",");
    api
      .workloadInsight(codes)
      .then((insight) =>
        setState((prev) => {
          const currentKey = prev.selectedCourses.map((c) => c.code).join(",");
          return currentKey === key ? { ...prev, workloadInsight: insight } : prev;
        }),
      )
      .catch(() => {
        setState((prev) => {
          const currentKey = prev.selectedCourses.map((c) => c.code).join(",");
          return currentKey === key ? { ...prev, workloadInsight: null } : prev;
        });
      });
  }, []);

  const setAnchor = useCallback(async (course: CourseResult) => {
    setState((s) => ({
      ...s,
      anchorCourse: course.course_code,
      coEnrollLoading: true,
      coEnrollError: null,
    }));
    try {
      const data = await api.coenrollment(
        course.course_code,
        course.day_of_week ?? undefined,
        course.start_time ?? undefined,
        course.end_time ?? undefined,
      );
      setState((s) => ({ ...s, coEnrollData: data.recommendations, coEnrollLoading: false }));
    } catch (e) {
      setState((s) => ({
        ...s,
        coEnrollData: [],
        coEnrollLoading: false,
        coEnrollError:
          e instanceof Error ? e.message : "Failed to load co-enrollment data.",
      }));
    }
  }, []);

  const addCourse = useCallback((course: SelectedCourse) => {
    setState((s) => {
      // Deduplicate
      if (s.selectedCourses.some((c) => c.code === course.code)) return s;

      const next = [...s.selectedCourses, course];

      refreshWorkloadInsight(next);

      return { ...s, selectedCourses: next };
    });
  }, [refreshWorkloadInsight]);

  const removeCourse = useCallback((code: string) => {
    setState((s) => {
      const next = s.selectedCourses.filter((c) => c.code !== code);
      refreshWorkloadInsight(next);
      return {
        ...s,
        selectedCourses: next,
        workloadInsight: next.length === 0 ? null : s.workloadInsight,
      };
    });
  }, [refreshWorkloadInsight]);

  const clearSemester = useCallback(() => {
    setState((s) => ({
      ...s,
      anchorCourse: null,
      selectedCourses: [],
      coEnrollData: [],
      workloadInsight: null,
      coEnrollLoading: false,
      coEnrollError: null,
    }));
  }, []);

  return (
    <StudySquadContext.Provider
      value={{ ...state, setAnchor, addCourse, removeCourse, clearSemester }}
    >
      {children}
    </StudySquadContext.Provider>
  );
}

export function useStudySquad() {
  const ctx = useContext(StudySquadContext);
  if (!ctx) throw new Error("useStudySquad must be used inside StudySquadProvider");
  return ctx;
}
