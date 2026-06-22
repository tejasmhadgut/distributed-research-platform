import { useState, useRef } from "react"
import { Link, useParams, useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { useAuth } from "../contexts/AuthContext"
import { useSessions } from "../contexts/SessionsContext"

export default function Sidebar() {
  const { logout } = useAuth()
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const { sessions, createSession, updateTitle } = useSessions()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editValue, setEditValue] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleCreate() {
    const session = await createSession()
    navigate(`/session/${session.id}`)
  }

  function startEditing(id: number, currentTitle: string, e: React.MouseEvent) {
    e.preventDefault()
    setEditingId(id)
    setEditValue(currentTitle)
    setTimeout(() => inputRef.current?.select(), 0)
  }

  function commitEdit(id: number) {
    const trimmed = editValue.trim()
    if (trimmed && trimmed !== sessions.find((s) => s.id === id)?.title) {
      updateTitle(id, trimmed)
    }
    setEditingId(null)
  }

  return (
    <aside className="w-64 h-screen flex flex-col border-r border-border bg-card shrink-0">
      <div className="p-4">
        <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">
          Research Platform
        </p>
        <Button className="w-full" size="sm" onClick={handleCreate}>
          + New Session
        </Button>
      </div>
      <Separator />
      <ScrollArea className="flex-1 px-2 py-2">
        {sessions.map((s) => (
          <Link key={s.id} to={`/session/${s.id}`} onClick={(e) => editingId === s.id && e.preventDefault()}>
            <div
              className={`group px-3 py-2 rounded-md text-sm cursor-pointer hover:bg-accent transition-colors flex items-center gap-1 ${
                String(s.id) === sessionId
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground"
              }`}
            >
              {editingId === s.id ? (
                <input
                  ref={inputRef}
                  className="flex-1 bg-transparent outline-none min-w-0"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  onBlur={() => commitEdit(s.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commitEdit(s.id)
                    if (e.key === "Escape") setEditingId(null)
                  }}
                  onClick={(e) => e.preventDefault()}
                />
              ) : (
                <>
                  <span className="truncate flex-1">{s.title}</span>
                  <span
                    className="opacity-0 group-hover:opacity-60 text-xs px-1 shrink-0"
                    onClick={(e) => startEditing(s.id, s.title, e)}
                  >
                    ✎
                  </span>
                </>
              )}
            </div>
          </Link>
        ))}
      </ScrollArea>
      <Separator />
      <div className="p-4">
        <Button variant="ghost" size="sm" className="w-full text-muted-foreground" onClick={logout}>
          Log out
        </Button>
      </div>
    </aside>
  )
}
