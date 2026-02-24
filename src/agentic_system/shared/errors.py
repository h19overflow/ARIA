"""Domain errors for the agentic system."""


class AgentError(Exception):
    """Base error for all agentic system failures."""
    def __init__(self, message: str, *, agent: str, context: dict | None = None) -> None:
        self.agent = agent
        self.context = context or {}
        super().__init__(f"[{agent}] {message}")


class ExtractionError(AgentError):
    """Orchestrator failed to map ConversationNotes to valid n8n nodes."""
    pass


class CredentialError(AgentError):
    """Missing or invalid credential."""
    pass


class DeployError(AgentError):
    """n8n workflow deployment failed."""
    pass


class ExecutionError(AgentError):
    """n8n workflow execution failed after retries."""
    pass


class FixExhaustedError(AgentError):
    """Fix agent exceeded max retry attempts."""
    def __init__(self, message: str, *, agent: str, attempts: int, context: dict | None = None) -> None:
        self.attempts = attempts
        super().__init__(message, agent=agent, context=context)


class ClassificationError(AgentError):
    """Error classifier could not determine error type."""
    pass
