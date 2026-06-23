import axios from "axios"

const api = axios.create({
  baseURL: "",
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token")
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const url: string = error.config?.url ?? ""
    const isAuthEndpoint = url.includes("/auth/")
    if (!isAuthEndpoint && (status === 401 || status === 403)) {
      window.dispatchEvent(new CustomEvent("auth:expired"))
    }
    return Promise.reject(error)
  }
)

export default api
