# chatgpt_telegram_bot
This is a Telegram bot that allows you to interact with ChatGPT, an advanced chatbot powered by OpenAI. The bot is designed to run via Docker Compose, making it easy to deploy and manage in any environment.

## Features
- Code highlighting
- Chat modes: 🛎 Assistant, 💻 Code Assistant, 📝 Text Improver , ⚫ Blank, 🖼️ Image
- List of allowed Telegram users
- Message streaming
- Image generation via Kandinsky 2.2

## Bot commands
- `/new` – Start new conversation
- `/mode` – Select chat mode
- `/retry` – Regenerate last bot answer
- `/help` – Show help

## Setup
1. Get your Telegram bot token from [@BotFather](https://t.me/BotFather)

2. Edit `config/config.example.yml` to set your telegram token and OpenAI credentials (email and password or [OpenAI access_token](https://chat.openai.com/api/auth/session)) and run 2 commands below (*if you're advanced user, you can also edit* `config/config.example.env`):
```bash
mv config/config.example.yml config/config.yml
mv config/config.example.env config/config.env
```

And now **run**:

 ```bash
 docker-compose -f docker-compose.yml --env-file config/config.env up --build
 ```


## References
1. [*Build ChatGPT from GPT-3*](https://learnprompting.org/docs/applied_prompting/build_chatgpt)
2. [*Reverse Engineered ChatGPT API by OpenAI*](https://github.com/acheong08/ChatGPT)
3. [*OpenAI Davinci API Telegram Bot*](https://github.com/karfly/chatgpt_telegram_bot)
4. [*Kandinsky 2.2*](https://huggingface.co/kandinsky-community/kandinsky-2-2-decoder)
5. [*OpenAI API Free Reverse Proxy*](https://github.com/PawanOsman/ChatGPT)
6. [*GPT4FREE*](https://github.com/xtekky/gpt4free)
