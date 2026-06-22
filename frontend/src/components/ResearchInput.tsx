import { useState, KeyboardEvent } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

interface Props {
  onSend: (question: string, ticker: string) => void
  connected: boolean
}

export default function ResearchInput({ onSend, connected }: Props) {
  const [question, setQuestion] = useState("")
  const [ticker, setTicker] = useState("")

  function submit() {
    const q = question.trim()
    if (!q || !connected) return
    onSend(q, ticker.trim())
    setQuestion("")
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="border-t border-border px-4 py-3 flex gap-2 items-end bg-background">
      <Input
        className="w-24 shrink-0"
        placeholder="Ticker"
        value={ticker}
        onChange={(e) => setTicker(e.target.value.toUpperCase())}
        disabled={!connected}
        maxLength={10}
      />
      <textarea
        className="flex-1 resize-none bg-muted rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring min-h-[40px] max-h-[120px]"
        rows={1}
        placeholder={connected ? "Ask a research question…" : "Connecting…"}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={!connected}
      />
      <Button size="sm" onClick={submit} disabled={!connected || !question.trim()}>
        Send
      </Button>
    </div>
  )
}
