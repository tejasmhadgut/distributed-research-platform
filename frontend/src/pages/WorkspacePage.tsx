import { useEffect, useCallback, useState } from "react"
import { useParams } from "react-router-dom"
import Sidebar from "../components/Sidebar"
import ResearchThread from "../components/ResearchThread"
import ResearchInput from "../components/ResearchInput"
import DataPanel from "../components/DataPanel"
import { useWebSocket } from "../hooks/useWebSocket"
import { useSessions } from "../contexts/SessionsContext"
import api from "../lib/api"

export default function WorkspacePage() {
  const { sessionId } = useParams()
  const id = sessionId ? parseInt(sessionId) : null
  const { messages, connected, loading, send, setInitialMessages } = useWebSocket(id)
  const { sessions, updateTitle } = useSessions()
  const currentSession = sessions.find((s) => s.id === id)
  const [currentTicker, setCurrentTicker] = useState<string | null>(null)

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
    if (ticker) setCurrentTicker(ticker.toUpperCase())
    send(question, ticker, tickers)
  }, [id, messages.length, send, updateTitle])

  useEffect(() => {
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
      }
    })
  }, [id, setInitialMessages])

  return (
    <div className="flex h-screen bg-background text-foreground">
      <Sidebar />
      <main className="flex flex-col flex-1 overflow-hidden">
        {id ? (
          <>
            <div className="px-6 py-3 border-b border-border flex items-center gap-2">
              <span className="text-sm font-medium">{currentSession?.title ?? `Session ${id}`}</span>
              <span className={`ml-auto text-xs ${connected ? "text-green-500" : "text-muted-foreground"}`}>
                {connected ? "● connected" : "○ connecting"}
              </span>
            </div>
            <div className="flex flex-1 overflow-hidden">
              <div className="flex flex-col flex-1 overflow-hidden">
                <ResearchThread messages={messages} loading={loading} />
                <ResearchInput onSend={handleSend} connected={connected} />
              </div>
              {currentTicker && <DataPanel ticker={currentTicker} />}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
            Select or create a session to get started.
          </div>
        )}
      </main>
    </div>
  )
}
