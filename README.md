# IFB220 Topic-Constrained Chatbot

A simple command-line chatbot built for IFB220. It uses GPT-4.1-mini through the IFB220 API, but it only answers questions about one chosen topic (climbing by default). Questions on other topics are blocked before they reach the model.

## Features

- Command-line chat with GPT-4.1-mini (Chat Completions API)
- Keeps the conversation history, so follow-up questions work
- Topic guardrail using text-embedding-3-small and cosine similarity
- System message that also tells the model to stay on topic
- Topic, topic description and similarity threshold set in `config.py`
- Type `quit` to exit
- API key is read from an environment variable, not stored in the code

## Technologies Used

- Python 3
- `requests` library
- Built-in `math` and `os` modules
- IFB220 API (GPT-4.1-mini and text-embedding-3-small)

## How It Works

1. On start-up, the topic description from `config.py` is turned into an embedding (a list of numbers that represents its meaning).
2. When you type a message, it is also turned into an embedding.
3. The two embeddings are compared using cosine similarity.
4. If the score is below `SIMILARITY_THRESHOLD`, the chatbot replies that it can only answer questions about the topic. The message is not sent to GPT.
5. If the score passes, the message is added to the conversation and the whole conversation is sent to GPT-4.1-mini. The reply is printed and added to the conversation.

## Project Structure

```
IFB220_Chatbot/
├── main.py            # Chatbot loop, API calls and topic filter
├── config.py          # Topic, topic description and similarity threshold
├── requirements.txt   # Python dependencies (requests)
└── README.md
```

## Setup and Installation

1. Install Python 3.
2. Open a terminal in the project folder.
3. Install the dependencies:

```powershell
pip install -r requirements.txt
```

4. Get your API key from the IFB220 API Portal (do not put it in the code or commit it anywhere).

## Setting the API_KEY Environment Variable (PowerShell)

For the current PowerShell window only:

```powershell
$env:API_KEY = "your-api-key-here"
```

Replace `your-api-key-here` with your own key. You will need to set it again in each new PowerShell window.

## Running the Chatbot

```powershell
python main.py
```

Type your message and press Enter. Type `quit` to exit.

To change the topic, edit `TOPIC` and `TOPIC_DESCRIPTION` in `config.py`.

## Example Interaction

The replies below are only an illustration. Real answers from the model will vary.

```
Type 'quit' to exit.
You: What is the difference between sport and trad climbing?
Bot: In sport climbing the bolts are already fixed to the rock, while in trad
climbing you place your own protection as you climb...
You: What is the capital of France?
Bot: Sorry, I can only answer questions about climbing.
You: quit
```

## Embedding-Based Topic Filtering

An embedding turns text into a list of numbers so that texts with similar meanings end up with similar numbers. The chatbot gets an embedding for the topic description and one for each user message.

Cosine similarity measures how close the two embeddings point in the same direction. It is calculated as the dot product of the two lists divided by the product of their lengths. The result is usually between 0 and 1 here, where a higher number means the meanings are more alike.

The chatbot compares this score to `SIMILARITY_THRESHOLD` in `config.py` (currently 0.3). A message scoring below it is treated as off-topic. The 0.3 value is a starting point that I tested and can adjust, so it is not a perfect rule. Very short follow-up messages may sometimes score low even when they are on topic.
