import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import TypingIndicator from "./TypingIndicator.jsx";

// Re-parsed on every token update while streaming, so formatting (bold,
// lists, code, etc.) appears live rather than waiting for the full
// response to land. A half-typed marker (e.g. "**RAG" with no closing
// "**" yet) simply renders as plain text for a moment, then snaps into
// its formatted form once the closing marker arrives — expected and
// harmless, the same behavior you'd see in most streaming chat UIs.
const markdownComponents = {
  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  ul: ({ children }) => <ul className="mb-2 last:mb-0 pl-5 list-disc space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="mb-2 last:mb-0 pl-5 list-decimal space-y-1">{children}</ol>,
  li: ({ children }) => <li className="pl-0.5">{children}</li>,
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-accent underline underline-offset-2 hover:opacity-80"
    >
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-line pl-3 my-2 text-ink-soft">{children}</blockquote>
  ),
  code: ({ inline, children }) =>
    inline ? (
      <code className="px-1 py-0.5 rounded bg-ink/10 text-[13px] font-mono">{children}</code>
    ) : (
      <code className="block font-mono text-[13px] whitespace-pre-wrap">{children}</code>
    ),
  pre: ({ children }) => (
    <pre className="mb-2 last:mb-0 rounded-lg bg-ink/5 border border-line p-3 overflow-x-auto">
      {children}
    </pre>
  ),
  h1: ({ children }) => <h1 className="text-lg font-semibold mb-2 mt-1">{children}</h1>,
  h2: ({ children }) => <h2 className="text-base font-semibold mb-2 mt-1">{children}</h2>,
  h3: ({ children }) => <h3 className="text-[15px] font-semibold mb-1 mt-1">{children}</h3>,
  hr: () => <hr className="border-line my-2" />,
};

export default function MessageBubble({ role, content, streaming, error }) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={[
          "max-w-[80%] sm:max-w-[70%] rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed break-words",
          isUser
            ? "bg-accent text-white rounded-br-sm whitespace-pre-wrap"
            : "bg-card border border-line text-ink rounded-bl-sm",
          error ? "border border-danger/40 text-danger" : "",
        ].join(" ")}
      >
        {content ? (
          isUser ? (
            // User's own input stays plain text — no need to parse markdown
            // out of something they typed themselves.
            content
          ) : (
            <>
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkBreaks]}
                components={markdownComponents}
              >
                {content}
              </ReactMarkdown>
              {streaming && (
                <span className="inline-block w-[2px] h-4 -mb-0.5 ml-0.5 bg-ink-soft animate-blink align-middle" />
              )}
            </>
          )
        ) : streaming ? (
          <TypingIndicator />
        ) : null}
      </div>
    </div>
  );
}
