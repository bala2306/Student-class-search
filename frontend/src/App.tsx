import { StudySquadProvider } from "./context/StudySquadContext";
import ChatPanel from "./components/ChatPanel";
import StudySquadPanel from "./components/StudySquadPanel";

export default function App() {
  return (
    <StudySquadProvider>
      <div className="flex h-screen bg-gray-50 overflow-hidden">
        {/* Left: Chat */}
        <div className="flex flex-col flex-1 min-w-0 border-r border-gray-200 bg-white">
          <header className="flex items-center gap-3 px-6 py-4 border-b border-gray-200 bg-white">
            <span className="text-2xl">🎓</span>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">Student Class Search</h1>
              <p className="text-xs text-gray-500">AI-powered course discovery & schedule planning</p>
            </div>
          </header>
          <ChatPanel />
        </div>

        {/* Right: Study Squad */}
        <div className="w-96 flex flex-col bg-gray-50 overflow-hidden">
          <header className="px-5 py-4 border-b border-gray-200 bg-white">
            <h2 className="text-sm font-semibold text-gray-900">Study Squad Finder</h2>
            <p className="text-xs text-gray-500 mt-0.5">Click a course card to explore co-enrollment insights</p>
          </header>
          <StudySquadPanel />
        </div>
      </div>
    </StudySquadProvider>
  );
}
