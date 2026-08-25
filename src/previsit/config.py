from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central env-backed config. Swapping infra (e.g. Gemini -> Azure OpenAI)
    is a matter of changing values here, never the code that calls them."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # SQL Server
    mssql_host: str = "localhost"
    mssql_port: int = 1433
    mssql_database: str = "previsit"
    mssql_sa_password: str = ""
    mssql_driver: str = "ODBC Driver 18 for SQL Server"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_http_port: int = 6333
    qdrant_grpc_port: int = 6334
    qdrant_collection: str = "note_chunks"

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"

    # LLM provider
    llm_provider: str = "gemini"
    llm_model: str = "gemini-3.6-flash"
    gemini_api_key: str = ""
    groq_api_key: str = ""
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = ""

    # MLflow
    mlflow_tracking_uri: str = "sqlite:///mlruns.db"

    # Synthea
    synthea_population: int = 1000
    synthea_state: str = "Arizona"
    synthea_output_dir: str = "./data/synthea_output"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @property
    def mssql_connection_string(self) -> str:
        driver = self.mssql_driver.replace(" ", "+")
        return (
            f"mssql+pyodbc://sa:{self.mssql_sa_password}"
            f"@{self.mssql_host}:{self.mssql_port}/{self.mssql_database}"
            f"?driver={driver}&TrustServerCertificate=yes"
        )


settings = Settings()
