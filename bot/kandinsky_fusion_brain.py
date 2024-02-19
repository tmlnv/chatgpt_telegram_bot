import aiohttp
import json
import asyncio
import base64
from io import BytesIO

from PIL import Image
from loguru import logger

import conf as config


class FusionBrainAPI:
    def __init__(self, base_url='https://api.fusionbrain.ai/web/api/v1/text2image'):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {config.fusion_brain_auth_token}"}

    async def generate_image(self, query: str) -> str | None:
        run_url = f'{self.base_url}/run?model_id=1'
        payload = {
            "type": "GENERATE",
            "style": "DEFAULT",
            "width": 1024,
            "height": 1024,
            "generateParams": {"query": query}
        }
        data = aiohttp.FormData()
        data.add_field('params', json.dumps(payload), filename='blob', content_type='application/json')

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.post(run_url, data=data) as response:
                if response.status == 201:
                    resp = await response.json()
                    uuid = resp.get('uuid')
                    logger.info(f"Image generation started. UUID: {uuid}")
                    return uuid
                else:
                    resp = await response.text()
                    logger.error(f"Image generation failed. Response: {resp}")
                    return None

    async def get_image(self, uuid: str) -> str | None:
        status_url = f'{self.base_url}/status/{uuid}'
        async with aiohttp.ClientSession(headers=self.headers) as session:
            while True:
                async with session.get(status_url) as response:
                    if response.status == 200:
                        resp = await response.json()
                        if resp.get('status') == 'DONE':
                            logger.success("Image successfully generated")
                            image_data = resp.get('images')[0] if resp.get('images') else None
                            return image_data
                        elif resp.get('status') == 'INITIAL' or resp.get('status') == 'IN_PROGRESS':
                            logger.info("Image is still being generated, waiting and trying again...")
                            await asyncio.sleep(5)
                            continue
                        else:
                            logger.error("An error occurred during image generation.")
                            return None
                    else:
                        resp = await response.text()
                        logger.error(f"Failed to get image status. Response: {resp}")
                        return None

    @staticmethod
    async def get_image_bytes(image: str) -> BytesIO:
        logger.info("Decoding image from base64")
        img_data = base64.b64decode(image)
        logger.info("Encoding image into BytesIO")
        img_bytes = BytesIO(img_data)
        logger.info(type(img_bytes))
        return img_bytes

    @staticmethod
    def save_image(base64_image, filename):
        # Decode the base64 image
        img_data = base64.b64decode(base64_image)

        # Make a byte stream from the decoded image
        img_bytes = BytesIO(img_data)

        # Open this byte stream as an image with PIL
        img = Image.open(img_bytes)

        # Save this image to a file
        img.save(filename)
        print(f"Image saved as {filename}")
