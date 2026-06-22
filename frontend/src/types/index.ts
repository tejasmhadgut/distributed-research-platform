export interface Session {
  id: number
  title: string
  description?: string
}

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  created_at: string
  streaming?: boolean
}
