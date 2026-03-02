"""Benchmark scenario definitions for build cycle stress testing.

Each scenario is an ARIAState-compatible dict with topology and expected metadata.
Imported by build_cycle_scenarios.py for the public BENCHMARK_SCENARIOS list.
"""
from __future__ import annotations

SCENARIO_1_MULTI_BRANCH = {
    "name": "Multi-Branch Conditional (If node with 2 credential types)",
    "blueprint": {
        "intent": (
            "When I receive a webhook, check if the payload has priority=high. "
            "If yes, summarize the data with a Code node and post to Slack. "
            "If no, send an archive notification email via Gmail."
        ),
        "required_nodes": ["webhook", "if", "code", "slack", "gmail"],
        "credential_ids": {},
        "topology": {
            "nodes": ["Webhook", "If", "Code", "Slack", "Gmail"],
            "edges": [
                {"from_node": "Webhook", "to_node": "If", "branch": None},
                {"from_node": "If", "to_node": "Code", "branch": "true"},
                {"from_node": "Code", "to_node": "Slack", "branch": None},
                {"from_node": "If", "to_node": "Gmail", "branch": "false"},
            ],
            "entry_node": "Webhook",
            "branch_nodes": ["If"],
        },
        "user_description": (
            "Route high-priority webhook payloads to Slack after summarizing, "
            "and low-priority ones to Gmail as archive notifications."
        ),
    },
    "expected": {
        "node_count": 5,
        "edge_count": 4,
        "credential_types": ["slackOAuth2Api", "gmailOAuth2Api"],
        "complexity_justification": (
            "Stress-tests If-node branching with true/false edge routing, "
            "dual credential types, and a Code node in the true branch for "
            "data transformation before the Slack destination."
        ),
    },
}


SCENARIO_2_TRANSFORM_CHAIN = {
    "name": "Data Transformation Pipeline (5-node chained transforms)",
    "blueprint": {
        "intent": (
            "Every hour, fetch JSON data from an external API via HTTP Request, "
            "extract the key fields using a Code node, format the extracted data "
            "as an HTML summary with a second Code node, and send the result "
            "to a Telegram chat."
        ),
        "required_nodes": ["schedule", "httpRequest", "code", "code", "telegram"],
        "credential_ids": {},
        "topology": {
            "nodes": [
                "Schedule",
                "HTTP Request",
                "Extract Fields",
                "Format HTML",
                "Telegram",
            ],
            "edges": [
                {"from_node": "Schedule", "to_node": "HTTP Request", "branch": None},
                {"from_node": "HTTP Request", "to_node": "Extract Fields", "branch": None},
                {"from_node": "Extract Fields", "to_node": "Format HTML", "branch": None},
                {"from_node": "Format HTML", "to_node": "Telegram", "branch": None},
            ],
            "entry_node": "Schedule",
            "branch_nodes": [],
        },
        "user_description": (
            "Hourly scheduled pipeline: fetch API data, extract fields, "
            "format as HTML, send to Telegram. Tests long linear chains "
            "with multiple Code nodes and a non-webhook trigger."
        ),
    },
    "expected": {
        "node_count": 5,
        "edge_count": 4,
        "credential_types": ["telegramApi"],
        "complexity_justification": (
            "Stress-tests long linear chain (5 nodes, 4 edges), multiple "
            "Code nodes with distinct JS logic, Schedule trigger instead of "
            "Webhook (different trigger_type handling), and chained data "
            "transformations where each node depends on the previous output."
        ),
    },
}


SCENARIO_3_FAN_OUT_SWITCH = {
    "name": "Fan-Out Switch (3-way routing, multi-credential)",
    "blueprint": {
        "intent": (
            "When I receive a webhook, read the 'category' field from the payload. "
            "If category is 'bug', make an HTTP POST to the Linear API to create an issue. "
            "If category is 'question', send a message to a Slack channel. "
            "For everything else, send a notification email via Gmail."
        ),
        "required_nodes": ["webhook", "switch", "httpRequest", "slack", "gmail"],
        "credential_ids": {},
        "topology": {
            "nodes": [
                "Webhook",
                "Switch",
                "HTTP Request",
                "Slack",
                "Gmail",
            ],
            "edges": [
                {"from_node": "Webhook", "to_node": "Switch", "branch": None},
                {"from_node": "Switch", "to_node": "HTTP Request", "branch": "0"},
                {"from_node": "Switch", "to_node": "Slack", "branch": "1"},
                {"from_node": "Switch", "to_node": "Gmail", "branch": "2"},
            ],
            "entry_node": "Webhook",
            "branch_nodes": ["Switch"],
        },
        "user_description": (
            "3-way content router: bugs to Linear (HTTP), questions to Slack, "
            "everything else to Gmail. Tests Switch node fan-out with "
            "multiple credential types and no merge/convergence."
        ),
    },
    "expected": {
        "node_count": 5,
        "edge_count": 4,
        "credential_types": ["slackOAuth2Api", "gmailOAuth2Api"],
        "complexity_justification": (
            "Stress-tests Switch node with 3 output branches (indices 0/1/2), "
            "fan-out topology with no merge node, multi-credential destinations "
            "(Slack + Gmail), and an HTTP Request node for external API calls "
            "without credentials (Linear API key in parameters)."
        ),
    },
}
