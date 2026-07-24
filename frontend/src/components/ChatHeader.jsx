export default function ChatHeader({ sessionId, isStreaming }) {
  return (
    <header className="border-b border-line px-4 sm:px-6 py-3.5 flex items-center justify-between bg-paper">
      <div className="flex items-baseline gap-2.5">
        <h1 className="font-display text-lg text-ink">Chatbot</h1>
        <span className="hidden sm:inline text-xs font-mono text-ink-soft/70">
          session · {sessionId.slice(0, 8)}
        </span>
      </div>
      <div className="flex items-center gap-1.5 text-xs font-mono text-ink-soft">
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            isStreaming ? "bg-accent animate-pulse" : "bg-ink-soft/40"
          }`}
        />
        {isStreaming ? "streaming" : "idle"}
      </div>
    </header>
  );
}
