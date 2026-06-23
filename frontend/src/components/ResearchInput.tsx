import { useState, type KeyboardEvent } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

interface Props {
  onSend: (question: string, ticker: string, tickers?: string[]) => void
  connected: boolean
}

export default function ResearchInput({ onSend, connected }: Props) {
  const [question, setQuestion] = useState("")
  const [ticker, setTicker] = useState("")
  const [ticker2, setTicker2] = useState("")
  const [compareMode, setCompareMode] = useState(false)

  function submit() {
    const q = question.trim()
    if (!q || !connected) return
    if (compareMode) {
      const t1 = ticker.trim().toUpperCase()
      const t2 = ticker2.trim().toUpperCase()
      if (!t1 || !t2) return
      onSend(q, t1, [t1, t2])
    } else {
      onSend(q, ticker.trim().toUpperCase())
    }
    setQuestion("")
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const canSend = connected && !!question.trim() && (compareMode ? !!ticker.trim() && !!ticker2.trim() : true)

  return (
    <div className="border-t border-border px-4 py-3 space-y-2 bg-background">
      <div className="flex items-center gap-2">
        <Input
          className="w-24 shrink-0 uppercase text-xs h-8"
          placeholder={compareMode ? "Ticker 1" : "AAPL (optional)"}
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          disabled={!connected}
          maxLength={10}
        />
        {compareMode && (
          <>
            <span className="text-xs text-muted-foreground">vs</span>
            <Input
              className="w-24 shrink-0 uppercase text-xs h-8"
              placeholder="Ticker 2"
              value={ticker2}
              onChange={(e) => setTicker2(e.target.value.toUpperCase())}
              disabled={!connected}
              maxLength={10}
            />
          </>
        )}
        <button
          className={`ml-auto text-xs px-2 py-1 rounded-md border transition-colors ${
            compareMode
              ? "border-primary text-primary bg-primary/10"
              : "border-border text-muted-foreground hover:border-primary hover:text-primary"
          }`}
          onClick={() => { setCompareMode((m) => !m); setTicker2("") }}
        >
          Compare
        </button>
      </div>
      <div className="flex gap-2 items-end">
        <textarea
          className="flex-1 resize-none bg-muted rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring min-h-[40px] max-h-[120px]"
          rows={1}
          placeholder={
            !connected
              ? "Connecting…"
              : compareMode
              ? "e.g. Which company has better margins and growth prospects?"
              : "Ask a research question…"
          }
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={!connected}
        />
        <Button size="sm" onClick={submit} disabled={!canSend}>
          Send
        </Button>
      </div>
    </div>
  )
}
