export default function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  loading,
  open,
  onClose,
}) {
  return (
    <>
      {/* Mobile backdrop — tapping it closes the sidebar. Invisible/inert on desktop. */}
      {open && (
        <div
          className="fixed inset-0 bg-black/30 z-10 sm:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={[
          "fixed sm:static inset-y-0 left-0 z-20 w-64 shrink-0",
          "bg-card border-r border-line flex flex-col",
          "transform transition-transform duration-200 sm:transform-none",
          open ? "translate-x-0" : "-translate-x-full sm:translate-x-0",
        ].join(" ")}
      >
        <div className="p-3 border-b border-line">
          <button
            onClick={onNewChat}
            className="w-full flex items-center justify-center gap-1.5 rounded-lg bg-accent text-white text-sm font-medium py-2 hover:opacity-90 transition"
          >
            + New chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto py-2">
          {loading ? (
            <p className="px-3 py-2 text-xs text-ink-soft">Loading…</p>
          ) : sessions.length === 0 ? (
            <p className="px-3 py-2 text-xs text-ink-soft">No conversations yet</p>
          ) : (
            <ul className="space-y-0.5 px-1.5">
              {sessions.map((s) => (
                <li key={s.session_id}>
                  <button
                    onClick={() => onSelectSession(s.session_id)}
                    title={s.title}
                    className={[
                      "w-full text-left px-2.5 py-2 rounded-lg text-sm truncate transition",
                      s.session_id === activeSessionId
                        ? "bg-accent/10 text-ink font-medium"
                        : "text-ink-soft hover:bg-ink/5",
                    ].join(" ")}
                  >
                    {s.title || "New chat"}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </>
  );
}
