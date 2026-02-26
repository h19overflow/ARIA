"""Benchmark fixtures for the Build Cycle — simple, medium, large tiers.

Each fixture has:
  name        — human label
  tier        — "simple" | "medium" | "large"
  blueprint   — dict passed as build_blueprint to the graph
  expected_trigger_type — "webhook" | "schedule" | "other"
  expected_node_count   — minimum nodes we expect in the generated workflow
"""
from __future__ import annotations

FIXTURES: list[dict] = [
    # ── Simple ──────────────────────────────────────────────────────────────────────────
    {
        "name": "Webhook Echo",
        "tier": "simple",
        "expected_trigger_type": "webhook",
        "expected_node_count": 1,
        "blueprint": {
            "intent": "When I receive a webhook POST, respond with a 200 OK acknowledgment",
            "required_nodes": ["webhook"],
            "credential_ids": {},
            "topology": {
                "nodes": ["Webhook"],
                "edges": [],
                "entry_node": "Webhook",
                "branch_nodes": [],
            },
            "user_description": "Simple webhook responder",
        },
    },
    {
        "name": "Webhook to HTTP Request",
        "tier": "simple",
        "expected_trigger_type": "webhook",
        "expected_node_count": 2,
        "blueprint": {
            "intent": "When I receive a webhook, forward the payload via HTTP POST to https://httpbin.org/post",
            "required_nodes": ["webhook", "httpRequest"],
            "credential_ids": {},
            "topology": {
                "nodes": ["Webhook", "HTTP Request"],
                "edges": [{"from_node": "Webhook", "to_node": "HTTP Request", "branch": None}],
                "entry_node": "Webhook",
                "branch_nodes": [],
            },
            "user_description": "Forward webhook to httpbin",
        },
    },
    {
        "name": "Schedule to HTTP Request",
        "tier": "simple",
        "expected_trigger_type": "schedule",
        "expected_node_count": 2,
        "blueprint": {
            "intent": "Every 15 minutes, make an HTTP GET request to https://httpbin.org/get and log the result",
            "required_nodes": ["scheduleTrigger", "httpRequest"],
            "credential_ids": {},
            "topology": {
                "nodes": ["Schedule Trigger", "HTTP Request"],
                "edges": [{"from_node": "Schedule Trigger", "to_node": "HTTP Request", "branch": None}],
                "entry_node": "Schedule Trigger",
                "branch_nodes": [],
            },
            "user_description": "Scheduled HTTP ping",
        },
    },
    # ── Medium ──────────────────────────────────────────────────────────────────────────
    {
        "name": "Webhook Set HTTP",
        "tier": "medium",
        "expected_trigger_type": "webhook",
        "expected_node_count": 3,
        "blueprint": {
            "intent": "When I receive a webhook, extract the 'name' field, transform it to uppercase using a Set node, then POST the result to https://httpbin.org/post",
            "required_nodes": ["webhook", "set", "httpRequest"],
            "credential_ids": {},
            "topology": {
                "nodes": ["Webhook", "Set", "HTTP Request"],
                "edges": [
                    {"from_node": "Webhook", "to_node": "Set", "branch": None},
                    {"from_node": "Set", "to_node": "HTTP Request", "branch": None},
                ],
                "entry_node": "Webhook",
                "branch_nodes": [],
            },
            "user_description": "Webhook with field transform",
        },
    },
    {
        "name": "Webhook IF two branches",
        "tier": "medium",
        "expected_trigger_type": "webhook",
        "expected_node_count": 4,
        "blueprint": {
            "intent": "When I receive a webhook with a 'status' field: if status equals 'ok' POST to https://httpbin.org/post with approved=true, otherwise POST with approved=false",
            "required_nodes": ["webhook", "if", "httpRequest"],
            "credential_ids": {},
            "topology": {
                "nodes": ["Webhook", "IF", "HTTP Request (approved)", "HTTP Request (rejected)"],
                "edges": [
                    {"from_node": "Webhook", "to_node": "IF", "branch": None},
                    {"from_node": "IF", "to_node": "HTTP Request (approved)", "branch": "true"},
                    {"from_node": "IF", "to_node": "HTTP Request (rejected)", "branch": "false"},
                ],
                "entry_node": "Webhook",
                "branch_nodes": ["IF"],
            },
            "user_description": "Conditional routing on webhook field",
        },
    },
    {
        "name": "Schedule HTTP Set HTTP",
        "tier": "medium",
        "expected_trigger_type": "schedule",
        "expected_node_count": 4,
        "blueprint": {
            "intent": "Every hour, fetch data from https://httpbin.org/get, extract the 'url' field using a Set node, then POST it to https://httpbin.org/post",
            "required_nodes": ["scheduleTrigger", "httpRequest", "set"],
            "credential_ids": {},
            "topology": {
                "nodes": ["Schedule Trigger", "HTTP Request (fetch)", "Set", "HTTP Request (post)"],
                "edges": [
                    {"from_node": "Schedule Trigger", "to_node": "HTTP Request (fetch)", "branch": None},
                    {"from_node": "HTTP Request (fetch)", "to_node": "Set", "branch": None},
                    {"from_node": "Set", "to_node": "HTTP Request (post)", "branch": None},
                ],
                "entry_node": "Schedule Trigger",
                "branch_nodes": [],
            },
            "user_description": "Scheduled fetch-transform-post pipeline",
        },
    },
    # ── Large ───────────────────────────────────────────────────────────────────────────
    {
        "name": "Webhook Set IF HTTP Merge",
        "tier": "large",
        "expected_trigger_type": "webhook",
        "expected_node_count": 6,
        "blueprint": {
            "intent": "When I receive a webhook with 'amount' field: extract and set it, check if amount > 100, if yes POST to https://httpbin.org/post with tier=premium, if no POST with tier=standard, then merge both branches and POST a summary to https://httpbin.org/post",
            "required_nodes": ["webhook", "set", "if", "httpRequest", "merge"],
            "credential_ids": {},
            "topology": {
                "nodes": ["Webhook", "Set", "IF", "HTTP Request (premium)", "HTTP Request (standard)", "Merge"],
                "edges": [
                    {"from_node": "Webhook", "to_node": "Set", "branch": None},
                    {"from_node": "Set", "to_node": "IF", "branch": None},
                    {"from_node": "IF", "to_node": "HTTP Request (premium)", "branch": "true"},
                    {"from_node": "IF", "to_node": "HTTP Request (standard)", "branch": "false"},
                    {"from_node": "HTTP Request (premium)", "to_node": "Merge", "branch": None},
                    {"from_node": "HTTP Request (standard)", "to_node": "Merge", "branch": None},
                ],
                "entry_node": "Webhook",
                "branch_nodes": ["IF"],
            },
            "user_description": "Branch-and-merge with conditional tiering",
        },
    },
    {
        "name": "Schedule three HTTP Set IF HTTP",
        "tier": "large",
        "expected_trigger_type": "schedule",
        "expected_node_count": 7,
        "blueprint": {
            "intent": "Every 30 minutes: fetch from https://httpbin.org/get, fetch from https://httpbin.org/uuid, fetch from https://httpbin.org/ip, combine the results with a Set node, if the ip field is not empty POST all data to https://httpbin.org/post, otherwise log a skip message to https://httpbin.org/post",
            "required_nodes": ["scheduleTrigger", "httpRequest", "set", "if"],
            "credential_ids": {},
            "topology": {
                "nodes": ["Schedule Trigger", "HTTP Request (get)", "HTTP Request (uuid)", "HTTP Request (ip)", "Set", "IF", "HTTP Request (post)"],
                "edges": [
                    {"from_node": "Schedule Trigger", "to_node": "HTTP Request (get)", "branch": None},
                    {"from_node": "HTTP Request (get)", "to_node": "HTTP Request (uuid)", "branch": None},
                    {"from_node": "HTTP Request (uuid)", "to_node": "HTTP Request (ip)", "branch": None},
                    {"from_node": "HTTP Request (ip)", "to_node": "Set", "branch": None},
                    {"from_node": "Set", "to_node": "IF", "branch": None},
                    {"from_node": "IF", "to_node": "HTTP Request (post)", "branch": "true"},
                ],
                "entry_node": "Schedule Trigger",
                "branch_nodes": ["IF"],
            },
            "user_description": "Multi-fetch aggregation with conditional post",
        },
    },
    {
        "name": "Webhook Set HTTP IF Set HTTP Merge HTTP",
        "tier": "large",
        "expected_trigger_type": "webhook",
        "expected_node_count": 9,
        "blueprint": {
            "intent": "When I receive a webhook with a 'query' field: extract the query with Set, fetch https://httpbin.org/get?q={{query}}, check if the response status is 200, if yes transform the result with another Set and POST to https://httpbin.org/post with success=true, if no POST directly with success=false, merge both paths, then POST a final audit record to https://httpbin.org/post",
            "required_nodes": ["webhook", "set", "httpRequest", "if", "merge"],
            "credential_ids": {},
            "topology": {
                "nodes": ["Webhook", "Set (extract)", "HTTP Request (fetch)", "IF", "Set (transform)", "HTTP Request (success)", "HTTP Request (fail)", "Merge", "HTTP Request (audit)"],
                "edges": [
                    {"from_node": "Webhook", "to_node": "Set (extract)", "branch": None},
                    {"from_node": "Set (extract)", "to_node": "HTTP Request (fetch)", "branch": None},
                    {"from_node": "HTTP Request (fetch)", "to_node": "IF", "branch": None},
                    {"from_node": "IF", "to_node": "Set (transform)", "branch": "true"},
                    {"from_node": "IF", "to_node": "HTTP Request (fail)", "branch": "false"},
                    {"from_node": "Set (transform)", "to_node": "HTTP Request (success)", "branch": None},
                    {"from_node": "HTTP Request (success)", "to_node": "Merge", "branch": None},
                    {"from_node": "HTTP Request (fail)", "to_node": "Merge", "branch": None},
                    {"from_node": "Merge", "to_node": "HTTP Request (audit)", "branch": None},
                ],
                "entry_node": "Webhook",
                "branch_nodes": ["IF"],
            },
            "user_description": "Full pipeline: extract → fetch → branch → merge → audit",
        },
    },
]
