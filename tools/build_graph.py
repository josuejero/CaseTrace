"""PyVis-driven graph reporter for CaseTrace Phase 5."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import networkx as nx
from pyvis.network import Network

from tools.entity_graph_builder import EntityGraphBuilder, GraphData


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Phase 5 entity graph.")
    parser.add_argument(
        "--case-dir",
        type=Path,
        default=Path("cases/CT-2026-001"),
        help="Case directory that contains case.json and parsed outputs.",
    )
    parser.add_argument(
        "--parsed-dir",
        type=Path,
        default=None,
        help="Directory containing case.db (defaults to <case-dir>/parsed).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for graph artifacts (defaults to <case-dir>/reports).",
    )
    args = parser.parse_args()

    case_dir = args.case_dir
    parsed_dir = args.parsed_dir or (case_dir / "parsed")
    db_path = parsed_dir / "case.db"
    if not db_path.exists():
        raise SystemExit(f"case.db not found at {db_path}")

    builder = EntityGraphBuilder(db_path, case_dir)
    graph_data = builder.build()

    output_dir = args.output_dir or (case_dir / "reports")
    analysis_dir = output_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    graph_json_path = analysis_dir / "graph-data.json"
    graph_json_path.write_text(
        json.dumps(graph_data.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )

    net = _render_pyvis_graph(graph_data)
    graph_html_path = output_dir / "graph.html"
    graph_html_path.parent.mkdir(parents=True, exist_ok=True)
    net.write_html(str(graph_html_path))

    detail_path = analysis_dir / "entity-detail.html"
    detail_path.write_text(_entity_detail_html(graph_data, graph_json_path.name), encoding="utf-8")

    print(f"Graph data written to {graph_json_path}")
    print(f"Interactive PyVis page written to {graph_html_path}")
    print(f"Entity detail view written to {detail_path}")


def _render_pyvis_graph(graph_data: GraphData) -> Network:
    nx_graph = nx.MultiDiGraph()
    for node in graph_data.nodes:
        nx_graph.add_node(
            node.node_id,
            label=node.label,
            title=_format_metadata(node.metadata),
            group=node.type,
        )
    for edge in graph_data.edges:
        nx_graph.add_edge(
            edge.source,
            edge.target,
            label=edge.type,
            title=_format_metadata(edge.metadata),
        )
    net = Network(width="100%", height="850px", directed=True)
    net.from_nx(nx_graph)
    return net


def _format_metadata(metadata: dict) -> str:
    if not metadata:
        return ""
    return json.dumps(metadata, indent=2, ensure_ascii=False)


def _entity_detail_html(graph_data: GraphData, data_file_name: str) -> str:
    case_id = graph_data.case_id or "unknown"
    generated_at = graph_data.generated_at or "unknown"
    template = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>CaseTrace Entity Details</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 2rem; max-width: 960px; }
    h1 { margin-bottom: 0; }
    section { margin-top: 2rem; border-top: 1px solid #ccc; padding-top: 1rem; }
    table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; }
    th, td { border: 1px solid #ddd; padding: 0.25rem 0.5rem; text-align: left; }
    th { background: #f8f8f8; }
    .status { color: #b22222; }
  </style>
</head>
<body>
  <h1>Entity details · __CASE_ID__</h1>
  <p>Each table lists edges that touch the person plus their raw evidence references.</p>
  <p>Generated <strong>__GENERATED_AT__</strong>.</p>
  <div id=\"entity-details\"></div>
  <p class=\"status\" id=\"status\"></p>
  <script>
    const dataUrl = "__DATA_FILE__";
    const entityContainer = document.getElementById("entity-details");
    const statusMessage = document.getElementById("status");

    fetch(dataUrl)
      .then((resp) => resp.ok ? resp.json() : Promise.reject(resp.statusText))
      .then(render)
      .catch((error) => {
        statusMessage.textContent = "Unable to load graph data: " + error;
      });

    function render(data) {
      const nodes = data.nodes || [];
      const edges = data.edges || [];
      const people = nodes.filter((node) => node.type === "person");
      const rows = Object.fromEntries(nodes.map((node) => [node.node_id, node]));

      if (!people.length) {
        entityContainer.textContent = "No person nodes were found in the graph.";
        return;
      }

      people.forEach((person) => {
        const personSection = document.createElement("section");
        const title = document.createElement("h2");
        title.textContent = person.label;
        personSection.appendChild(title);
        const summary = document.createElement("p");
        summary.textContent = `Node metadata: ${Object.keys(person.metadata || {}).length ? JSON.stringify(person.metadata) : "none"}`;
        personSection.appendChild(summary);

        const table = document.createElement("table");
        const head = document.createElement("thead");
        head.innerHTML = "<tr><th>Edge</th><th>Direction</th><th>Other node</th><th>Record</th><th>Raw ref</th></tr>";
        table.appendChild(head);
        const body = document.createElement("tbody");
        const related = edges.filter(
          (edge) => edge.source === person.node_id || edge.target === person.node_id
        );
        related.forEach((edge) => {
          const otherId = edge.source === person.node_id ? edge.target : edge.source;
          const direction = edge.source === person.node_id ? "→" : "←";
          const otherNode = rows[otherId];
          const row = document.createElement("tr");
          row.innerHTML = `
            <td>${edge.type}</td>
            <td>${direction}</td>
            <td>${otherNode ? otherNode.label : otherId}</td>
            <td>${edge.metadata.record_id || "–"}</td>
            <td>${edge.metadata.raw_ref || "–"}</td>
          `;
          body.appendChild(row);
        });
        table.appendChild(body);
        personSection.appendChild(table);
        entityContainer.appendChild(personSection);
      });
    }
  </script>
</body>
</html>
"""
    return (
        template
        .replace("__CASE_ID__", case_id)
        .replace("__GENERATED_AT__", generated_at)
        .replace("__DATA_FILE__", data_file_name)
    )


if __name__ == "__main__":
    main()
