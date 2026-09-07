"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { sendAssistantMessage } from "../lib/api";

type ChatMessage = {
  role: "user" | "assistant";
  text: string;
  source?: string;
};

const GENERAL_SUGGESTIONS = [
  "What is ResearchOS?",
  "What projects do I have?",
  "Explain quantum computing in simple terms",
  "How do I write a literature review?",
  "Recommend a dataset for my research",
  "What is the difference between supervised and unsupervised learning?",
];

const PROJECT_SUGGESTIONS = [
  "What documents are in this project?",
  "Summarize my uploaded paper",
  "What methodology does my document use?",
  "What are the limitations?",
  "What research gaps exist?",
  "Show me my references",
  "What analyses have I run?",
  "What evidence sessions do I have?",
];

export default function ResearchAssistant({
  projectId,
}: {
  projectId?: number;
} = {}) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      text: "Hello! I'm your **ResearchOS Research Assistant**.\n\nI can help you with:\n- Your projects, documents, and references\n- Summarizing and analyzing uploaded papers\n- Research methodology and guidance\n- Dataset recommendations\n- Understanding research gaps\n\nWhat would you like to know?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const suggestions = projectId
    ? PROJECT_SUGGESTIONS
    : GENERAL_SUGGESTIONS;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 150);
  }, [isOpen]);

  async function handleSend(
    e: FormEvent,
    questionText?: string,
  ) {
    e.preventDefault();
    const text = (questionText || input).trim();
    if (!text || loading) return;

    const userMessage: ChatMessage = { role: "user", text };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const token = localStorage.getItem("access_token");
      if (!token) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: "Please sign in to use the Research Assistant.", source: "none" },
        ]);
        return;
      }
      // Build conversation history for follow-up context
      const history = messages
        .filter((m) => m.role === "user" || m.role === "assistant")
        .map((m) => ({ role: m.role, content: m.text }))
        .slice(-10); // last 10 turns
      const response = await sendAssistantMessage(token, text, projectId, history);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: response.reply,
          source: response.source,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "I'm sorry, I couldn't process your request right now. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function clearChat() {
    setMessages([
      {
        role: "assistant",
        text: "Chat cleared. How can I help you with your research?",
      },
    ]);
  }

  const hasUserMessages = messages.some(
    (m) => m.role === "user",
  );

  return (
    <div
      className="fixed bottom-5 right-5 z-50 sm:bottom-6 sm:right-6"
      style={{
        fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
      }}
    >
      {/* Chat Panel */}
      {isOpen && (
        <div className="research-assistant-panel mb-3 w-[calc(100vw-2.5rem)] max-w-[380px] sm:w-[380px]">
          {/* Header */}
          <div className="research-assistant-header">
            <div className="flex items-center gap-3">
              <div
                className="flex h-9 w-9 items-center justify-center rounded-full text-sm font-bold"
                style={{
                  background: "rgba(105, 76, 197, 0.1)",
                  color: "#664bc5",
                }}
              >
                ✦
              </div>
              <div>
                <h3
                  className="text-sm font-bold"
                  style={{ color: "#1b2440" }}
                >
                  Research Assistant
                </h3>
                <p
                  className="text-xs"
                  style={{ color: "#8790a4" }}
                >
                  {projectId
                    ? "Project context aware"
                    : "Workspace-wide assistant"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              {hasUserMessages && (
                <button
                  onClick={clearChat}
                  className="flex h-8 w-8 items-center justify-center rounded-full transition text-xs"
                  style={{ color: "#8790a4" }}
                  title="Clear chat"
                >
                  🗑
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="flex h-8 w-8 items-center justify-center rounded-full transition"
                style={{ color: "#8790a4" }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background =
                    "rgba(105, 76, 197, 0.06)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background =
                    "transparent";
                }}
                aria-label="Close assistant"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          </div>

          {/* Messages */}
          <div
            className="research-assistant-messages"
            style={{ height: "380px" }}
          >
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`research-assistant-msg ${msg.role}`}
              >
                <div className="research-assistant-bubble">
                  <p style={{ whiteSpace: "pre-wrap" }}>
                    {msg.text}
                  </p>
                  {msg.source && msg.role === "assistant" && (
                    <p
                      className="mt-2 border-t border-slate-200 pt-1.5 text-[10px] italic"
                      style={{ color: "#94a3b8" }}
                    >
                      Source: {msg.source}
                    </p>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="research-assistant-msg assistant">
                <div className="research-assistant-bubble">
                  <div className="flex items-center gap-1.5 py-1">
                    <span className="typing-dot" />
                    <span className="typing-dot" />
                    <span className="typing-dot" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Suggested questions */}
          {!hasUserMessages && (
            <div className="research-assistant-suggestions">
              {suggestions.map((q) => (
                <button
                  key={q}
                  onClick={(e) => handleSend(e, q)}
                  disabled={loading}
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          {/* Input bar */}
          <form
            onSubmit={handleSend}
            className="research-assistant-input-bar"
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                projectId
                  ? "Ask anything about this project…"
                  : "Ask anything — research, coding, general…"
              }
              disabled={loading}
              aria-label="Type your message"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="research-assistant-send"
              aria-label="Send message"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          </form>
        </div>
      )}

      {/* Floating trigger button */}
      <div className="flex justify-end">
        <button
          onClick={() => setIsOpen((prev) => !prev)}
          className={`research-assistant-trigger ${isOpen ? "open" : ""}`}
          aria-label={
            isOpen
              ? "Close research assistant"
              : "Open research assistant"
          }
        >
          {isOpen ? (
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          ) : (
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 2a8 8 0 0 0-8 8c0 3.4 2.1 6.3 5 7.4V22l3.5-2.5c.2 0 .3 0 .5 0a8 8 0 0 0 0-16z" />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}
