import { useEffect, useRef, useState, useCallback } from "react"
import type { Message } from "../types"

export function useWebSocket(sessionId: number | null, onTickersDetected?: (tickers: string[]) => void, onResearchEnd?: () => void) {
  const ws = useRef<WebSocket | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [connected, setConnected] = useState(false)
  const [loading, setLoading] = useState(false)
  const [statusMessage, setStatusMessage] = useState("")
  const [retrySignal, setRetrySignal] = useState(0)
  const onTickersDetectedRef = useRef(onTickersDetected)
  const onResearchEndRef = useRef(onResearchEnd)
  useEffect(() => { onTickersDetectedRef.current = onTickersDetected })
  useEffect(() => { onResearchEndRef.current = onResearchEnd })
  const intentionalClose = useRef(false)
  const retryCount = useRef(0)
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!sessionId) return

    intentionalClose.current = false
    const token = localStorage.getItem("token")
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const socket = new WebSocket(
      `${protocol}//${window.location.host}/ws/session/${sessionId}?token=${token}`
    )
    ws.current = socket

    socket.onopen = () => {
      retryCount.current = 0
      setConnected(true)
    }

    socket.onclose = () => {
      setConnected(false)
      setLoading(false)
      if (!intentionalClose.current && retryCount.current < 3) {
        retryCount.current += 1
        retryTimer.current = setTimeout(() => setRetrySignal((s) => s + 1), 1500)
      }
    }

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === "status_update") {
        setStatusMessage(data.message)
        setLoading(true)
        return
      }

      if (data.type === "tickers_detected") {
        onTickersDetectedRef.current?.(data.tickers)
        return
      }

      if (data.type === "workflow_started") return

      if (data.type === "chunk") {
        setLoading(false)
        setStatusMessage("")
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last?.role === "assistant" && last.streaming) {
            return [
              ...prev.slice(0, -1),
              { ...last, content: last.content + data.content },
            ]
          }
          return [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content: data.content,
              created_at: new Date().toISOString(),
              streaming: true,
            },
          ]
        })
        return
      }

      if (data.status === "queued" || data.status === "running") {
        setLoading(true)
        return
      }

      if (data.status === "completed") {
        setLoading(false)
        setStatusMessage("")
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last?.streaming) {
            return [...prev.slice(0, -1), { ...last, streaming: false }]
          }
          return prev
        })
        onResearchEndRef.current?.()
        return
      }

      if (data.status === "failed") {
        setLoading(false)
        setStatusMessage("")
        onResearchEndRef.current?.()
      }
    }

    return () => {
      if (retryTimer.current) clearTimeout(retryTimer.current)
      const alreadyClosed = socket.readyState === WebSocket.CLOSED
      intentionalClose.current = true
      socket.close()
      setConnected(false)
      setLoading(false)
      if (!alreadyClosed) {
        setMessages([])
      } else {
        setMessages((prev) =>
          prev.map((m) => (m.streaming ? { ...m, streaming: false } : m))
        )
      }
    }
  }, [sessionId, retrySignal])

  const send = useCallback((question: string, ticker: string, tickers?: string[]) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return
    ws.current.send(JSON.stringify({ question, ticker, tickers }))
    const label =
      tickers && tickers.length > 1
        ? `[${tickers.join(" vs ")}] ${question}`
        : ticker
        ? `[${ticker.toUpperCase()}] ${question}`
        : question
    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: label,
        created_at: new Date().toISOString(),
      },
    ])
  }, [])

  const setInitialMessages = useCallback((msgs: Message[]) => {
    setMessages(msgs)
  }, [])

  return { messages, connected, loading, statusMessage, send, setInitialMessages }
}
