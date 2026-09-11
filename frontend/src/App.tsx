import { Routes, Route, Navigate, useParams } from "react-router-dom"
import { useAuth } from "./contexts/AuthContext"
import { SessionsProvider } from "./contexts/SessionsContext"
import LoginPage from "./pages/LoginPage"
import RegisterPage from "./pages/RegisterPage"
import WorkspacePage from "./pages/WorkspacePage"
import Sidebar from "./components/Sidebar"

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function KeyedWorkspace() {
  const { sessionId } = useParams()
  return (
    <SessionsProvider>
      <div className="flex h-screen overflow-hidden bg-background text-foreground">
        <Sidebar />
        <WorkspacePage key={sessionId ?? "home"} />
      </div>
    </SessionsProvider>
  )
}

export default function App() {
  return (
    <div>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/session/:sessionId" element={
          <ProtectedRoute><KeyedWorkspace /></ProtectedRoute>
        } />
        <Route path="*" element={
          <ProtectedRoute><KeyedWorkspace /></ProtectedRoute>
        } />
      </Routes>
    </div>
  )
}
