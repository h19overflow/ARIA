from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # n8n
    n8n_base_url: str = "http://localhost:5678"
    n8n_api_key: str = ""

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Google / Gemini
    google_api_key: str = ""
    gemini_api_key: str = ""  # alias — same key, different env var name
    gemini_model: str = "gemini-3.1-pro-preview"
    embedding_model: str = "models/gemini-embedding-001"

    # Weights & Biases / Weave
    wandb_project: str = "ARIA"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
