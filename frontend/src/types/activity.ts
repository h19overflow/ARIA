export interface AgentActivity {
  id: string;
  type: 'tool_start' | 'tool_end';
  tool: string;
  args?: Record<string, unknown>;
  result?: string;
  timestamp: Date;
}
