import { useEffect, useState, useRef } from "react"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import api from "../lib/api"

interface Metrics {
  ticker: string
  fetched_at: string
  price_data: Record<string, number | null>
  income_statement: Record<string, number | null>
  balance_sheet: Record<string, number | null>
}

interface Filing {
  id: number
  form_type: string
  filed_at: string
  filing_url: string
}

interface QuantData {
  metrics: Record<string, number | string | null>
}

interface SearchResult {
  id: number
  chunk_index: number
  text: string
  similarity: number
}

function fmt(n: number | null | undefined, decimals = 2): string {
  if (n == null) return "—"
  if (Math.abs(n) >= 1e12) return `$${(n / 1e12).toFixed(decimals)}T`
  if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(decimals)}B`
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(decimals)}M`
  return n.toFixed(decimals)
}

function pct(n: number | null | undefined): string {
  if (n == null) return "—"
  return `${(n * 100).toFixed(1)}%`
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] text-muted-foreground uppercase tracking-wide">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  )
}

export default function DataPanel({ ticker }: { ticker: string }) {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [filings, setFilings] = useState<Filing[]>([])
  const [quant, setQuant] = useState<QuantData | null>(null)
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!ticker) return
    setLoading(true)
    setMetrics(null)
    setFilings([])
    setQuant(null)
    setSearchResults([])
    setSearchQuery("")

    const fetchQuant = async () => {
      try {
        const r = await api.get(`/api/v1/quant/${ticker}`)
        return r.data
      } catch (e: any) {
        if (e?.response?.status === 404) {
          try {
            await api.post("/api/v1/quant/", { ticker })
            const r = await api.get(`/api/v1/quant/${ticker}`)
            return r.data
          } catch {
            return null
          }
        }
        return null
      }
    }

    Promise.all([
      api.get(`/api/v1/financial/metrics/${ticker}`).catch(() => null),
      api.get(`/api/v1/financial/filings/${ticker}`).catch(() => null),
      fetchQuant(),
    ]).then(([m, f, q]) => {
      if (m) setMetrics(m.data)
      if (f) setFilings(f.data)
      if (q) setQuant(q)
      setLoading(false)
    })
  }, [ticker])

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!searchQuery.trim()) return
    setSearching(true)
    setSearchResults([])
    try {
      const r = await api.post("/api/v1/documents/search", {
        query: searchQuery,
        ticker,
        limit: 5,
      })
      setSearchResults(r.data.results ?? [])
    } catch {
      setSearchResults([])
    }
    setSearching(false)
  }

  const p = metrics?.price_data ?? {}
  const inc = metrics?.income_statement ?? {}
  const bal = metrics?.balance_sheet ?? {}
  const qm = quant?.metrics ?? {}

  return (
    <aside className="w-72 shrink-0 border-l border-border flex flex-col bg-card">
      <div className="px-4 py-3 border-b border-border">
        <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          {ticker}
        </span>
        {metrics && (
          <p className="text-[11px] text-muted-foreground mt-0.5">
            Updated {new Date(metrics.fetched_at).toLocaleDateString()}
          </p>
        )}
      </div>

      {loading && (
        <div className="flex-1 flex items-center justify-center text-xs text-muted-foreground">
          Loading data…
        </div>
      )}

      {!loading && (
        <Tabs defaultValue="overview" className="flex flex-col flex-1 overflow-hidden">
          <TabsList className="mx-3 mt-2 mb-1 h-8">
            <TabsTrigger value="overview" className="text-xs flex-1">Overview</TabsTrigger>
            <TabsTrigger value="filings" className="text-xs flex-1">Filings</TabsTrigger>
            <TabsTrigger value="search" className="text-xs flex-1">Search</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="flex-1 overflow-hidden m-0">
            <ScrollArea className="h-full px-4 pb-4">
              {!metrics ? (
                <p className="text-xs text-muted-foreground pt-4">No data available. Run a research query on {ticker} first.</p>
              ) : (
                <div className="space-y-5 pt-3">
                  <section>
                    <h3 className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">Price</h3>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-3">
                      <Stat label="Current" value={fmt(p.current_price as number)} />
                      <Stat label="P/E Ratio" value={p.pe_ratio != null ? String((p.pe_ratio as number).toFixed(1)) : "—"} />
                      <Stat label="52W High" value={fmt(p.fifty_two_week_high as number)} />
                      <Stat label="52W Low" value={fmt(p.fifty_two_week_low as number)} />
                      <Stat label="Market Cap" value={fmt(p.market_cap as number)} />
                      <Stat label="vs 52W High" value={pct(qm.price_vs_52w_high as number)} />
                    </div>
                  </section>

                  <section>
                    <h3 className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">Income</h3>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-3">
                      <Stat label="Revenue" value={fmt(inc.total_revenue as number)} />
                      <Stat label="Net Income" value={fmt(inc.net_income as number)} />
                      <Stat label="Net Margin" value={pct(qm.net_margin as number)} />
                    </div>
                  </section>

                  <section>
                    <h3 className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">Balance Sheet</h3>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-3">
                      <Stat label="Total Assets" value={fmt(bal.total_assets as number)} />
                      <Stat label="Total Debt" value={fmt(bal.total_debt as number)} />
                      <Stat label="Debt / Assets" value={pct(qm.debt_to_assets as number)} />
                      <Stat label="Cap Tier" value={qm.cap_tier ? String(qm.cap_tier) : "—"} />
                    </div>
                  </section>
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          <TabsContent value="filings" className="flex-1 overflow-hidden m-0">
            <ScrollArea className="h-full px-4 pb-4">
              {filings.length === 0 ? (
                <p className="text-xs text-muted-foreground pt-4">No filings found for {ticker}.</p>
              ) : (
                <div className="space-y-2 pt-3">
                  {filings.map((f) => (
                    <a
                      key={f.id}
                      href={f.filing_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-between px-3 py-2 rounded-md hover:bg-accent transition-colors group"
                    >
                      <div>
                        <span className="text-xs font-medium">{f.form_type}</span>
                        <p className="text-[11px] text-muted-foreground">{f.filed_at}</p>
                      </div>
                      <span className="text-[11px] text-muted-foreground group-hover:text-foreground">↗</span>
                    </a>
                  ))}
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          <TabsContent value="search" className="flex-1 overflow-hidden m-0 flex flex-col">
            <form onSubmit={handleSearch} className="px-3 pt-3 pb-2 flex gap-2">
              <input
                ref={inputRef}
                className="flex-1 text-xs bg-background border border-border rounded-md px-3 py-1.5 outline-none focus:ring-1 focus:ring-ring"
                placeholder={`Search ${ticker} filings…`}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <button
                type="submit"
                disabled={searching}
                className="text-xs px-3 py-1.5 rounded-md bg-primary text-primary-foreground disabled:opacity-50"
              >
                {searching ? "…" : "Go"}
              </button>
            </form>
            <ScrollArea className="flex-1 px-3 pb-4">
              {searchResults.length === 0 && !searching && (
                <p className="text-xs text-muted-foreground px-1 pt-2">
                  Search the full text of {ticker} SEC filings using semantic similarity.
                </p>
              )}
              {searchResults.map((r) => (
                <div key={r.id} className="mb-3 p-3 rounded-md bg-accent/50 text-xs">
                  <div className="flex justify-between mb-1">
                    <span className="text-muted-foreground">Chunk {r.chunk_index}</span>
                    <span className="text-muted-foreground">{(r.similarity * 100).toFixed(0)}% match</span>
                  </div>
                  <p className="leading-relaxed line-clamp-6">{r.text}</p>
                </div>
              ))}
            </ScrollArea>
          </TabsContent>
        </Tabs>
      )}
    </aside>
  )
}
