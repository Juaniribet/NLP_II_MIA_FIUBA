# AI Chat Assistant

A simple Streamlit-based chat interface for interacting with AI models.

## Features

- Simple username-based login
- Clean chat interface
- Message history during session
- Simulated response streaming

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and add your OpenAI API key:
   ```bash
   cp .env.example .env
   ```
4. Edit `.env` and set your `OPENAI_API_KEY`

## Running the Application

```bash
streamlit run main.py
```

## Project Structure

```
.
├── main.py              # Main application file
├── requirements.txt     # Project dependencies
├── .env                # Environment variables (create from .env.example)
└── src/
    └── utils/
        └── config.py   # Configuration settings
```

## Usage

1. Enter your username to start
2. Type your message in the chat input
3. Chat history is maintained during your session

## Requirements

- Python 3.8+
- Streamlit
- OpenAI Python client
- python-dotenv 