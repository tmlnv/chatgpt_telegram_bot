# chatgpt_telegram_bot
This is a Telegram bot that allows you to interact with ChatGPT, an advanced chatbot powered by OpenAI. The bot is designed to run via Docker Compose, making it easy to deploy and manage in any environment.

## Features
- Code highlighting
- Special chat modes: 👩🏼‍🎓 Assistant, 👩🏼‍💻 Code Assistant, 📝 Text Improver
- List of allowed Telegram users

## Bot commands
- `/retry` – Regenerate last bot answer
- `/new` – Start new conversation
- `/mode` – Select chat mode
- `/help` – Show help

## Setup
1. Create your [OpenAI](https://chat.openai.com/auth/login) account

2. Get your Telegram bot token from [@BotFather](https://t.me/BotFather)

3. Edit `config/config.example.yml` to set your telegram token and OpenAI credentials and run 2 commands below (*if you're advanced user, you can also edit* `config/config.example.env`):
```bash
mv config/config.example.yml config/config.yml
mv config/config.example.env config/config.env
```

And now **run**:

```bash
docker-compose --env-file config/config.env up --build
```

## References
1. [*Build ChatGPT from GPT-3*](https://learnprompting.org/docs/applied_prompting/build_chatgpt)
2. [*Reverse Engineered ChatGPT API by OpenAI*](https://github.com/acheong08/ChatGPT)
3. [*OpenAI Davinci API Telegram Bot*](https://github.com/karfly/chatgpt_telegram_bot)
