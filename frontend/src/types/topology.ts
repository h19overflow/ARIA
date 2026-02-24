export interface TopologyEdge {
  from_node: string
  to_node: string
  branch?: string | null
}

export interface Topology {
  nodes: string[]
  edges: TopologyEdge[]
  entry_node: string
  branch_nodes: string[]
}
