import asyncio

import replicate
from loguru import logger

import config


class KandinskyReplicate:

    def __init__(self):
        self.client = replicate.Client(api_token=config.replicate_api_token)

    def _get_replicate_response(self, prompt: str):
        logger.info("Generating image")
        replicate_generated_img = self.client.run(
            "ai-forever/kandinsky-2.2:ea1addaab376f4dc227f5368bbd8eff901820fd1cc14ed8cad63b29249e9d463",
            input={"prompt": f"{prompt}"}
        )
        logger.info(f"Image generated\n{replicate_generated_img[0]}")
        return replicate_generated_img[0]

    async def generate_image(self, prompt: str) -> str:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._get_replicate_response, prompt)
        return result
