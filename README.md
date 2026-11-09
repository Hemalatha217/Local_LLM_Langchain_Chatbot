# Local_LLM_Langchain_Chatbot

# 🧬 Aivora Chatbot

### Intelligent Conversations Powered by Local LLM and LangChain Memory

Aivora Chatbot is an AI-powered conversational application developed using Streamlit, Ollama, and LangChain. It provides an interactive chatbot experience with conversation memory, allowing users to communicate with a locally running Large Language Model (LLM).

The application supports three types of LangChain memory and uses SQLite to permanently store conversations, making previous chats accessible even after restarting the application.

---

## 🚀 Features

- **Local LLM Integration:** Uses Ollama to run AI models locally.
- **LangChain Integration:** Uses LangChain to manage conversation context.
- **Buffer Memory:** Stores the complete conversation history.
- **Summary Memory:** Creates summaries of previous conversations.
- **Window Memory:** Retains the latest three conversation exchanges.
- **Conversation History:** Saves conversations using SQLite.
- **New Chat:** Allows users to start separate conversations.
- **Clear Current Chat:** Deletes messages from the selected conversation.
- **Clear All History:** Removes all saved conversations.
- **Interactive Interface:** Built using Streamlit with a white and purple theme.
- **Context-Aware Responses:** Uses previous conversation history to generate relevant responses.

---

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Programming language |
| Streamlit | User interface |
| Ollama | Local LLM execution |
| LangChain | Conversation management |
| LangChain Classic | Conversation memory |
| SQLite | Conversation storage |

---

## 🧠 LangChain Memory Types

### 1. Conversation Buffer Memory
Stores the complete conversation history, including user questions and AI responses.

### 2. Conversation Summary Memory
Maintains a summarized version of previous conversations to preserve important context.

### 3. Conversation Window Memory
Stores only the latest three conversation exchanges to maintain recent context.

---

## 📁 Project Structure

```text
Aivora-Chatbot/
│
├── app.py
├── requirements.txt
├── aivora.db
└── README.md
```

**Note:** `aivora.db` is automatically created when the application runs.

---

## ⚙️ Installation and Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/Aivora-Chatbot.git
```

### Step 2: Navigate to the Project Folder

```bash
cd Aivora-Chatbot
```

### Step 3: Create a Virtual Environment

```bash
python -m venv venv
```

### Step 4: Activate the Virtual Environment

For Windows:

```bash
venv\Scripts\activate
```

### Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 6: Install Ollama

Download Ollama from:

https://ollama.com/download

### Step 7: Download the LLM Model

```bash
ollama pull llama3.2
```

### Step 8: Start Ollama

```bash
ollama serve
```

### Step 9: Run the Application

Open another terminal in the project directory and execute:

```bash
streamlit run app.py
```

The application will open in your browser.

---

## 📦 Requirements

The project dependencies are listed in `requirements.txt`.

```text
streamlit
langchain-core
langchain-classic
langchain-ollama
requests
```

---

## 💬 How to Use

1. Launch the Aivora Chatbot application.
2. Select an Ollama language model.
3. Choose a LangChain memory type.
4. Click **New Chat** to start a conversation.
5. Enter your question in the chat input.
6. Receive AI-generated responses.
7. Access previous conversations from Chat History.
8. Use Clear Current Chat or Clear All History to manage conversations.

---

## 🔐 Data Storage

Aivora Chatbot uses SQLite to store:

- Conversation IDs
- Conversation titles
- User messages
- AI-generated responses
- Conversation timestamps

The conversation database is stored locally in `aivora.db`.

---

## 🎨 User Interface

The application features:

- White and purple gradient background.
- Light purple sidebar.
- Interactive chat interface.
- Conversation history management.
- Custom Aivora AI branding.

---

## 🔮 Future Enhancements

- User authentication.
- Export conversation history.
- Support for additional Ollama models.
- Document-based question answering.
- Voice input and output.
- Improved long-term conversational memory.

---

## 👩‍💻 Developer

**Hemalatha K**

Project: Aivora Chatbot

---

## ⭐ Acknowledgement

Developed using Python, Streamlit, Ollama, and LangChain.

