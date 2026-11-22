// Mirrors ALLOWED_TOOLS in backend/agents/schemas.py
export const TOOLS = [
  { id: "web_search", label: "Web Search", hint: "Search the web for information" },
  { id: "calculator", label: "Calculator", hint: "Maths and KPI calculations" },
  { id: "csv_reader", label: "File / CSV Reader", hint: "Read uploaded CSV files" },
  { id: "code", label: "Code Execution", hint: "Run Python code in a sandbox" },
] as const;

export type ToolName = (typeof TOOLS)[number]["id"];
export type PermissionMode = "auto" | "ask" | "blocked";

export const MODES: { id: PermissionMode; label: string }[] = [
  { id: "auto", label: "Auto" },
  { id: "ask", label: "Ask first" },
  { id: "blocked", label: "Blocked" },
];

// Risky tools ask for approval unless the user changes it.
export const defaultMode = (tool: ToolName): PermissionMode =>
  tool === "code" ? "ask" : "auto";

export type Agent = {
  id: number;
  name: string;
  instructions: string;
  tools: string[];
  permissions: Record<string, string>;
  schedule: string | null;
};

export type AgentInput = Omit<Agent, "id">;

export const toolLabel = (id: string) =>
  TOOLS.find((t) => t.id === id)?.label ?? id;
