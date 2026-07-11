"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAppLanguage } from "@/hooks/useAppLanguage";
import { askQuestionStream, getQaHistory } from "@/lib/api";
import { text } from "@/lib/i18n";
import type { QaMessage } from "@/lib/types";

export default function QaPanel({ runId }: { runId: string }) {
  const language = useAppLanguage();
  const [messages, setMessages] = useState<QaMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const requestVersionRef = useRef(0);

  useEffect(() => {
    setLoading(false);
    setInput("");
    return () => {
      requestVersionRef.current += 1;
      const activeRequest = abortRef.current;
      abortRef.current = null;
      activeRequest?.abort();
    };
  }, [runId]);

  useEffect(() => {
    let isMounted = true;
    setHistoryLoaded(false);
    setMessages([]);
    setError(null);
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
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
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
    const requestVersion = requestVersionRef.current + 1;
    requestVersionRef.current = requestVersion;
    const requestKey = Date.now();
    const assistantTempId = `tmp-assistant-${requestKey}`;
    let assistantContent = "";

    const userMsg: QaMessage = {
      id: `tmp-user-${requestKey}`,
      run_id: runId,
      role: "user",
      content: question,
      created_at: new Date().toISOString(),
    };
    const assistantMsg: QaMessage = {
      id: assistantTempId,
      run_id: runId,
      role: "assistant",
      content: "",
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    try {
      const stream = askQuestionStream(runId, question, abortController.signal);
      for await (const event of stream) {
        if (requestVersionRef.current !== requestVersion) return;
        if (event.type === "token" && event.content) {
          assistantContent += event.content;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantTempId ? { ...m, content: assistantContent } : m,
            ),
          );
        } else if (event.type === "done" && event.message_id) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantTempId
                ? { ...m, id: event.message_id!, content: assistantContent }
                : m,
            ),
          );
        } else if (event.type === "error") {
          const message = event.content || text(language, "qaError");
          assistantContent = message;
          setError(message);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantTempId ? { ...m, content: assistantContent } : m,
            ),
          );
        }
      }
    } catch (err) {
      if (requestVersionRef.current !== requestVersion) return;
      if (err instanceof DOMException && err.name === "AbortError") {
        setError(text(language, "qaStopped"));
        try {
          const history = await getQaHistory(runId);
          if (requestVersionRef.current === requestVersion) {
            setMessages(history);
          }
        } catch {
          // Keep the optimistic partial message if history reload fails.
        }
        return;
      }
      const message = text(language, "qaError");
      assistantContent = message;
      setError(message);
      setMessages((prev) =>
        prev.map((item) =>
          item.id === assistantTempId ? { ...item, content: assistantContent } : item,
        ),
      );
    } finally {
      if (requestVersionRef.current === requestVersion && abortRef.current === abortController) {
        abortRef.current = null;
        setLoading(false);
      }
    }
  }, [runId, input, loading, language]);

  const handleStop = useCallback(() => {
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

      <div className="qa-messages" aria-live="polite" aria-busy={loading}>
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
