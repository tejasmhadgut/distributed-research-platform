import { createContext, useContext, useState, useEffect, useCallback } from "react"
import type { Session } from "../types"
import api from "../lib/api"

interface SessionsContextValue {
  sessions: Session[]
  createSession: () => Promise<Session>
  updateTitle: (id: number, title: string) => void
}

const SessionsContext = createContext<SessionsContextValue | null>(null)

export function SessionsProvider({ children }: { children: React.ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>([])

  useEffect(() => {
    api.get("/api/v1/sessions").then((r) => setSessions(r.data)).catch(() => {})
  }, [])

  const createSession = useCallback(async () => {
    const r = await api.post("/api/v1/sessions", { title: "New Research" })
    setSessions((prev) => [r.data, ...prev])
    return r.data as Session
  }, [])

  const updateTitle = useCallback((id: number, title: string) => {
    api.patch(`/api/v1/sessions/${id}`, { title }).catch(() => {})
    setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, title } : s)))
  }, [])

  return (
    <SessionsContext.Provider value={{ sessions, createSession, updateTitle }}>
      {children}
    </SessionsContext.Provider>
  )
}

export function useSessions() {
  const ctx = useContext(SessionsContext)
  if (!ctx) throw new Error("useSessions must be used within SessionsProvider")
  return ctx
}
