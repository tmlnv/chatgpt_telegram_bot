import json

import openai
from loguru import logger

import conf as config

# setup openai
openai.api_key = config.hugging_face_as_openai_api_key
if config.openai_api_base is not None:
    openai.api_base = config.openai_api_base

OPENAI_COMPLETION_OPTIONS = {
    "temperature": 0.7,
    "max_tokens": 1000,
    "top_p": 1,
    "frequency_penalty": 0,
    "presence_penalty": 0,
    "request_timeout": 60.0,
}

with open('bot/chat_modes.json', 'r') as file:
    CHAT_MODES = json.load(file)


class ChatGPT:
    def __init__(self, model="gpt-3.5-turbo-16k"):
        self.model = model

    async def send_message_stream(
            self,
            message: str,
            dialog_messages: list[dict[str, str]] | None = None,
            chat_mode: str = "assistant"
    ):
        if dialog_messages is None:
            dialog_messages: list[str] = []

        if chat_mode not in CHAT_MODES.keys():
            raise ValueError(f"Chat mode {chat_mode} is not supported")

        n_dialog_messages_before = len(dialog_messages)
        answer = None
        while answer is None:
            try:
                messages = self._generate_prompt_messages(message, dialog_messages, chat_mode)
                logger.info(f'Prompt:\n{messages}')

                r_gen = await openai.ChatCompletion.acreate(
                    model=self.model,
                    messages=messages,
                    stream=True,
                    **OPENAI_COMPLETION_OPTIONS
                )

                answer = ""
                async for r_item in r_gen:
                    delta = r_item.choices[0].delta
                    if "content" in delta:
                        answer += delta.content
                        n_first_dialog_messages_removed = n_dialog_messages_before - len(dialog_messages)
                        yield "not_finished", answer, messages, n_first_dialog_messages_removed

                answer = self._postprocess_answer(answer)

            except openai.error.InvalidRequestError as e:  # too many tokens
                if len(dialog_messages) == 0:
                    raise e

                # forget first message in dialog_messages
                dialog_messages = dialog_messages[1:]

        logger.info(answer)

        n_first_dialog_messages_removed = n_dialog_messages_before - len(dialog_messages)

        yield 'finished', answer, messages, n_first_dialog_messages_removed

    async def send_message(
            self,
            message: str,
            dialog_messages: list[dict[str, str]] | None = None,
            chat_mode: str = "assistant"
    ):
        if dialog_messages is None:
            dialog_messages = []

        if chat_mode not in CHAT_MODES.keys():
            raise ValueError(f"Chat mode {chat_mode} is not supported")

        n_dialog_messages_before = len(dialog_messages)
        answer = None
        while answer is None:
            try:
                messages = self._generate_prompt_messages(message, dialog_messages, chat_mode)
                logger.info(f'Prompt:\n{messages}')
                r = await openai.ChatCompletion.acreate(
                    model=self.model,
                    messages=messages,
                    **OPENAI_COMPLETION_OPTIONS
                )
                answer = r.choices[0].message["content"]
                logger.info(f'ChatGPT answer:\n{answer}')

                answer = self._postprocess_answer(answer)

            except openai.error.InvalidRequestError as e:  # too many tokens
                if len(dialog_messages) == 0:
                    raise ValueError(
                        "Dialog messages is reduced to zero, but still has too many tokens to make completion"
                    ) from e

                # forget first message in dialog_messages
                dialog_messages = dialog_messages[1:]

        n_first_dialog_messages_removed = n_dialog_messages_before - len(dialog_messages)

        return answer, messages, n_first_dialog_messages_removed

    @staticmethod
    def _generate_prompt(message, dialog_messages, chat_mode):
        prompt = CHAT_MODES[chat_mode]["prompt_start"]
        prompt += "\n\n"

        # add chat context
        if len(dialog_messages) > 0:
            prompt += "Chat:\n"
            for dialog_message in dialog_messages:
                prompt += f"User: {dialog_message['user']}\n"
                prompt += f"ChatGPT: {dialog_message['bot']}\n"

        # current message
        prompt += f"User: {message}\n"
        prompt += "ChatGPT: "

        return prompt

    @staticmethod
    def _generate_prompt_messages(
            message: str,
            dialog_messages: list[dict[str, str]],
            chat_mode: str
    ) -> list[dict[str, str]]:
        prompt = CHAT_MODES[chat_mode]["prompt_start"]

        messages = [{"role": "system", "content": prompt}]
        for dialog_message in dialog_messages:
            messages.append({"role": "user", "content": dialog_message["user"]})
            messages.append({"role": "assistant", "content": dialog_message["bot"]})
        messages.append({"role": "user", "content": message})

        return messages

    @staticmethod
    def _postprocess_answer(answer: str) -> str:
        answer = answer.strip()
        return answer
