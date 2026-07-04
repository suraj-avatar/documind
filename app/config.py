from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
class Settings(BaseSettings):

    GROQ_API_KEY: str

    CHROMA_PATH: str = "vectorstore"

    EMBEDDING_MODEL: str = "BAAI/bge-base-en-v1.5"

    LLM_MODEL: str = "llama-3.1-8b-instant"

    class Config:
        env_file = ".env"


settings = Settings()