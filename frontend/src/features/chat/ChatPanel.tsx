import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowUp, BookOpen, Bot, Building2, LifeBuoy, RotateCcw, ThumbsDown, ThumbsUp, X } from "lucide-react";
import { api } from "../../lib/api";
import { cn, shortCompanyName } from "../../lib/format";
import type { ChatContext, ChatMode, ChatSource } from "../../lib/types";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
  interactionId?: string;
  feedback?: "positive" | "negative";
  error?: boolean;
}

interface ChatPanelProps {
  open: boolean;
  context: ChatContext;
  onClose: () => void;
  onClearContext: () => void;
}

const MODES: { id: ChatMode; label: string; icon: React.ReactNode; hint: string }[] = [
  { id: "search", label: "Продажи", icon: <Bot className="size-3.5" />, hint: "Продукты, сегменты, возражения, скрипты" },
  { id: "help", label: "Справка", icon: <LifeBuoy className="size-3.5" />, hint: "Как пользоваться системой" },
];

export function ChatPanel({ open, context, onClose, onClearContext }: ChatPanelProps) {
  const [mode, setMode] = useState<ChatMode>("search");
  const [messages, setMessages] = useState<Message[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!open) return;
    api.chatSuggestions(mode, context).then(setSuggestions).catch(() => setSuggestions([]));
  }, [open, mode, context]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open, context]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  async function send(text: string) {
    const query = text.trim();
    if (!query || busy) return;
    setInput("");
    setBusy(true);
    const assistantId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", content: query },
      { id: assistantId, role: "assistant", content: "" },
    ]);
    const update = (patch: Partial<Message> | ((m: Message) => Partial<Message>)) =>
      setMessages((prev) =>
        prev.map((m) => (m.id === assistantId ? { ...m, ...(typeof patch === "function" ? patch(m) : patch) } : m)),
      );

    try {
      const response = await api.streamChat(
        { query, mode, session_id: sessionId, context },
        (token) => update((m) => ({ content: m.content + token })),
      );
      setSessionId(response.session_id);
      update({
        content: response.answer,
        sources: response.sources,
        interactionId: response.interaction_id,
      });
      if (response.suggested_followups.length) setSuggestions(response.suggested_followups);
    } catch (e) {
      update({ content: e instanceof Error ? e.message : "Ассистент недоступен", error: true });
    } finally {
      setBusy(false);
    }
  }

  async function feedback(message: Message, value: "positive" | "negative") {
    if (!message.interactionId || message.feedback) return;
    setMessages((prev) => prev.map((m) => (m.id === message.id ? { ...m, feedback: value } : m)));
    await api.chatFeedback(message.interactionId, value).catch(() => undefined);
  }

  function reset() {
    if (sessionId) api.clearChat(sessionId).catch(() => undefined);
    setSessionId(null);
    setMessages([]);
  }

  if (!open) return null;

  return (
    <aside className="fixed inset-y-0 right-0 z-40 flex w-full max-w-[440px] flex-col border-l border-slate-200 bg-white shadow-2xl animate-slide-in">
      <header className="border-b border-slate-200 px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-violet-500 text-white">
            <Bot className="size-4" />
          </div>
          <div className="mr-auto">
            <h2 className="text-sm font-semibold text-slate-900">Ассистент НЕВАТОМ</h2>
            <p className="text-[11px] text-slate-500">Отвечает по базе знаний компании</p>
          </div>
          <button
            type="button"
            title="Новый диалог"
            aria-label="Новый диалог"
            onClick={reset}
            className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            <RotateCcw className="size-4" />
          </button>
          <button
            type="button"
            aria-label="Закрыть"
            onClick={onClose}
            className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            <X className="size-4" />
          </button>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-1 rounded-lg bg-slate-100 p-1">
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              title={m.hint}
              onClick={() => setMode(m.id)}
              className={cn(
                "inline-flex items-center justify-center gap-1.5 rounded-md py-1.5 text-xs font-medium transition-colors",
                mode === m.id ? "bg-white text-slate-900 shadow-xs" : "text-slate-500 hover:text-slate-800",
              )}
            >
              {m.icon}
              {m.label}
            </button>
          ))}
        </div>
        {context.company_name && (
          <div className="mt-2.5 flex items-center gap-2 rounded-lg bg-brand-50 px-2.5 py-1.5 text-xs text-brand-700">
            <Building2 className="size-3.5 shrink-0" />
            <span className="truncate">
              Контекст: <b>{shortCompanyName(context.company_name)}</b>
              {context.score != null && ` · ${context.score} баллов`}
            </span>
            <button
              type="button"
              aria-label="Убрать контекст"
              onClick={onClearContext}
              className="ml-auto rounded p-0.5 hover:bg-brand-100"
            >
              <X className="size-3" />
            </button>
          </div>
        )}
      </header>

      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="pt-6 text-center">
            <p className="text-sm font-medium text-slate-900">Чем помочь?</p>
            <p className="mt-1 text-xs text-slate-500">{MODES.find((m) => m.id === mode)?.hint}</p>
          </div>
        )}
        {messages.map((m) =>
          m.role === "user" ? (
            <div key={m.id} className="flex justify-end animate-fade-in">
              <div className="max-w-[85%] rounded-2xl rounded-br-md bg-brand-600 px-3.5 py-2 text-sm text-white">
                {m.content}
              </div>
            </div>
          ) : (
            <div key={m.id} className="animate-fade-in">
              <div
                className={cn(
                  "rounded-2xl rounded-bl-md px-3.5 py-2.5",
                  m.error ? "bg-red-50 text-sm text-red-700" : "bg-slate-50",
                )}
              >
                {m.content ? (
                  m.error ? (
                    m.content
                  ) : (
                    <div className="prose-chat">
                      {/* react-markdown не исполняет HTML из ответа — защита от XSS */}
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                    </div>
                  )
                ) : (
                  <TypingDots />
                )}
              </div>
              {m.sources && m.sources.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {uniqueSources(m.sources).map((s) => (
                    <span
                      key={`${s.doc_id}-${s.section}`}
                      title={s.doc_id}
                      className="inline-flex max-w-full items-center gap-1 rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-[11px] text-slate-500"
                    >
                      <BookOpen className="size-3 shrink-0" />
                      <span className="truncate">{s.section}</span>
                    </span>
                  ))}
                </div>
              )}
              {m.interactionId && (
                <div className="mt-1 flex gap-0.5">
                  {(["positive", "negative"] as const).map((value) => {
                    const Icon = value === "positive" ? ThumbsUp : ThumbsDown;
                    return (
                      <button
                        key={value}
                        type="button"
                        aria-label={value === "positive" ? "Полезный ответ" : "Неполезный ответ"}
                        disabled={!!m.feedback}
                        onClick={() => feedback(m, value)}
                        className={cn(
                          "rounded p-1 transition-colors",
                          m.feedback === value ? "text-brand-600" : "text-slate-300 hover:text-slate-600",
                          m.feedback && m.feedback !== value && "invisible",
                        )}
                      >
                        <Icon className="size-3.5" />
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          ),
        )}
      </div>

      <div className="border-t border-slate-200 p-3">
        {!busy && suggestions.length > 0 && (
          <div className="mb-2.5 flex flex-wrap gap-1.5">
            {suggestions.slice(0, 4).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => send(s)}
                className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-left text-xs text-slate-600 transition-colors hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700"
              >
                {s}
              </button>
            ))}
          </div>
        )}
        <form
          className="flex items-end gap-2 rounded-xl border border-slate-200 bg-white p-1.5 shadow-xs focus-within:border-brand-500 focus-within:ring-3 focus-within:ring-brand-100"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <textarea
            ref={inputRef}
            rows={1}
            maxLength={500}
            value={input}
            placeholder="Спросите о продукте, клиенте или системе…"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            className="max-h-32 min-h-9 flex-1 resize-none bg-transparent px-2 py-2 text-sm focus:outline-none"
          />
          <button
            type="submit"
            aria-label="Отправить"
            disabled={!input.trim() || busy}
            className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-brand-600 text-white transition-colors hover:bg-brand-700 disabled:bg-slate-200"
          >
            <ArrowUp className="size-4" />
          </button>
        </form>
      </div>
    </aside>
  );
}

function TypingDots() {
  return (
    <div className="flex gap-1 py-1.5" aria-label="Ассистент печатает">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="size-1.5 animate-bounce rounded-full bg-slate-400"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </div>
  );
}

/** Несколько фрагментов одного раздела показываем одной меткой */
function uniqueSources(sources: ChatSource[]): ChatSource[] {
  const seen = new Set<string>();
  return sources.filter((s) => {
    const key = s.section.replace(/^[^\p{L}\d]+/u, "").trim();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
