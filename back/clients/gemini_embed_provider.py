from google import genai

from core.api.embed_provider import EmbedProvider


class GeminiEmbedProvider(EmbedProvider):

    def __init__(self, api_key: str, model: str = "gemini-embedding-001") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.aio.models.embed_content(
            model=self._model,
            contents=texts,
        )
        return [e.values for e in response.embeddings]
