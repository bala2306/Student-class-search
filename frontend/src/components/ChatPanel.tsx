import { useState, useCallback } from "react";
import { api, type HistoryMessage } from "../api/client";
import type { Message } from "./MessageThread";
import MessageThread from "./MessageThread";
import InputBar from "./InputBar";

let msgId = 0;
const nextId = () => String(++msgId);

/**
 * Serialize the last 3 turns (6 messages) into the history format
 * the backend expects. Only include settled (non-loading, non-error) turns.
 */
function buildHistory(messages: Message[]): HistoryMessage[] {
  const settled = messages.filter((m) => !m.loading && !m.error && m.text);
  return settled.slice(-6).map((m) => ({
    role: m.role,
    content: m.text ?? "",
  }));
}

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  const sendQuery = useCallback(async (query: string) => {
    const userMsg: Message = { id: nextId(), role: "user", text: query };
    const placeholderId = nextId();
    const placeholder: Message = { id: placeholderId, role: "assistant", loading: true };

    // Capture history BEFORE appending the new user message
    setMessages((prev) => {
      const history = buildHistory(prev);
      const next = [...prev, userMsg, placeholder];

      // Fire the async search with the pre-computed history
      doSearch(query, history, placeholderId, next);

      return next;
    });
    setLoading(true);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function doSearch(
    query: string,
    history: HistoryMessage[],
    placeholderId: string,
    _snapshot: Message[],   // unused but kept for clarity
  ) {
    try {
      const resp = await api.search(query, history);

      setMessages((prev) =>
        prev.map((m) =>
          m.id === placeholderId
            ? {
                ...m,
                loading: false,
                text: resp.response_text,
                courses: resp.results,
              }
            : m,
        ),
      );
    } catch (e) {
      const detail =
        e instanceof Error ? e.message : "Search engine temporarily unavailable.";
      setMessages((prev) =>
        prev.map((m) =>
          m.id === placeholderId ? { ...m, loading: false, error: detail } : m,
        ),
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <MessageThread messages={messages} />
      <InputBar onSubmit={sendQuery} disabled={loading} />
    </div>
  );
}
