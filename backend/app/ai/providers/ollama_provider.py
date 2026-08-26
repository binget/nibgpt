import json
import urllib.request

from app.ai.providers.base import (
    AIProvider,
)

from app.core.config import (
    settings,
)


class OllamaProvider(AIProvider):
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        url = (
            f"{settings.ollama_base_url}"
            "/api/generate"
        )

        full_prompt = prompt

        if system_prompt:
            full_prompt = (
                f"{system_prompt}\n\n"
                f"User:\n{prompt}\n\n"
                f"Assistant:"
            )

        payload = {
            "model": settings.ollama_model,
            "prompt": full_prompt,
            "stream": False,

            "options": {
                "num_ctx": 2048,
                "temperature": 0.4,
                "num_predict": 2048,
            },

            "keep_alive": "30m",
        }

        request = urllib.request.Request(
            url=url,
            data=json.dumps(
                payload
            ).encode(
                "utf-8"
            ),
            headers={
                "Content-Type":
                    "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=240,
            ) as response:
                raw_response = (
                    response
                    .read()
                    .decode(
                        "utf-8"
                    )
                )

        except Exception as error:
            raise RuntimeError(
                "Unable to communicate "
                "with Ollama."
            ) from error

        try:
            result = json.loads(
                raw_response
            )

        except json.JSONDecodeError as error:
            raise RuntimeError(
                "Ollama returned an invalid "
                "JSON response."
            ) from error

        answer = (
            result.get(
                "response"
            )
            or ""
        ).strip()

        if not answer:
            raise RuntimeError(
                "Ollama returned an empty answer."
            )

        return answer

    def stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ):
        url = (
            f"{settings.ollama_base_url}"
            "/api/generate"
        )

        full_prompt = prompt

        if system_prompt:
            full_prompt = (
                f"{system_prompt}\n\n"
                f"User:\n{prompt}\n\n"
                f"Assistant:"
            )

        payload = {
            "model": settings.ollama_model,
            "prompt": full_prompt,
            "stream": True,
            
            "options": {
                "num_ctx": 2048,
                "temperature": 0.4,
                "num_predict": 2048,
            },

            "keep_alive": "30m",
        }

        request = urllib.request.Request(
            url=url,
            data=json.dumps(
                payload
            ).encode("utf-8"),
            headers={
                "Content-Type":
                    "application/json",
            },
            method="POST",
        )

        try:
            response = urllib.request.urlopen(
                request,
                timeout=180,
            )

            with response:
                for raw_line in response:
                    line = (
                        raw_line
                        .decode("utf-8")
                        .strip()
                    )

                    if not line:
                        continue

                    data = json.loads(line)

                    token = data.get(
                        "response",
                        "",
                    )

                    if token:
                        yield token

                    if data.get("done"):
                        break

        except Exception as error:
            raise RuntimeError(
                "Unable to stream response "
                "from Ollama."
            ) from error

     
