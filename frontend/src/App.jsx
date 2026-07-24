import { useEffect, useRef, useState } from "react";
import ChatHeader from "./components/ChatHeader.jsx";
import MessageList from "./components/MessageList.jsx";
import ChatInput from "./components/ChatInput.jsx";
import Sidebar from "./components/Sidebar.jsx";
import { streamChat } from "./api/chatStream.js";
import { fetchConversations, fetchConversationMessages } from "./api/conversations.js";

const SESSION_STORAGE_KEY = "chatbot_session_id";

function getOrCreateSessionId() {
  const existing = localStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) return existing;
  const id = crypto.randomUUID();
  localStorage.setItem(SESSION_STORAGE_KEY, id);
  return id;
}

function toUiMessages(rawMessages) {
  // Server messages are {role, content}; UI messages also need a stable
  // id for React keys/updates. No streaming/error flags — these are
  // already-complete messages loaded from history.
  return rawMessages.map((m) => ({
    id: crypto.randomUUID(),
    role: m.role,
    content: m.content,
  }));
}

export default function App() {
  const [sessionId, setSessionId] = useState(getOrCreateSessionId);
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const abortRef = useRef(null);

  const refreshSessions = async () => {
    try {
      const list = await fetchConversations();
      setSessions(list);
    } catch (err) {
      console.error("Failed to refresh conversation list:", err);
    } finally {
      setSessionsLoading(false);
    }
  };

  useEffect(() => {
    refreshSessions();
    return () => abortRef.current?.abort();
  }, []);

  const updateAssistantMessage = (id, updater) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? updater(m) : m)));
  };

  const switchToSession = (id) => {
    abortRef.current?.abort();
    localStorage.setItem(SESSION_STORAGE_KEY, id);
    setSessionId(id);
    setSidebarOpen(false);
  };

  const handleNewChat = () => {
    if (isStreaming) return;
    const id = crypto.randomUUID();
    switchToSession(id);
    setMessages([]);
  };

  const handleSelectSession = async (id) => {
    if (id === sessionId || isStreaming) return;
    switchToSession(id);
    try {
      const data = await fetchConversationMessages(id);
      setMessages(toUiMessages(data.messages));
    } catch (err) {
      console.error("Failed to load session:", err);
      setMessages([]);
    }
  };

  const handleSend = async (text) => {
    if (isStreaming) return;

    const userMessage = { id: crypto.randomUUID(), role: "user", content: text };
    const assistantId = crypto.randomUUID();
    const assistantMessage = { id: assistantId, role: "assistant", content: "", streaming: true };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setIsStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamChat({
        sessionId,
        message: text,
        signal: controller.signal,
        onEvent: (event) => {
          if (event.type === "token") {
            updateAssistantMessage(assistantId, (m) => ({
              ...m,
              content: m.content + event.content,
            }));
          } else if (event.type === "done") {
            updateAssistantMessage(assistantId, (m) => ({ ...m, streaming: false }));
          } else if (event.type === "error") {
            updateAssistantMessage(assistantId, (m) => ({
              ...m,
              content: m.content || "Something went wrong on the server side.",
              streaming: false,
              error: true,
            }));
          }
        },
      });
    } catch (err) {
      if (err.name !== "AbortError") {
        updateAssistantMessage(assistantId, (m) => ({
          ...m,
          content: "Couldn't reach the server. Is the backend running?",
          streaming: false,
          error: true,
        }));
      }
    } finally {
      setIsStreaming(false);
      refreshSessions();
    }
  };

  return (
    <div className="h-full flex">
      <Sidebar
        sessions={sessions}
        activeSessionId={sessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        loading={sessionsLoading}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="flex-1 flex flex-col min-w-0 relative">
        {/* Mobile-only sidebar toggle — kept independent of ChatHeader's
            internals since that file's contents weren't available here.
            Feel free to move this into ChatHeader if you'd rather it
            live inline with the title. */}
        <button
          onClick={() => setSidebarOpen((v) => !v)}
          className="sm:hidden absolute top-3 left-3 z-10 w-8 h-8 flex items-center justify-center rounded-md bg-card border border-line text-ink-soft"
          aria-label="Toggle chat history"
        >
          ☰
        </button>
        <ChatHeader sessionId={sessionId} isStreaming={isStreaming} />
        <MessageList messages={messages} />
        <ChatInput onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  );
}
