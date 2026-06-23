const BASE = import.meta.env.VITE_API_BASE_URL || "";

export interface CourseResult {
  course_code: string;
  title: string;
  subject: string;
  course_level: number | null;
  credits: number | null;
  instructor_name: string | null;
  day_of_week: string | null;
  start_time: string | null;
  end_time: string | null;
  room: string | null;
  building: string | null;
  semester: string | null;
  description: string | null;
  graph_context: string | null;
}

export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export interface SearchResponse {
  query: string;
  query_type: string;
  response_text: string;                 // RAG-grounded GPT response
  filters_extracted: Record<string, unknown>;
  results: CourseResult[];
  result_count: number;
  graph_context: string | null;
  message: string | null;               // backwards compat alias for response_text
}

export interface CoEnrollResult {
  course_code: string;
  title: string;
  subject: string | null;
  course_level: number | null;
  credits: number | null;
  frequency: number;
  co_occurrence_count: number;
  day_of_week: string | null;
  start_time: string | null;
  end_time: string | null;
  has_time_conflict: boolean;
  score_source: "coenrollment" | "catalog_match" | null;
}

export interface CoEnrollResponse {
  anchor_course: string;
  recommendations: CoEnrollResult[];
}

export interface WorkloadInsight {
  courses: string[];
  total_credits: number;
  workload_tier: string;
  workload_percentile: number;
  peer_schedule_count: number;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

export const api = {
  search: (query: string, history: HistoryMessage[] = []) =>
    post<SearchResponse>("/search", { query, history }),

  coenrollment: (
    code: string,
    anchorDay?: string,
    anchorStart?: string,
    anchorEnd?: string,
  ) => {
    let path = `/courses/${code}/coenrollment`;
    const params = new URLSearchParams();
    if (anchorDay) params.set("anchor_day", anchorDay);
    if (anchorStart) params.set("anchor_start", anchorStart);
    if (anchorEnd) params.set("anchor_end", anchorEnd);
    if ([...params].length) path += `?${params.toString()}`;
    return get<CoEnrollResponse>(path);
  },

  workloadInsight: (courses: string[]) =>
    get<WorkloadInsight>(`/graph/workload?courses=${courses.join(",")}`),
};
