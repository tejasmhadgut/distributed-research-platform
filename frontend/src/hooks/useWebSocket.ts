import { useEffect, useRef, useState, useCallback } from "react"
import { Message } from "../types"

export function useWebSocket(sessionId: number | null) {
  const ws = useRef<WebSocket | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [connected, setConnected] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!sessionId) return

    const token = localStorage.getItem("token")
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const socket = new WebSocket(
      `${protocol}//${window.location.host}/ws/session/${sessionId}?token=${token}`
    )
    ws.current = socket

    socket.onopen = () => setConnected(true)
    socket.onclose = () => { setConnected(false); setLoading(false) }
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === "workflow_started") return

      if (data.type === "chunk") {
        setLoading(false)
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
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last?.streaming) {
            return [...prev.slice(0, -1), { ...last, streaming: false }]
          }
          return prev
        })
        return
      }

      if (data.status === "failed") {
        setLoading(false)
      }
    }

    return () => {
      socket.close()
      setConnected(false)
      setLoading(false)
      setMessages([])
    }
  }, [sessionId])

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

  return { messages, connected, loading, send, setInitialMessages }
}
