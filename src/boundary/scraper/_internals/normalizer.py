"""
Normalise raw scraped data into a uniform N8nDocument shape
ready for embedding and storage in ChromaDB.
"""

import json
from dataclasses import dataclass, field


@dataclass
class N8nDocument:
    id: str
    name: str
    doc_type: str          # "node" | "workflow_template"
    description: str
    text: str              # the string that gets embedded
    metadata: dict = field(default_factory=dict)


def normalize_node(raw: dict) -> N8nDocument:
    """
    Normalise a scraped node page dict into an N8nDocument.
    Expected raw keys: name, node_type, description, operations, parameters, type_version, url
    """
    name = raw.get("name", "").rstrip("#").strip()
    description = raw.get("description", "")
    operations = raw.get("operations", [])
    parameters = raw.get("parameters", [])
    ops_text = ", ".join(operations) if operations else ""
    params_text = "\n".join(f"- {p}" for p in parameters) if parameters else ""
    node_type = raw.get("node_type", "")

    text = _build_node_text(name, node_type, description, ops_text, params_text)

    return N8nDocument(
        id=f"node::{raw.get('node_type', name).lower().replace(' ', '_')}",
        name=name,
        doc_type="node",
        description=description,
        text=text,
        metadata={
            "node_type": raw.get("node_type", ""),
            "type_version": str(raw.get("type_version", "1")),
            "url": raw.get("url", ""),
            "operations": ops_text,
            "parameters_count": str(len(parameters)),
        },
    )


def _build_node_text(
    name: str, node_type: str, description: str,
    ops_text: str, params_text: str,
) -> str:
    """Build the embedded text for a node document."""
    text = f"Node: {name} (type: {node_type}). {description}"
    if ops_text:
        text += f"\n\nOperations: {ops_text}."
    if params_text:
        text += f"\n\nNode parameters:\n{params_text}"
    else:
        text += "\n\nNode parameters: See node documentation for required parameters."
    return text


def normalize_workflow_template(raw: dict) -> N8nDocument:
    """
    Normalise a scraped workflow template into an N8nDocument.
    Expected raw keys: id, name, description, nodes_used, url, nodes, connections
    """
    name = raw.get("name", "")
    description = raw.get("description", "")
    nodes_used = raw.get("nodes_used", [])
    nodes_text = ", ".join(nodes_used) if nodes_used else ""

    # Construct the JSON structure for the workflow nodes and connections
    workflow_json = {
        "nodes": raw.get("nodes", []),
        "connections": raw.get("connections", {}),
    }
    workflow_json_str = json.dumps(workflow_json, indent=2)

    text = f"Workflow template: {name}. {description}"
    if nodes_text:
        text += f" Uses nodes: {nodes_text}."
    text += f"\n\nWorkflow JSON:\n```json\n{workflow_json_str}\n```"

    return N8nDocument(
        id=f"template::{raw.get('id', name.lower().replace(' ', '_'))}",
        name=name,
        doc_type="workflow_template",
        description=description,
        text=text,
        metadata={
            "template_id": str(raw.get("id", "")),
            "url": raw.get("url", ""),
            "nodes_used": nodes_text,
        },
    )
