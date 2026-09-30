import logging
import math
import os
import requests
from config import TOPIC, TOPIC_DESCRIPTION, SIMILARITY_THRESHOLD

# Endpoints from the IFB220 API documentation
URL = "https://qut-ai.azure-api.net/ifb220/openai/deployments/gpt-4.1-mini/chat/completions?api-version=2025-03-01-preview"
EMBEDDING_URL = "https://qut-ai.azure-api.net/ifb220/openai/deployments/text-embedding-3-small/embeddings?api-version=2025-03-01-preview"

# Seconds to wait for an API response before giving up
REQUEST_TIMEOUT = 30

# Most user + assistant messages to keep (use an even number)
MAX_HISTORY_MESSAGES = 10

# Characters of the last assistant reply used as context in the topic check
CONTEXT_REPLY_CHARS = 200

# Basic greetings and thanks that skip the topic check
SOCIAL_MESSAGES = {
    "hi",
    "hello",
    "hey",
    "hi there",
    "hello there",
    "good morning",
    "good afternoon",
    "good evening",
    "thanks",
    "thank you",
}

# Log events to a file (never log keys or message contents)
logging.basicConfig(
    filename="chatbot.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

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
    logging.info("Embedding request sent")
    response = requests.post(
        EMBEDDING_URL, headers=headers, json=body, timeout=REQUEST_TIMEOUT
    )
    if response.status_code != 200:
        logging.error("Embedding request failed, status code %s", response.status_code)
    response.raise_for_status()
    data = response.json()
    logging.info("Embedding request succeeded")

    # Log token usage if the API provides it
    usage = data.get("usage")
    if usage:
        logging.info(
            "Embedding usage: prompt_tokens=%s total_tokens=%s",
            usage.get("prompt_tokens"),
            usage.get("total_tokens"),
        )
    return data["data"][0]["embedding"]


def cosine_similarity(a, b):
    # dot product divided by the lengths of both vectors
    dot = sum(x * y for x, y in zip(a, b))
    length_a = math.sqrt(sum(x * x for x in a))
    length_b = math.sqrt(sum(y * y for y in b))
    return dot / (length_a * length_b)


def is_basic_social_message(text):
    # True only for a short, exact greeting or thanks (not longer sentences)
    cleaned = text.lower().strip().rstrip("!.,?").strip()
    return cleaned in SOCIAL_MESSAGES


logging.info("Chatbot starting")

# Embed the topic description once (the chatbot can't run without it)
try:
    topic_embedding = get_embedding(TOPIC_DESCRIPTION)
except requests.RequestException as error:
    logging.error("Topic embedding failed: %s", type(error).__name__)
    raise SystemExit("Could not reach the embedding service. Please try again later.")

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

    logging.info("User input received")

    if is_basic_social_message(user_message):
        # Greetings and thanks skip the topic check
        logging.info("Social message allowed, embedding check skipped")
    else:
        # Short follow-ups like "why?" are only on topic because of the
        # previous exchange, so include it in the text we check.
        # This text is only used for the check, not sent to GPT.
        check_text = user_message
        if len(messages) > 2:
            last_user = messages[-2]["content"]
            last_reply = messages[-1]["content"][:CONTEXT_REPLY_CHARS]
            check_text = (
                f"Previous user message: {last_user}\n"
                f"Previous assistant reply: {last_reply}\n"
                f"Current user message: {user_message}"
            )

        # Check the message is related to the topic
        try:
            message_embedding = get_embedding(check_text)
        except requests.RequestException as error:
            logging.error("Embedding request error: %s", type(error).__name__)
            print("Bot: Sorry, I couldn't check that message. Please try again.")
            continue
        similarity = cosine_similarity(message_embedding, topic_embedding)
        logging.info(
            "Embedding check: similarity=%.3f threshold=%s used_context=%s",
            similarity,
            SIMILARITY_THRESHOLD,
            check_text != user_message,
        )
        if similarity < SIMILARITY_THRESHOLD:
            logging.warning("Message blocked: below similarity threshold")
            print(f"Bot: Sorry, I can only answer questions about {TOPIC}.")
            continue

    # Add the user's message to the conversation
    messages.append({"role": "user", "content": user_message})

    # Send the whole conversation to the API
    body = {
        "messages": messages,
        "max_tokens": 200,
    }
    logging.info("Chat API request sent")
    try:
        response = requests.post(
            URL, headers=headers, json=body, timeout=REQUEST_TIMEOUT
        )
    except requests.RequestException as error:
        logging.error("Chat API request error: %s", type(error).__name__)
        print("Bot: Sorry, I couldn't get a reply. Please try again.")
        # Remove the message so it isn't sent again
        messages.pop()
        continue

    if response.status_code == 200:
        # The reply text is inside choices -> message -> content
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        print("Bot:", reply)
        logging.info("Chat API response successful")

        # Log token usage if the API provides it
        usage = data.get("usage")
        if usage:
            logging.info(
                "Chat usage: prompt_tokens=%s completion_tokens=%s total_tokens=%s",
                usage.get("prompt_tokens"),
                usage.get("completion_tokens"),
                usage.get("total_tokens"),
            )

        # Add the reply to the conversation so the bot remembers it
        messages.append({"role": "assistant", "content": reply})

        # Keep the system message and only the most recent messages
        if len(messages) - 1 > MAX_HISTORY_MESSAGES:
            messages = [messages[0]] + messages[-MAX_HISTORY_MESSAGES:]
    else:
        logging.error("Chat API error, status code %s", response.status_code)
        print("Error:", response.status_code, response.text)
        # Remove the failed message so it isn't sent again
        messages.pop()

logging.info("Chatbot exiting")
