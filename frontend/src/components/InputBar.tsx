import { useRef, type KeyboardEvent } from "react";

interface Props {
  onSubmit: (query: string) => void;
  disabled: boolean;
}

const SUGGESTIONS = [
  "Show me CS classes on Mondays",
  "What can I take after CS225?",
  "What 300-level math courses are on Fridays?",
  "Find classes taught by Dr. Ramos",
];

export default function InputBar({ onSubmit, disabled }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);

  function submit() {
    const val = ref.current?.value.trim() ?? "";
    if (!val || disabled) return;
    onSubmit(val);
    if (ref.current) ref.current.value = "";
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3 space-y-2">
      <div className="flex gap-2 flex-wrap">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => {
              if (ref.current) ref.current.value = s;
              ref.current?.focus();
            }}
            className="text-xs px-2.5 py-1 rounded-full border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors truncate max-w-[200px]"
          >
            {s}
          </button>
        ))}
      </div>
      <div className="flex gap-2 items-end">
        <textarea
          ref={ref}
          onKeyDown={onKey}
          disabled={disabled}
          rows={1}
          placeholder="Ask about courses… (Enter to send, Shift+Enter for newline)"
          className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          onClick={submit}
          disabled={disabled}
          className="bg-blue-600 text-white rounded-xl px-4 py-2.5 text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </div>
    </div>
  );
}
