import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

anthropic_client: Anthropic = Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

all_user_messages: list[dict] = []

while True:
    print("\n")
    user_input: str = input("Enter message - ")

    if user_input == "/quit":
        break

    else:
        new_message: dict = {
            "role": "user",
            "content": user_input
        }

        all_user_messages.append(new_message)

        with anthropic_client.messages.stream(
                max_tokens=512,
                messages=all_user_messages,
                model="claude-haiku-5-5",
                system="You are a conversational agent. You need to maintain context of user's queries based on what they ask, and keep a "
                       "track of what they have asked / told you before."
                ) as stream:

            model_response: list[str] = []
            for text in stream.text_stream:
                print(text, end="", flush=True)
                model_response.append(text)

        all_user_messages.append({
            "role": "assistant",
            "content": "".join(model_response)
        })
