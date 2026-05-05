from anthropic import Anthropic
from dotenv import load_dotenv
import os

load_dotenv()

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def main():
    for message in client.messages.create(max_tokens=100,
            messages=[{"content": "Hello, how are you?", "role": "user"}],
            model="claude-haiku-4-5"
            ):
        print(message)


if __name__ == "__main__":
    main()
