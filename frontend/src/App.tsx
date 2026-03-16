import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const ARTIFACT_TYPES = [
  "message",
  "call",
  "browser_visit",
  "location_point",
  "photo",
  "app_event",
  "recovered_record",
  "evidence_file",
];

const typeLabels: Record<string, string> = {
  message: "Messages",
  call: "Calls",
  browser_visit: "Browser",
  location_point: "Locations",
  photo: "Photos",
  app_event: "App events",
  recovered_record: "Recovered",
  evidence_file: "Files",
};

type TimelineEntry = {
  record_id: string;
  artifact_type: string;
  event_time_start: string | null;
  event_time_local: string | null;
  content_preview: string | null;
  event_type: string | null;
};

type SearchHit = {
  record_id: string;
  artifact_type: string;
  snippet: string;
  event_time: string | null;
  event_time_local: string | null;
  raw_ref: string | null;
  actor: string | null;
  counterparty: string | null;
  source_file: string | null;
  url: string | null;
  title: string | null;
  metadata_text: string | null;
  timeline_context: TimelineEntry[];
};

type SearchResponse = {
  total_hits: number;
  artifact_counts: Record<string, number>;
  hits: SearchHit[];
};

type FileSummary = {
  file_count: number;
  total_size_bytes: number;
};

type IntegrityManifest = {
  case_id: string;
  algorithm: string;
  generated_at: string;
  acquisition: {
    acquired_at: string;
    operator: string;
    script_version: string;
    device: {
      logical_id: string;
      adb_serial: string;
      platform: string;
    };
    method: string;
  };
  app: {
    package: string;
    label: string;
    version: string;
  };
  environment: {
    git_commit: string;
    container_image_digest: string | null;
  };
  parser_version: string;
  report?: {
    generated_at: string;
    path: string;
    sha256: string | null;
  };
  files: {
    path: string;
    sha256: string;
    size_bytes: number;
  }[];
};

type ProcessingLogStep = {
  stage: "acquisition" | "analysis" | "report_export";
  timestamp: string;
  description: string;
  actor: string | null;
  details: Record<string, unknown> | null;
};

type ProcessingLog = {
  case_id: string;
  generated_at: string;
  steps: ProcessingLogStep[];
};

type IntegrityResponse = {
  manifest: IntegrityManifest;
  processing_log: ProcessingLog;
  file_summary: FileSummary;
};

function useDebouncedValue(value: string, delay: number) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timeout);
  }, [value, delay]);

  return debounced;
}

function buildQuery(filters: string[], search: string) {
  const params = new URLSearchParams();
  if (search) {
    params.set("q", search);
  }
  filters.forEach((type) => params.append("type", type));
  params.set("limit", "40");
  params.set("offset", "0");
  return params.toString();
}

function formatBytes(bytes: number) {
  return `${bytes.toLocaleString()} bytes`;
}

function formatDetailValue(value: unknown) {
  if (value === null || value === undefined) {
    return "n/a";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

export default function App() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<string[]>([]);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [selectedRecord, setSelectedRecord] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [integrityData, setIntegrityData] = useState<IntegrityResponse | null>(null);
  const [integrityError, setIntegrityError] = useState<string | null>(null);
  const [integrityLoading, setIntegrityLoading] = useState(false);
  const debouncedQuery = useDebouncedValue(query, 320);

  useEffect(() => {
    const controller = new AbortController();
    const params = buildQuery(filters, debouncedQuery);
    setIsLoading(true);
    setError(null);
    fetch(`${API_URL}/search?${params}`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Search failed (${res.status})`);
        }
        return res.json();
      })
      .then((data: SearchResponse) => {
        setResponse(data);
        setSelectedRecord((prev) => (data.hits.some((hit) => hit.record_id === prev) ? prev : data.hits[0]?.record_id ?? null));
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          setError(err.message);
        }
      })
      .finally(() => setIsLoading(false));
    return () => controller.abort();
  }, [debouncedQuery, filters]);

  useEffect(() => {
    if (response && !selectedRecord) {
      setSelectedRecord(response.hits[0]?.record_id ?? null);
    }
  }, [response, selectedRecord]);

  useEffect(() => {
    const controller = new AbortController();
    setIntegrityLoading(true);
    setIntegrityError(null);
    fetch(`${API_URL}/integrity`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Integrity data failed (${res.status})`);
        }
        return res.json();
      })
      .then((data: IntegrityResponse) => {
        setIntegrityData(data);
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          setIntegrityError(err.message);
        }
      })
      .finally(() => setIntegrityLoading(false));
    return () => controller.abort();
  }, []);

  const hits = response?.hits ?? [];
  const selectedHit = hits.find((hit) => hit.record_id === selectedRecord) ?? hits[0] ?? null;
  const manifest = integrityData?.manifest ?? null;
  const processingLog = integrityData?.processing_log ?? null;

  const toggleFilter = (artifactType: string) => {
    setFilters((prev) =>
      prev.includes(artifactType) ? prev.filter((type) => type !== artifactType) : [...prev, artifactType]
    );
  };

  const clearFilters = () => {
    setFilters([]);
  };

  return (
    <div className="app-shell">
      <header>
        <h1>CaseTrace Search</h1>
        <p>Query messages, browser history, events, and files with fast keyword ranking.</p>
      </header>
      <section className="panel control-panel">
        <label htmlFor="global-search" className="sr-only">
          Global search term
        </label>
        <input
          id="global-search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search messages, urls, file names, notes..."
        />
        <div className="chip-row">
          <button type="button" className={`chip ${filters.length === 0 ? "active" : ""}`} onClick={clearFilters}>
            All {response ? `(${response.total_hits})` : ""}
          </button>
          {ARTIFACT_TYPES.map((type) => (
            <button
              key={type}
              type="button"
              className={`chip ${filters.includes(type) ? "active" : ""}`}
              onClick={() => toggleFilter(type)}
            >
              {typeLabels[type] ?? type} ({response?.artifact_counts[type] ?? 0})
            </button>
          ))}
        </div>
        <div className="status-row">
          {isLoading && <span>Loading search results...</span>}
          {error && <span className="status-error">{error}</span>}
          {!isLoading && !error && response && <span>{response.total_hits} hits</span>}
        </div>
      </section>
      <section className="panel integrity-panel">
        <h2>Integrity Panel</h2>
        {integrityLoading && <p>Loading integrity metadata...</p>}
        {integrityError && <p className="status-error">{integrityError}</p>}
        {!integrityLoading && !integrityError && !integrityData && (
          <p>Integrity metadata is unavailable.</p>
        )}
        {integrityData && manifest && processingLog && (
          <>
            <div className="integrity-grid">
              <div className="integrity-row">
                <strong>Operator</strong>
                <span>{manifest.acquisition.operator}</span>
              </div>
              <div className="integrity-row">
                <strong>Device</strong>
                <span>
                  {manifest.acquisition.device.logical_id} • {manifest.acquisition.device.platform}
                </span>
              </div>
              <div className="integrity-row">
                <strong>Acquired</strong>
                <span>
                  {manifest.acquisition.acquired_at}
                  <br />
                  {manifest.acquisition.method}
                </span>
              </div>
              <div className="integrity-row">
                <strong>App</strong>
                <span>
                  {manifest.app.label} ({manifest.app.package}) v{manifest.app.version}
                </span>
              </div>
              <div className="integrity-row">
                <strong>Parser</strong>
                <span>{manifest.parser_version}</span>
              </div>
              <div className="integrity-row">
                <strong>Manifest</strong>
                <span>{manifest.generated_at}</span>
              </div>
              <div className="integrity-row">
                <strong>Report</strong>
                <span>{manifest.report?.path ?? "—"}</span>
              </div>
              <div className="integrity-row">
                <strong>Report SHA</strong>
                <span>{manifest.report?.sha256 ?? "pending"}</span>
              </div>
              <div className="integrity-row">
                <strong>Commit</strong>
                <span className="monospace">{manifest.environment.git_commit}</span>
              </div>
              <div className="integrity-row">
                <strong>Container</strong>
                <span>{manifest.environment.container_image_digest ?? "n/a"}</span>
              </div>
              <div className="integrity-row">
                <strong>Files</strong>
                <span>
                  {integrityData.file_summary.file_count} files •{" "}
                  {formatBytes(integrityData.file_summary.total_size_bytes)}
                </span>
              </div>
            </div>
            <div className="processing-log">
              <div className="processing-log-header">
                <h3>Processing log</h3>
                <span>{processingLog.generated_at}</span>
              </div>
              <div className="processing-log-steps">
                {processingLog.steps.map((step) => (
                  <article
                    key={`${step.stage}-${step.timestamp}`}
                    className="processing-log-step"
                  >
                    <div className="processing-log-heading">
                      <span className={`stage-badge stage-${step.stage}`}>{step.stage}</span>
                      <span className="timestamp">{step.timestamp}</span>
                    </div>
                    <p className="description">{step.description}</p>
                    {step.actor && <p className="actor">Actor: {step.actor}</p>}
                    {step.details && (
                      <ul className="detail-list">
                        {Object.entries(step.details).map(([detailKey, detailValue]) => (
                          <li key={detailKey}>
                            <strong>{detailKey}</strong>
                            <span>{formatDetailValue(detailValue)}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </article>
                ))}
              </div>
            </div>
          </>
        )}
      </section>
      <section className="panel layout">
        <div className="result-feed">
          {hits.length === 0 && !isLoading ? (
            <p className="empty-state">
              Enter a search term or click a filter to explore artifacts.
            </p>
          ) : (
            <div className="result-list">
              {hits.map((hit) => (
                <article
                  key={hit.record_id}
                  className={`result-card ${selectedHit?.record_id === hit.record_id ? "selected" : ""}`}
                  onClick={() => setSelectedRecord(hit.record_id)}
                >
                  <div className="result-meta">
                    <span className="badge">{hit.artifact_type}</span>
                    <span>{hit.event_time ?? hit.event_time_local ?? "—"}</span>
                  </div>
                  <p className="snippet" dangerouslySetInnerHTML={{ __html: hit.snippet }} />
                  <p className="result-source">
                    {hit.source_file ?? "Source unknown"} • {hit.raw_ref ?? "no raw ref"}
                  </p>
                  <div className="result-foot">
                    <span>{hit.actor ?? hit.counterparty ?? "Unnamed"}</span>
                    {hit.url && (
                      <a href={hit.url} target="_blank" rel="noreferrer">
                        {hit.url}
                      </a>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
        {selectedHit && (
          <aside className="detail-panel">
            <h2>Details</h2>
            <p>
              <strong>Record:</strong> {selectedHit.record_id}
            </p>
            <p>
              <strong>Source:</strong> {selectedHit.source_file ?? "n/a"}
            </p>
            <p>
              <strong>Raw ref:</strong> {selectedHit.raw_ref ?? "n/a"}
            </p>
            <div className="context-block">
              <h3>Timeline context</h3>
              {selectedHit.timeline_context.length === 0 ? (
                <p className="empty-state">No timeline events were mapped to this artifact.</p>
              ) : (
                <ul>
                  {selectedHit.timeline_context.map((entry) => (
                    <li key={`${entry.record_id}-${entry.event_time_start}`}>
                      <strong>{entry.event_time_start ?? entry.event_time_local ?? ""}</strong>
                      <span>{entry.artifact_type}</span>
                      <p>{entry.content_preview}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </aside>
        )}
      </section>
    </div>
  );
}
