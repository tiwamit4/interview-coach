import { useEffect, useState } from "react";
import { Clock3, RefreshCw } from "lucide-react";
import { api } from "../lib/api";
import type { HistoryItem, Result } from "../lib/types";
import { Card, EmptyState, ErrorNotice, PageHeader } from "../components/ui";
import { Downloads, ResultView } from "../components/Results";
export default function History() {
  const [items, setItems] = useState<HistoryItem[]>([]),
    [selected, setSelected] = useState<HistoryItem | null>(null),
    [search, setSearch] = useState(""),
    [limit, setLimit] = useState("50"),
    [error, setError] = useState<unknown>(null),
    [busy, setBusy] = useState(false),
    [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setBusy(true);
    api<{ items: HistoryItem[] }>(`/history?limit=${limit}`, {
      signal: controller.signal,
    })
      .then((data) => setItems(data.items))
      .catch((e) => {
        if (!controller.signal.aborted) setError(e);
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(false);
      });
    return () => controller.abort();
  }, [version, limit]);
  async function open(item: HistoryItem) {
    setBusy(true);
    setError(null);
    try {
      setSelected(await api<HistoryItem>(`/history/${item.id}`));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  const filtered = items.filter((item) =>
    `${item.title} ${item.event_type}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  return (
    <>
      <PageHeader
        eyebrow="YOUR PREPARATION, SAVED"
        title="Pick up where you left off."
        description="Revisit generated questions, feedback, and the materials you’ve created."
      >
        <button
          className="button secondary"
          disabled={busy}
          onClick={() => setVersion((v) => v + 1)}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </PageHeader>
      <ErrorNotice error={error} />
      <Card>
        <div className="filter-row">
          <label>
            Search history
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Find a role, resume, or activity"
            />
          </label>
          <label>
            Show
            <select value={limit} onChange={(e) => setLimit(e.target.value)}>
              {[25, 50, 100, 200].map((n) => (
                <option key={n}>{n}</option>
              ))}
            </select>
          </label>
        </div>
        {busy && (
          <p role="status" className="muted">
            Loading history…
          </p>
        )}
        {filtered.length ? (
          <div className="history-list">
            {filtered.map((item) => (
              <button
                className={`history-item ${selected?.id === item.id ? "selected" : ""}`}
                key={item.id}
                disabled={busy}
                onClick={() => void open(item)}
              >
                <div className="history-icon">
                  <Clock3 size={19} />
                </div>
                <div>
                  <strong>{item.title}</strong>
                  <span>{item.event_type.replaceAll("_", " ")}</span>
                </div>
                <time>{new Date(item.created_at).toLocaleString()}</time>
              </button>
            ))}
          </div>
        ) : (
          !busy && (
            <EmptyState
              title={
                search
                  ? "No matching results"
                  : "A little history starts with a first step"
              }
              description={
                search
                  ? "Try a different search or increase the number of entries shown."
                  : "Your generated materials will appear here after you use a workflow."
              }
            />
          )
        )}
      </Card>
      {selected?.payload && (
        <>
          <div className="section-heading">
            <h2>{selected.title}</h2>
          </div>
          {selected.payload.transcript ? (
            <Card>
              <h3>Saved transcript</h3>
              <p className="pre-wrap">{String(selected.payload.transcript)}</p>
              <Downloads result={selected.payload} />
            </Card>
          ) : (
            <ResultView result={selected.payload as Result} />
          )}
        </>
      )}
    </>
  );
}
