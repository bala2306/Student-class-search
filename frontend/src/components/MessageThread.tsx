import { useEffect, useRef } from "react";
import type { CourseResult } from "../api/client";
import UserMessage from "./UserMessage";
import AssistantMessage from "./AssistantMessage";

export interface Message {
  id: string;
  role: "user" | "assistant";
  text?: string;         // RAG-grounded GPT response text (or user query text)
  courses?: CourseResult[];
  loading?: boolean;
  error?: string;
}

interface Props {
  messages: Message[];
}

export default function MessageThread({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-center px-8">
        <div className="space-y-3">
          <p className="text-4xl">🎓</p>
          <p className="text-gray-700 font-medium">What would you like to study?</p>
          <p className="text-sm text-gray-500">
            Search for courses by subject, day, level, or instructor — or ask about prerequisites.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto message-thread px-4 py-4 space-y-4">
      {messages.map((m) =>
        m.role === "user" ? (
          <UserMessage key={m.id} text={m.text ?? ""} />
        ) : (
          <AssistantMessage
            key={m.id}
            text={m.text}
            courses={m.courses}
            loading={m.loading}
            error={m.error}
          />
        ),
      )}
      <div ref={bottomRef} />
    </div>
  );
}
