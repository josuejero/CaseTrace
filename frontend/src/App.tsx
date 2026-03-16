import { useEffect, useMemo, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";

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

type PanelId =
  | "overview"
  | "timeline"
  | "artifacts"
  | "entity-graph"
  | "search"
  | "report";

const PANEL_TABS: { id: PanelId; label: string }[] = [
  { id: "overview", label: "Case overview" },
  { id: "timeline", label: "Timeline" },
  { id: "artifacts", label: "Artifacts" },
  { id: "entity-graph", label: "Entity graph" },
  { id: "search", label: "Search" },
  { id: "report", label: "Report" },
];

type OverviewResponse = {
  case_id?: string | null;
  title?: string | null;
  subject?: string | null;
  acquisition: {
    operator?: string | null;
    acquired_at?: string | null;
    method?: string | null;
    device?: {
      logical_id?: string | null;
      platform?: string | null;
    };
  };
  parser_version?: string | null;
  file_summary: {
    file_count: number;
    total_size_bytes: number;
  };
  artifact_counts: Record<string, number>;
  top_files: { path: string; size_bytes: number; sha256?: string | null }[];
  notable_artifacts: {
    record_id: string;
    artifact_type: string;
    confidence?: number | null;
    summary?: string | null;
    raw_ref?: string | null;
    source_file?: string | null;
  }[];
  latest_report: { path?: string | null; generated_at?: string | null } | null;
};

type TimelineEvent = {
  record_id: string;
  artifact_type: string;
  event_time_start?: string | null;
  event_time_local?: string | null;
  content_preview?: string | null;
  event_type?: string | null;
  actor?: string | null;
  target?: string | null;
  source_file?: string | null;
  raw_ref?: string | null;
  deleted_flag: boolean;
  has_location: boolean;
};

type TimelineGroup = {
  period: string;
  artifact_counts: Record<string, number>;
  events: TimelineEvent[];
};

type TimelineResponse = {
  total: number;
  groups: TimelineGroup[];
};

type ArtifactRow = {
  record_id: string;
  artifact_type: string;
  event_time_start?: string | null;
  event_time_local?: string | null;
  actor?: string | null;
  counterparty?: string | null;
  confidence?: number | null;
  deleted_flag: boolean;
  raw_ref?: string | null;
  source_file?: string | null;
  event_type?: string | null;
};

type ArtifactsResponse = {
  total: number;
  rows: ArtifactRow[];
};

type EntityGraphNode = {
  node_id: string;
  label: string;
  type: string;
  metadata: Record<string, unknown>;
};

type EntityGraphEdge = {
  edge_id: string;
  source: string;
  target: string;
  type: string;
  metadata: Record<string, unknown>;
};

type EntityGraphResponse = {
  case_id?: string | null;
  generated_at?: string | null;
  nodes: EntityGraphNode[];
  edges: EntityGraphEdge[];
};

type ReportSummary = {
  generated_at: string;
  path: string;
  sha256: string;
  pdf_path?: string | null;
  validation?: {
    expected_record_count?: number;
    actual_record_count?: number;
    artifact_breakdown?: {
      artifact_type: string;
      expected: number;
      actual: number;
    }[];
    minimum_correlations?: number;
    validation_dataset?: string;
  };
};

type ReportRenderResponse = {
  status: string;
  message?: string | null;
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
  timeline_context: (
    | {
        record_id: string;
        artifact_type: string;
        event_time_start: string | null;
        event_time_local: string | null;
        content_preview: string | null;
        event_type: string | null;
      }
    | null
  )[];
};

type SearchResponse = {
  total_hits: number;
  artifact_counts: Record<string, number>;
  source_counts: Record<string, number>;
  hits: SearchHit[];
};

type TimelineFilterState = {
  types: string[];
  deletedOnly: boolean;
  locationOnly: boolean;
};

type ArtifactQuery = {
  type: string;
  showDeleted: boolean;
  showRecoveredOnly: boolean;
  sortBy: "event_time_start" | "confidence" | "record_id";
  sortDir: "asc" | "desc";
};

function useDebouncedValue(value: string, delay: number) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timeout);
  }, [value, delay]);

  return debounced;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<PanelId>("overview");
  const [overviewData, setOverviewData] = useState<OverviewResponse | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  const [timelineData, setTimelineData] = useState<TimelineResponse | null>(null);
  const [timelineLoading, setTimelineLoading] = useState(true);
  const [timelineError, setTimelineError] = useState<string | null>(null);
  const [timelineFilters, setTimelineFilters] = useState<TimelineFilterState>({
    types: [],
    deletedOnly: false,
    locationOnly: false,
  });

  const [artifactsData, setArtifactsData] = useState<ArtifactsResponse | null>(null);
  const [artifactsLoading, setArtifactsLoading] = useState(true);
  const [artifactsError, setArtifactsError] = useState<string | null>(null);
  const [artifactQuery, setArtifactQuery] = useState<ArtifactQuery>({
    type: "",
    showDeleted: false,
    showRecoveredOnly: false,
    sortBy: "event_time_start",
    sortDir: "desc",
  });

  const [graphData, setGraphData] = useState<EntityGraphResponse | null>(null);
  const [graphLoading, setGraphLoading] = useState(true);
  const [graphError, setGraphError] = useState<string | null>(null);
  const [selectedGraphNode, setSelectedGraphNode] = useState<EntityGraphNode | null>(null);

  const [reportSummary, setReportSummary] = useState<ReportSummary | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);
  const [reportStatus, setReportStatus] = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(true);

  const [focusedRecord, setFocusedRecord] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<string[]>([]);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [selectedRecord, setSelectedRecord] = useState<string | null>(null);
  const debouncedQuery = useDebouncedValue(query, 320);

  useEffect(() => {
    fetch(`${API_URL}/overview`)
      .then(handleJson)
      .then((data) => {
        setOverviewData(data);
        setOverviewError(null);
      })
      .catch((err) => setOverviewError(err.message))
      .finally(() => setOverviewLoading(false));

    fetch(`${API_URL}/reports/latest`)
      .then(handleJson)
      .then((data) => {
        setReportSummary(data);
        setReportError(null);
      })
      .catch((err) => setReportError(err.message))
      .finally(() => setReportLoading(false));
  }, []);

  useEffect(() => {
    refreshTimeline();
  }, [timelineFilters]);

  useEffect(() => {
    refreshArtifacts();
  }, [artifactQuery]);

  useEffect(() => {
    fetch(`${API_URL}/entity-graph`)
      .then(handleJson)
      .then((data) => {
        setGraphData(data);
        setGraphError(null);
      })
      .catch((err) => setGraphError(err.message))
      .finally(() => setGraphLoading(false));
  }, []);

  useEffect(() => {
    if (!focusedRecord) {
      return;
    }
    setSelectedRecord(focusedRecord);
    setActiveTab("search");
  }, [focusedRecord]);

  useEffect(() => {
    if (response && !selectedRecord) {
      setSelectedRecord(response.hits[0]?.record_id ?? null);
    }
  }, [response, selectedRecord]);

  useEffect(() => {
    const controller = new AbortController();
    setSearchLoading(true);
    setSearchError(null);
    const params = new URLSearchParams();
    if (debouncedQuery) {
      params.set("q", debouncedQuery);
    }
    filters.forEach((type) => params.append("type", type));
    params.set("limit", "40");
    params.set("offset", "0");
    fetch(`${API_URL}/search?${params.toString()}`, { signal: controller.signal })
      .then(handleJson)
      .then((data: SearchResponse) => {
        setResponse(data);
        setSelectedRecord((prev) => (data.hits.some((hit) => hit.record_id === prev) ? prev : data.hits[0]?.record_id ?? null));
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          setSearchError(err.message);
        }
      })
      .finally(() => setSearchLoading(false));
    return () => controller.abort();
  }, [debouncedQuery, filters]);

  function handleJson(response: Response) {
    if (!response.ok) {
      throw new Error(`Request failed (${response.status})`);
    }
    return response.json();
  }

  function refreshTimeline() {
    setTimelineLoading(true);
    setTimelineError(null);
    const params = new URLSearchParams();
    timelineFilters.types.forEach((type) => params.append("type", type));
    if (timelineFilters.deletedOnly) {
      params.set("deleted_only", "true");
    }
    if (timelineFilters.locationOnly) {
      params.set("location_only", "true");
    }
    params.set("limit", "80");
    params.set("offset", "0");
    fetch(`${API_URL}/timeline?${params.toString()}`)
      .then(handleJson)
      .then((data: TimelineResponse) => {
        setTimelineData(data);
        setTimelineError(null);
      })
      .catch((err) => setTimelineError(err.message))
      .finally(() => setTimelineLoading(false));
  }

  function refreshArtifacts() {
    setArtifactsLoading(true);
    setArtifactsError(null);
    const params = new URLSearchParams({
      sort_by: artifactQuery.sortBy,
      sort_dir: artifactQuery.sortDir,
      limit: "30",
      offset: "0",
    });
    if (artifactQuery.type) {
      params.set("artifact_type", artifactQuery.type);
    }
    if (artifactQuery.showDeleted) {
      params.set("show_deleted", "true");
    }
    if (artifactQuery.showRecoveredOnly) {
      params.set("show_recovered_only", "true");
    }
    fetch(`${API_URL}/artifacts?${params.toString()}`)
      .then(handleJson)
      .then((data: ArtifactsResponse) => {
        setArtifactsData(data);
        setArtifactsError(null);
      })
      .catch((err) => setArtifactsError(err.message))
      .finally(() => setArtifactsLoading(false));
  }

  function toggleTimelineFilter(type: string) {
    setTimelineFilters((prev) => ({
      ...prev,
      types: prev.types.includes(type) ? prev.types.filter((item) => item !== type) : [...prev.types, type],
    }));
  }

  function toggleFilter(type: string) {
    setFilters((prev) => (prev.includes(type) ? prev.filter((item) => item !== type) : [...prev, type]));
  }

  function handleReportRefresh() {
    setReportStatus("Regenerating report...");
    fetch(`${API_URL}/reports/render?pdf=true`, { method: "POST" })
      .then(handleJson)
      .then((data: ReportRenderResponse) => {
        setReportStatus(data.message ?? data.status);
        setReportError(null);
        return fetch(`${API_URL}/reports/latest`).then(handleJson);
      })
      .then((fresh: ReportSummary) => setReportSummary(fresh))
      .catch((err) => setReportError(err.message))
      .finally(() => setReportStatus(null));
  }

  function handleGraphNodeClick(node: EntityGraphNode) {
    setSelectedGraphNode(node);
    if (node.metadata && typeof node.metadata.record_id === "string") {
      setFocusedRecord(node.metadata.record_id);
    }
  }

  const graphPayload = useMemo(() => {
    if (!graphData) {
      return null;
    }
    return {
      nodes: graphData.nodes,
      links: graphData.edges.map((edge) => ({
        source: edge.source,
        target: edge.target,
        label: edge.type,
        metadata: edge.metadata,
      })),
    };
  }, [graphData]);

  const reportIframe = `${API_URL}/reports/latest/html`;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">CaseTrace Investigator</p>
          <h1>Phase 9: Investigator UI</h1>
        </div>
        <nav className="tab-row">
          {PANEL_TABS.map((tab) => (
            <button
              key={tab.id}
              className={`tab-button ${tab.id === activeTab ? "active" : ""}`}
              type="button"
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>
      <main className="panel-wrapper">
        {activeTab === "overview" && (
          <section className="panel overview-panel">
            {overviewLoading && <p>Loading overview…</p>}
            {overviewError && <p className="status-error">{overviewError}</p>}
            {overviewData && (
              <div className="overview-grid">
                <article className="card">
                  <h2>Case metadata</h2>
                  <p>{overviewData.title}</p>
                  <p>Subject: {overviewData.subject ?? "n/a"}</p>
                  <p>Parser: {overviewData.parser_version ?? "n/a"}</p>
                  <p>
                    {overviewData.acquisition.operator} · {overviewData.acquisition.method}
                  </p>
                </article>
                <article className="card">
                  <h2>File summary</h2>
                  <p>{overviewData.file_summary.file_count.toLocaleString()} files</p>
                  <p>{overviewData.file_summary.total_size_bytes.toLocaleString()} bytes</p>
                  {overviewData.latest_report?.generated_at && (
                    <p>Report generated at {overviewData.latest_report.generated_at}</p>
                  )}
                </article>
                <article className="card">
                  <h2>Artifact counts</h2>
                  <div className="badge-grid">
                    {Object.entries(overviewData.artifact_counts).map(([artifact, count]) => (
                      <span key={artifact} className="badge">
                        {artifact}: {count}
                      </span>
                    ))}
                  </div>
                </article>
                <article className="card">
                  <h2>Top files</h2>
                  <ul>
                    {overviewData.top_files.map((file) => (
                      <li key={file.path}>
                        <strong>{file.path}</strong>
                        <small>{file.size_bytes.toLocaleString()} bytes</small>
                      </li>
                    ))}
                  </ul>
                </article>
                <article className="card">
                  <h2>Notable recovered artifacts</h2>
                  <ul>
                    {overviewData.notable_artifacts.map((artifact) => (
                      <li key={artifact.record_id}>
                        <p>
                          <strong>{artifact.record_id}</strong> ({artifact.artifact_type})
                        </p>
                        <p>{artifact.summary ?? artifact.raw_ref ?? "No detail"}</p>
                        {artifact.database_file && <p>Database: {artifact.database_file}</p>}
                        <button type="button" onClick={() => setFocusedRecord(artifact.record_id)}>
                          View evidence
                        </button>
                      </li>
                    ))}
                  </ul>
                </article>
              </div>
            )}
          </section>
        )}

        {activeTab === "timeline" && (
          <section className="panel timeline-panel">
            <header className="panel-header">
              <div>
                <h2>Timeline</h2>
                <p>Filter events, jump to source records, and trace deleted items.</p>
              </div>
              <div className="filter-row">
                {ARTIFACT_TYPES.map((type) => (
                  <button
                    key={type}
                    type="button"
                    className={`chip ${timelineFilters.types.includes(type) ? "active" : ""}`}
                    onClick={() => toggleTimelineFilter(type)}
                  >
                    {type}
                  </button>
                ))}
                <label>
                  <input
                    type="checkbox"
                    checked={timelineFilters.deletedOnly}
                    onChange={() =>
                      setTimelineFilters((prev) => ({ ...prev, deletedOnly: !prev.deletedOnly }))
                    }
                  />
                  Show deleted
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={timelineFilters.locationOnly}
                    onChange={() =>
                      setTimelineFilters((prev) => ({ ...prev, locationOnly: !prev.locationOnly }))
                    }
                  />
                  Location-only
                </label>
                <button type="button" onClick={refreshTimeline} className="secondary">
                  Refresh
                </button>
              </div>
            </header>
            {timelineLoading && <p>Loading timeline…</p>}
            {timelineError && <p className="status-error">{timelineError}</p>}
            {timelineData && (
              <div className="timeline-groups">
                {timelineData.groups.map((group) => (
                  <article key={group.period} className="timeline-group">
                    <header>
                      <h3>{group.period}</h3>
                      <small>{group.events.length} events</small>
                    </header>
                    <div className="timeline-events">
                      {group.events.map((event) => (
                        <div key={event.record_id} className="timeline-event">
                          <div className="timeline-meta">
                            <strong>{event.event_time_local ?? event.event_time_start ?? "—"}</strong>
                            <span>{event.artifact_type}</span>
                            {event.deleted_flag && <span className="chip deleted">deleted</span>}
                          </div>
                          <p>{event.content_preview ?? event.event_type ?? "No preview"}</p>
                          <button type="button" onClick={() => setFocusedRecord(event.record_id)}>
                            Jump to source
                          </button>
                        </div>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        )}

        {activeTab === "artifacts" && (
          <section className="panel artifacts-panel">
            <header className="panel-header">
              <h2>Artifacts browser</h2>
              <div className="filter-row">
                <select
                  value={artifactQuery.type}
                  onChange={(event) => setArtifactQuery((prev) => ({ ...prev, type: event.target.value }))}
                >
                  <option value="">All types</option>
                  {ARTIFACT_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
                <label>
                  <input
                    type="checkbox"
                    checked={artifactQuery.showDeleted}
                    onChange={() =>
                      setArtifactQuery((prev) => ({ ...prev, showDeleted: !prev.showDeleted }))
                    }
                  />
                  Include deleted
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={artifactQuery.showRecoveredOnly}
                    onChange={() =>
                      setArtifactQuery((prev) => ({ ...prev, showRecoveredOnly: !prev.showRecoveredOnly }))
                    }
                  />
                  Recovered only
                </label>
                <select
                  value={artifactQuery.sortBy}
                  onChange={(event) =>
                    setArtifactQuery((prev) => ({
                      ...prev,
                      sortBy: event.target.value as ArtifactQuery["sortBy"],
                    }))
                  }
                >
                  <option value="event_time_start">Event time</option>
                  <option value="confidence">Confidence</option>
                  <option value="record_id">Record ID</option>
                </select>
                <select
                  value={artifactQuery.sortDir}
                  onChange={(event) =>
                    setArtifactQuery((prev) => ({
                      ...prev,
                      sortDir: event.target.value as ArtifactQuery["sortDir"],
                    }))
                  }
                >
                  <option value="desc">Descending</option>
                  <option value="asc">Ascending</option>
                </select>
                <button type="button" onClick={refreshArtifacts} className="secondary">
                  Refresh
                </button>
              </div>
            </header>
            {artifactsLoading && <p>Loading artifacts…</p>}
            {artifactsError && <p className="status-error">{artifactsError}</p>}
            {artifactsData && (
              <div className="artifact-table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Record</th>
                      <th>Artifact</th>
                      <th>Time</th>
                      <th>Actor</th>
                      <th>Confidence</th>
                      <th>Deleted</th>
                      <th>Source</th>
                      <th>Jump</th>
                    </tr>
                  </thead>
                  <tbody>
                    {artifactsData.rows.map((row) => (
                      <tr key={row.record_id}>
                        <td>{row.record_id}</td>
                        <td>{row.artifact_type}</td>
                        <td>{row.event_time_local ?? row.event_time_start ?? "—"}</td>
                        <td>{row.actor ?? row.target ?? "—"}</td>
                        <td>{row.confidence?.toFixed(2) ?? "—"}</td>
                        <td>{row.deleted_flag ? "yes" : "no"}</td>
                        <td>{row.source_file ?? "—"}</td>
                        <td>
                          <button type="button" onClick={() => setFocusedRecord(row.record_id)}>
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}

        {activeTab === "entity-graph" && (
          <section className="panel graph-panel">
            <header className="panel-header">
              <div>
                <h2>Entity graph</h2>
                <p>Explore the interactive relationship map with click-through evidence.</p>
              </div>
              <button type="button" className="secondary" onClick={() => setSelectedGraphNode(null)}>
                Clear selection
              </button>
            </header>
            {graphLoading && <p>Loading graph…</p>}
            {graphError && <p className="status-error">{graphError}</p>}
            {graphPayload && (
              <div className="graph-wrapper">
                <div className="graph-canvas">
                  <ForceGraph2D
                    graphData={graphPayload}
                    nodeAutoColorBy="type"
                    nodeLabel={(node: EntityGraphNode) => `${node.label} (${node.type})`}
                    linkDirectionalArrowLength={6}
                    linkDirectionalArrowRelPos={1}
                    onNodeClick={handleGraphNodeClick}
                  />
                </div>
                <aside className="graph-detail">
                  {selectedGraphNode ? (
                    <>
                      <h3>{selectedGraphNode.label}</h3>
                      <p>{selectedGraphNode.type}</p>
                      <pre>{JSON.stringify(selectedGraphNode.metadata, null, 2)}</pre>
                      <div>
                        {graphData?.edges
                          .filter(
                            (edge) => edge.source === selectedGraphNode.node_id || edge.target === selectedGraphNode.node_id
                          )
                          .map((edge) => (
                            <div key={edge.edge_id} className="edge-card">
                              <p>
                                <strong>{edge.type}</strong> · {edge.source === selectedGraphNode.node_id ? "→" : "←"} {edge.target === selectedGraphNode.node_id ? edge.source : edge.target}
                              </p>
                              {edge.metadata.record_id && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setFocusedRecord(String(edge.metadata.record_id));
                                  }}
                                >
                                  View record {edge.metadata.record_id}
                                </button>
                              )}
                            </div>
                          ))}
                      </div>
                    </>
                  ) : (
                    <p>Click a node to inspect its metadata and evidence.</p>
                  )}
                </aside>
              </div>
            )}
          </section>
        )}

        {activeTab === "search" && (
          <section className="panel search-panel">
            <header className="panel-header">
              <div>
                <h2>Search</h2>
                <p>Keyword search, source filters, and raw evidence context.</p>
              </div>
            </header>
            <div className="control-panel">
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search messages, metadata, file names…"
              />
              <div className="chip-row">
                <button type="button" className={`chip ${filters.length === 0 ? "active" : ""}`} onClick={() => setFilters([])}>
                  All {response ? `(${response.total_hits})` : ""}
                </button>
                {ARTIFACT_TYPES.map((type) => (
                  <button
                    key={type}
                    className={`chip ${filters.includes(type) ? "active" : ""}`}
                    type="button"
                    onClick={() => toggleFilter(type)}
                  >
                    {type} ({response?.artifact_counts[type] ?? 0})
                  </button>
                ))}
              </div>
            </div>
            <div className="layout">
              <div className="result-feed">
                {searchLoading && <p>Loading results…</p>}
                {searchError && <p className="status-error">{searchError}</p>}
                {!searchLoading && !searchError && response?.hits.length === 0 && <p className="empty-state">No hits.</p>}
                <div className="result-list">
                  {response?.hits.map((hit) => (
                    <article
                      key={hit.record_id}
                      className={`result-card ${selectedRecord === hit.record_id ? "selected" : ""}`}
                      onClick={() => setSelectedRecord(hit.record_id)}
                    >
                      <div className="result-meta">
                        <span className="badge">{hit.artifact_type}</span>
                        <span>{hit.event_time ?? hit.event_time_local ?? "—"}</span>
                      </div>
                      <p className="snippet" dangerouslySetInnerHTML={{ __html: hit.snippet }} />
                      <p className="result-source">
                        {hit.source_file ?? "Source unknown"} · {hit.raw_ref ?? "no raw ref"}
                      </p>
                    </article>
                  ))}
                </div>
              </div>
              {selectedRecord && (
                <aside className="detail-panel">
                  <h3>Details</h3>
                  {selectedRecord && <p>Record ID: {selectedRecord}</p>}
                  {response?.hits
                    .find((hit) => hit.record_id === selectedRecord)
                    ?.timeline_context.map((entry) => (
                      <div key={`${entry.record_id}-${entry.event_time_start}`} className="context-card">
                        <strong>{entry.event_time_start ?? entry.event_time_local ?? "—"}</strong>
                        <p>{entry.artifact_type}</p>
                        <p>{entry.content_preview}</p>
                      </div>
                    ))}
                </aside>
              )}
            </div>
          </section>
        )}

        {activeTab === "report" && (
          <section className="panel report-panel">
            <header className="panel-header">
              <div>
                <h2>Report</h2>
                <p>Executive summary, validation, and integrity in one document.</p>
              </div>
              <div className="report-actions">
                <button type="button" onClick={handleReportRefresh} disabled={!!reportStatus}>
                  Regenerate report
                </button>
                <a href={reportIframe} target="_blank" rel="noreferrer">
                  Open HTML
                </a>
                {reportSummary?.pdf_path && (
                  <a href={`${API_URL}/reports/latest/pdf`} target="_blank" rel="noreferrer">
                    Download PDF
                  </a>
                )}
              </div>
            </header>
            {reportStatus && <p>{reportStatus}</p>}
            {reportError && <p className="status-error">{reportError}</p>}
            <div className="report-cards">
              <div className="card">
                <h3>Validation</h3>
                <p>
                  Expected {reportSummary?.validation?.expected_record_count ?? "n/a"} vs actual {reportSummary?.validation?.actual_record_count ?? "n/a"}
                </p>
                <ul>
                  {(reportSummary?.validation?.artifact_breakdown ?? []).map((row) => (
                    <li key={row.artifact_type}>
                      {row.artifact_type}: {row.actual} / {row.expected}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="card">
                <h3>Integrity</h3>
                <p>Report path: {reportSummary?.path}</p>
                <p>SHA-256: {reportSummary?.sha256}</p>
                <p>Generated at: {reportSummary?.generated_at}</p>
              </div>
            </div>
            <div className="report-frame">
              <iframe title="Investigator report" src={reportIframe} />
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
