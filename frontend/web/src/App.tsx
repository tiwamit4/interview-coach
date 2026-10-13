import { useCallback, useEffect, useState } from "react";
import {
  ArrowUpRight,
  AudioLines,
  BookOpen,
  BriefcaseBusiness,
  ChartNoAxesCombined,
  ChevronRight,
  Compass,
  FilePenLine,
  History as HistoryIcon,
  Layers3,
  Menu,
  MessageCircleQuestion,
  RefreshCw,
  Sun,
  Moon,
  Target,
  X,
} from "lucide-react";
import { api } from "./lib/api";
import type { UIConfig } from "./lib/types";
import { Workflows, workflows, type WorkflowKey } from "./pages/Workflows";
import Voice from "./pages/Voice";
import Sessions from "./pages/Sessions";
import ProgressPage from "./pages/Progress";
import History from "./pages/History";
import { ErrorNotice } from "./components/ui";
const navigation = [
  { id: "analyze", label: "Analyze fit", icon: Target, group: "PREPARE" },
  { id: "questions", label: "Questions", icon: MessageCircleQuestion },
  { id: "prep", label: "Interview prep", icon: BookOpen },
  { id: "resume", label: "Resume optimizer", icon: FilePenLine },
  { id: "applications", label: "Application writer", icon: BriefcaseBusiness },
  { id: "full", label: "Full analysis", icon: Layers3 },
  { id: "voice", label: "Voice practice", icon: AudioLines, group: "PRACTISE" },
  { id: "sessions", label: "Interview sessions", icon: Compass },
  {
    id: "progress",
    label: "Progress",
    icon: ChartNoAxesCombined,
    group: "REFLECT",
  },
  { id: "history", label: "History", icon: HistoryIcon },
];
export default function App() {
  const [page, setPage] = useState(() =>
      navigation.some((item) => item.id === location.hash.slice(1))
        ? location.hash.slice(1)
        : "analyze",
    ),
    [visited, setVisited] = useState(new Set<string>()),
    [menu, setMenu] = useState(false),
    [dark, setDark] = useState(
      () => localStorage.getItem("interview-coach-theme") === "dark",
    ),
    [config, setConfig] = useState<UIConfig | null>(null),
    [error, setError] = useState<unknown>(null),
    [connecting, setConnecting] = useState(false),
    [connection, setConnection] = useState(0),
    [draft, setDraft] = useState("");
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("interview-coach-theme", dark ? "dark" : "light");
  }, [dark]);
  useEffect(() => {
    const update = () => {
      const next = location.hash.slice(1);
      if (navigation.some((item) => item.id === next)) setPage(next);
    };
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  useEffect(() => {
    setVisited((old) => new Set([...old, page]));
  }, [page]);
  useEffect(() => {
    const controller = new AbortController();
    setConnecting(true);
    setError(null);
    api<UIConfig>("/ui-config", { signal: controller.signal })
      .then(setConfig)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e);
      })
      .finally(() => {
        if (!controller.signal.aborted) setConnecting(false);
      });
    return () => controller.abort();
  }, [connection]);
  const navigate = (id: string) => {
    location.hash = id;
    setPage(id);
    setMenu(false);
  };
  const practice = useCallback((text: string) => {
    setDraft(text);
    location.hash = "sessions";
    setPage("sessions");
    setMenu(false);
  }, []);
  const clearDraft = useCallback(() => setDraft(""), []);
  const current = navigation.find((item) => item.id === page)!;
  return (
    <div className="app-shell">
      <aside className={`sidebar ${menu ? "open" : ""}`}>
        <a
          href="#analyze"
          className="brand"
          onClick={() => navigate("analyze")}
        >
          <span className="brand-mark">
            <Compass size={24} />
          </span>
          <span>
            interview
            <span className="brand-second">
              coach<span className="brand-dot">.</span>
            </span>
          </span>
        </a>
        <button
          className="mobile-close icon-button"
          aria-label="Close navigation"
          onClick={() => setMenu(false)}
        >
          <X />
        </button>
        <p className="sidebar-intro">
          A little more ready.
          <br />A lot more confident.
        </p>
        <nav aria-label="Main navigation">
          {navigation.map(({ id, label, icon: Icon, group }) => (
            <div key={id}>
              {group && <p className="nav-group">{group}</p>}
              <button
                className={`nav-item ${page === id ? "active" : ""}`}
                aria-current={page === id ? "page" : undefined}
                onClick={() => navigate(id)}
              >
                <Icon size={18} />
                {label}
                {page === id && <ChevronRight size={15} />}
              </button>
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="coach-note">
            <span className="tiny-star">✳</span>
            <p>
              Confidence comes
              <br />
              from showing up.
            </p>
            <small>Make time for one more answer.</small>
          </div>
          <button className="theme-toggle" onClick={() => setDark(!dark)}>
            {dark ? <Sun size={17} /> : <Moon size={17} />}{" "}
            {dark ? "Light appearance" : "Dark appearance"}
          </button>
        </div>
      </aside>
      {menu && <div className="sidebar-scrim" onClick={() => setMenu(false)} />}
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="mobile-menu icon-button"
              aria-label="Open navigation"
              onClick={() => setMenu(true)}
            >
              <Menu size={21} />
            </button>
            <span>Your workspace</span>
            <ChevronRight size={13} />
            <strong>{current.label}</strong>
          </div>
          <span className={`connection ${config && !error ? "online" : ""}`}>
            <i />
            {connecting
              ? "Connecting…"
              : config && !error
                ? "Backend connected"
                : "Backend unavailable"}
          </span>
        </header>
        <main>
          <div className="workspace-label">
            <span>
              <i /> YOUR NEXT CHAPTER STARTS HERE
            </span>
            <a
              href={
                import.meta.env.VITE_API_DOCS_URL ||
                "http://localhost:8000/docs"
              }
              target="_blank"
              rel="noreferrer"
            >
              API docs <ArrowUpRight size={14} />
            </a>
          </div>
          {Boolean(error) && (
            <div className="connection-error">
              <ErrorNotice error={error} />
              <button
                className="button secondary"
                onClick={() => setConnection((n) => n + 1)}
              >
                <RefreshCw size={16} />
                Reconnect
              </button>
            </div>
          )}
          {!config ? (
            <div className="initial-state">
              <Compass size={40} />
              <h1>
                {connecting
                  ? "Getting your workspace ready…"
                  : "Let’s connect your workspace."}
              </h1>
              <p>Start the Interview Coach API, then reconnect to begin.</p>
            </div>
          ) : (
            <>
              {(Object.keys(workflows) as WorkflowKey[])
                .filter((id) => page === id || visited.has(id))
                .map((id) => (
                  <div hidden={page !== id} key={id}>
                    <Workflows
                      page={id}
                      config={config}
                      onPractice={practice}
                    />
                  </div>
                ))}
              {page === "voice" && <Voice config={config} />}
              {page === "sessions" && (
                <Sessions
                  config={config}
                  draft={draft}
                  onDraftUsed={clearDraft}
                />
              )}
              {page === "progress" && <ProgressPage onPractice={practice} />}
              {page === "history" && <History />}
            </>
          )}
          <footer className="page-footer">
            <span>INTERVIEW COACH</span>
            <p>Preparation that moves you forward.</p>
            <span>Built for your next opportunity.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
