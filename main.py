import math
import os
import requests
from config import TOPIC, TOPIC_DESCRIPTION, SIMILARITY_THRESHOLD

# Endpoints from the IFB220 API documentation
URL = "https://qut-ai.azure-api.net/ifb220/openai/deployments/gpt-4.1-mini/chat/completions?api-version=2025-03-01-preview"
EMBEDDING_URL = "https://qut-ai.azure-api.net/ifb220/openai/deployments/text-embedding-3-small/embeddings?api-version=2025-03-01-preview"

# Most user + assistant messages to keep (use an even number)
MAX_HISTORY_MESSAGES = 10

# Read the API key from the environment (never hard-code it)
api_key = os.environ.get("API_KEY")
if not api_key:
    raise SystemExit("API_KEY environment variable is not set.")

# Headers required by the IFB220 API Portal
headers = {
    "Content-Type": "application/json",
    "Cache-Control": "no-cache",
    "api-key": api_key,
}


def get_embedding(text):
    # Send the text to the embedding endpoint and return the vector
    body = {"input": text}
    response = requests.post(EMBEDDING_URL, headers=headers, json=body)
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def cosine_similarity(a, b):
    # dot product divided by the lengths of both vectors
    dot = sum(x * y for x, y in zip(a, b))
    length_a = math.sqrt(sum(x * x for x in a))
    length_b = math.sqrt(sum(y * y for y in b))
    return dot / (length_a * length_b)


# Embed the topic description once
topic_embedding = get_embedding(TOPIC_DESCRIPTION)

# System message that keeps the assistant on the topic
system_message = (
    f"You are a {TOPIC} assistant. "
    f"Only answer questions related to {TOPIC}. "
    f"If a question is not about {TOPIC}, politely say you can only help with {TOPIC}."
)

# The conversation starts with the system message
messages = [
    {"role": "system", "content": system_message},
]

print("Type 'quit' to exit.")

while True:
    # Get the user's message
    user_message = input("You: ")
    if user_message.lower() == "quit":
        break

    # Ignore empty messages
    if user_message.strip() == "":
        continue

    # Check the message is related to the topic
    message_embedding = get_embedding(user_message)
    similarity = cosine_similarity(message_embedding, topic_embedding)
    if similarity < SIMILARITY_THRESHOLD:
        print(f"Bot: Sorry, I can only answer questions about {TOPIC}.")
        continue

    # Add the user's message to the conversation
    messages.append({"role": "user", "content": user_message})

    # Send the whole conversation to the API
    body = {
        "messages": messages,
        "max_tokens": 200,
    }
    response = requests.post(URL, headers=headers, json=body)

    if response.status_code == 200:
        # The reply text is inside choices -> message -> content
        reply = response.json()["choices"][0]["message"]["content"]
        print("Bot:", reply)

        # Add the reply to the conversation so the bot remembers it
        messages.append({"role": "assistant", "content": reply})

        # Keep the system message and only the most recent messages
        if len(messages) - 1 > MAX_HISTORY_MESSAGES:
            messages = [messages[0]] + messages[-MAX_HISTORY_MESSAGES:]
    else:
        print("Error:", response.status_code, response.text)
        # Remove the failed message so it isn't sent again
        messages.pop()
