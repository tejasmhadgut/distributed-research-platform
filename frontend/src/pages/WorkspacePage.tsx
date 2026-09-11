import { useEffect, useCallback, useState } from "react"
import { useParams } from "react-router-dom"
import ResearchThread from "../components/ResearchThread"
import ResearchInput from "../components/ResearchInput"
import DataPanel from "../components/DataPanel"
import { useWebSocket } from "../hooks/useWebSocket"
import { useSessions } from "../contexts/SessionsContext"
import api from "../lib/api"

export default function WorkspacePage() {
  const { sessionId } = useParams()
  const id = sessionId ? parseInt(sessionId) : null
  const [currentTickers, setCurrentTickers] = useState<string[]>([])
  const [extracting, setExtracting] = useState(false)
  const [showDataPanel, setShowDataPanel] = useState(false)
  const { messages, connected, loading, statusMessage, send, setInitialMessages } = useWebSocket(
    id,
    (tickers) => { setCurrentTickers(tickers); setExtracting(false); setShowDataPanel(true) },
    () => { setExtracting(false) },
  )

  const { sessions, updateTitle } = useSessions()
  const currentSession = sessions.find((s) => s.id === id)

  const loadHistory = useCallback(() => {
    if (!id) return
    api.get(`/api/v1/sessions/${id}/history`).then((r) => {
      if (r.data.length > 0) {
        setInitialMessages(
          r.data.map((m: { role: string; content: string; created_at: string }) => ({
            id: crypto.randomUUID(),
            role: m.role as "user" | "assistant",
            content: m.content,
            created_at: m.created_at,
          }))
        )
        const title = sessions.find((s) => s.id === id)?.title ?? ""
        const match = title.match(/^\[([^\]]+)\]/)
        if (match) {
          const tickers = match[1].split(" vs ").map((t) => t.trim().toUpperCase())
          setCurrentTickers(tickers)
          setShowDataPanel(true)
        }
      }
    })
  }, [id, setInitialMessages, sessions])

  const handleSend = useCallback((question: string, ticker: string, tickers?: string[]) => {
    if (id && messages.length === 0) {
      const label =
        tickers && tickers.length > 1
          ? `[${tickers.join(" vs ")}] ${question}`
          : ticker
          ? `[${ticker.toUpperCase()}] ${question}`
          : question
      updateTitle(id, label.slice(0, 60))
    }
    if (tickers && tickers.length > 1) {
      setCurrentTickers(tickers.map((t) => t.toUpperCase()))
      setShowDataPanel(true)
    } else if (ticker) {
      setCurrentTickers([ticker.toUpperCase()])
      setShowDataPanel(true)
    } else {
      setExtracting(true)
    }
    send(question, ticker, tickers)
  }, [id, messages.length, send, updateTitle])

  useEffect(() => { loadHistory() }, [loadHistory])

  return (
    <main className="flex flex-col flex-1 min-h-0 overflow-hidden">
        {id ? (
          <>
            <div className="px-6 py-3 border-b border-border flex items-center gap-2">
              <span className="text-sm font-medium">{currentSession?.title ?? `Session ${id}`}</span>
              <div className="ml-auto flex items-center gap-3">
                {currentTickers.length > 0 && (
                  <button
                    onClick={() => setShowDataPanel((v) => !v)}
                    className="text-xs px-2 py-1 rounded border border-border hover:bg-accent transition-colors"
                  >
                    {showDataPanel ? "Hide Data" : `Show Data (${currentTickers.join(", ")})`}
                  </button>
                )}
                <span className={`text-xs ${connected ? "text-green-500" : "text-muted-foreground"}`}>
                  {connected ? "● connected" : "○ connecting"}
                </span>
              </div>
            </div>
            <div className="flex flex-1 min-h-0 overflow-hidden">
              <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
                <ResearchThread messages={messages} loading={loading} statusMessage={statusMessage} />
                <ResearchInput onSend={handleSend} connected={connected} />
              </div>
              {(extracting || (showDataPanel && currentTickers.length > 0)) && <DataPanel tickers={currentTickers} researchLoading={loading} extracting={extracting} statusMessage={statusMessage} />}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
            Select or create a session to get started.
          </div>
        )}
    </main>
  )
}
