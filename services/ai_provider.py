import json
from abc import ABC, abstractmethod
from urllib import request
from urllib.error import URLError


class AIProvider(ABC):
    @abstractmethod
    def generate_json(
        self,
        system_prompt,
        user_prompt,
        response_schema=None,
    ):
        """
        Send prompts to an AI model and return
        the model response as a Python dictionary.
        """
        raise NotImplementedError


class OllamaProvider(AIProvider):
    def __init__(
        self,
        model="qwen3:14b",
        base_url="http://localhost:11434",
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def generate_json(
        self,
        system_prompt,
        user_prompt,
        response_schema=None,
    ):
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0,
            },
        }

        if response_schema:
            payload["format"] = response_schema
        else:
            payload["format"] = "json"

        body = json.dumps(
            payload
        ).encode("utf-8")

        http_request = request.Request(
            f"{self.base_url}/api/generate",
            data=body,
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(
                http_request,
                timeout=180,
            ) as response:
                response_body = (
                    response.read().decode(
                        "utf-8"
                    )
                )

        except URLError as error:
            raise RuntimeError(
                "Could not connect to the local "
                "Ollama service."
            ) from error

        outer_response = json.loads(
            response_body
        )

        model_response = (
            outer_response.get(
                "response",
                "",
            ).strip()
        )

        if not model_response:
            raise ValueError(
                "Ollama returned an empty response."
            )

        try:
            return json.loads(
                model_response
            )

        except json.JSONDecodeError as error:
            raise ValueError(
                "Ollama did not return valid JSON."
            ) from error