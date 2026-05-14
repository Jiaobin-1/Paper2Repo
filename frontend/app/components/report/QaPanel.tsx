"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { askQuestionStream, getQaHistory } from "../../../lib/api";
import { text } from "../../../lib/i18n";
import { useAppLanguage } from "../../../lib/useAppLanguage";
import type { QaMessage } from "../../../lib/types";

export default function QaPanel({ runId }: { runId: string }) {
  const language = useAppLanguage();
  const [messages, setMessages] = useState<QaMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    let isMounted = true;
    getQaHistory(runId)
      .then((history) => {
        if (isMounted) {
          setMessages(history);
          setHistoryLoaded(true);
        }
      })
      .catch(() => {
        if (isMounted) {
      setError(text(language, "qaLoadHistoryError"));
          setHistoryLoaded(true);
        }
      });
    return () => {
      isMounted = false;
    };
  }, [runId, language]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(async () => {
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    setLoading(true);
    setError(null);
    abortRef.current?.abort();
    const abortController = new AbortController();
    abortRef.current = abortController;

    const userMsg: QaMessage = {
      id: `tmp-user-${Date.now()}`,
      run_id: runId,
      role: "user",
      content: question,
      created_at: new Date().toISOString(),
    };
    const assistantMsg: QaMessage = {
      id: `tmp-assistant-${Date.now()}`,
      run_id: runId,
      role: "assistant",
      content: "",
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    try {
      const stream = askQuestionStream(runId, question, abortController.signal);
      for await (const event of stream) {
        if (event.type === "token" && event.content) {
          assistantMsg.content += event.content;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id ? { ...m, content: assistantMsg.content } : m,
            ),
          );
        } else if (event.type === "done" && event.message_id) {
          assistantMsg.id = event.message_id;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id || m.id.startsWith("tmp-assistant-")
                ? { ...assistantMsg }
                : m,
            ),
          );
        } else if (event.type === "error") {
          const message = event.content || text(language, "qaError");
          assistantMsg.content = message;
          setError(message);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id ? { ...m, content: assistantMsg.content } : m,
            ),
          );
        }
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setError(text(language, "qaStopped"));
        try {
          setMessages(await getQaHistory(runId));
        } catch {
          // Keep the optimistic partial message if history reload fails.
        }
        return;
      }
      setError(text(language, "qaError"));
    } finally {
      if (abortRef.current === abortController) {
        abortRef.current = null;
      }
      setLoading(false);
    }
  }, [runId, input, loading, language]);

  const handleStop = useCallback(async () => {
    abortRef.current?.abort();
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  if (!historyLoaded) {
    return null;
  }

  return (
    <section className="panel stack qa-panel">
      <h2>{text(language, "qaTitle")}</h2>

      {messages.length === 0 && !loading ? (
        <p className="muted">{text(language, "qaEmpty")}</p>
      ) : null}

      <div className="qa-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`qa-message qa-message-${msg.role}`}>
            <div className="qa-message-role">{msg.role === "user" ? "You" : "AI"}</div>
            <div className="qa-message-content">
              {msg.content || (loading && msg.role === "assistant" ? text(language, "qaLoading") : "")}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {error ? <p className="qa-error">{error}</p> : null}

      <div className="qa-input-row">
        <textarea
          className="qa-input"
          placeholder={text(language, "qaPlaceholder")}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          disabled={loading}
        />
        <button
          className="button"
          onClick={loading ? handleStop : handleSend}
          disabled={!loading && !input.trim()}
          type="button"
        >
          {loading ? text(language, "qaStop") : text(language, "qaSend")}
        </button>
      </div>
    </section>
  );
}
