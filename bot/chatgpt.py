import json

import loguru
from revChatGPT.V1 import Chatbot

import config

with open('bot/chat_modes.json', 'r') as file:
    CHAT_MODES = json.load(file)


class ChatGPT:
    def __init__(self):
        self.chatbot = Chatbot(
            config={
                "email": config.openai_login,
                "password": config.openai_password
            }
        )

    def send_message(self, message, dialog_messages=[], chat_mode="assistant"):
        if chat_mode not in CHAT_MODES.keys():
            raise ValueError(f"Chat mode {chat_mode} is not supported")

        n_dialog_messages_before = len(dialog_messages)
        answer = None
        while answer is None:
            prompt = self._generate_prompt(message, dialog_messages, chat_mode)
            loguru.logger.info(f'Prompt:\n{prompt}')
            cntr = 0
            for data in self.chatbot.ask(prompt):
                answer = data["message"]
                cntr += 1
                if cntr % 25 == 0:
                    loguru.logger.info('ChatGPT is writing answer...')
            loguru.logger.info(f'ChatGPT answer:\n{answer}')

            # forget first message in dialog_messages
            dialog_messages = dialog_messages[1:]

        n_first_dialog_messages_removed = n_dialog_messages_before - len(dialog_messages)

        return answer, prompt, n_first_dialog_messages_removed

    def _generate_prompt(self, message, dialog_messages, chat_mode):
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
