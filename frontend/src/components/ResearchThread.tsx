import { useEffect, useRef } from "react"
import type { Message } from "../types"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

interface Props {
  messages: Message[]
  loading: boolean
  statusMessage?: string
}

export default function ResearchThread({ messages, loading, statusMessage }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  if (messages.length === 0 && !loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center px-8">
        <p className="text-muted-foreground text-sm">Ask a research question to get started.</p>
        <p className="text-muted-foreground text-xs">
          Try: <span className="text-foreground">Is Apple fairly valued?</span> or use Compare mode to analyse two companies side by side.
        </p>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
      {messages.map((m) => (
        <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
          {m.role === "user" ? (
            <div className="max-w-[70%] px-4 py-2 rounded-lg text-sm bg-primary text-primary-foreground">
              {m.content}
            </div>
          ) : (
            <div className="max-w-[80%] px-4 py-3 rounded-lg text-sm bg-muted text-foreground prose prose-sm prose-neutral dark:prose-invert max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {m.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
      ))}
      {loading && (
        <div className="flex justify-start">
          <div className="bg-muted px-4 py-3 rounded-lg flex items-center gap-2 text-sm text-muted-foreground">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:0ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:150ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:300ms]" />
            {statusMessage && (
              <span className="ml-1 text-xs">{statusMessage}</span>
            )}
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
