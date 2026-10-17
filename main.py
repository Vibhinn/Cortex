import os
from textwrap import indent

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

anthropic_client: Anthropic = Anthropic(
    api_key=str(os.environ.get("ANTHROPIC_API_KEY"))
)

all_user_messages: list[dict] = []

while True:
    user_input: str = input("Enter message - ")

    if user_input == "/quit":
        break

    else:
        new_message: dict = {
            "role": "user",
            "content": user_input
        }

        all_user_messages.append(new_message)

        model_response = anthropic_client.messages.create(
            max_tokens=512,
            messages=all_user_messages,
            model="claude-haiku-5-5"
        )

        for block in model_response.content:
            if block.type == "text":
                print(block.text)
