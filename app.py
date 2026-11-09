
import os
import uuid
import sqlite3
from pathlib import Path

import requests
import streamlit as st

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

from langchain_classic.memory import (
    ConversationBufferMemory,
    ConversationSummaryMemory,
    ConversationBufferWindowMemory
)


# =====================================================
# 1. PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="Aivora chatbot",
    page_icon="🧬",
    layout="wide"
)

APP_TITLE = "Aivora chatbot"
DEFAULT_MODEL = "llama3.2"

OLLAMA_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"
)

DB_PATH = Path(__file__).parent / "aivora.db"


# =====================================================
# 2. SQLITE DATABASE
# =====================================================

def get_connection():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id)
                REFERENCES conversations(id)
        )
    """)

    conn.commit()
    conn.close()


init_db()


# =====================================================
# 3. CONVERSATION FUNCTIONS
# =====================================================

def create_conversation():

    chat_id = str(uuid.uuid4())

    conn = get_connection()

    conn.execute("""
        INSERT INTO conversations (id, title)
        VALUES (?, ?)
    """, (chat_id, "New Chat"))

    conn.commit()
    conn.close()

    return chat_id


def get_conversations():

    conn = get_connection()

    rows = conn.execute("""
        SELECT id, title, updated_at
        FROM conversations
        ORDER BY updated_at DESC
    """).fetchall()

    conn.close()

    return [dict(row) for row in rows]


def get_messages(chat_id):

    conn = get_connection()

    rows = conn.execute("""
        SELECT role, content
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
    """, (chat_id,)).fetchall()

    conn.close()

    return [dict(row) for row in rows]


def save_conversation(chat_id, user_input, answer):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO messages (
            conversation_id, role, content
        )
        VALUES (?, ?, ?)
    """, (chat_id, "user", user_input))

    cursor.execute("""
        INSERT INTO messages (
            conversation_id, role, content
        )
        VALUES (?, ?, ?)
    """, (chat_id, "assistant", answer))

    result = cursor.execute("""
        SELECT title
        FROM conversations
        WHERE id = ?
    """, (chat_id,)).fetchone()

    if result and result["title"] == "New Chat":

        title = " ".join(user_input.split())

        if len(title) > 40:
            title = title[:40] + "..."

        cursor.execute("""
            UPDATE conversations
            SET title = ?
            WHERE id = ?
        """, (title, chat_id))

    cursor.execute("""
        UPDATE conversations
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (chat_id,))

    conn.commit()
    conn.close()


def clear_current_chat(chat_id):

    conn = get_connection()

    conn.execute("""
        DELETE FROM messages
        WHERE conversation_id = ?
    """, (chat_id,))

    conn.execute("""
        UPDATE conversations
        SET title = 'New Chat',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (chat_id,))

    conn.commit()
    conn.close()


def clear_all_history():

    conn = get_connection()

    conn.execute("DELETE FROM messages")

    conn.execute("DELETE FROM conversations")

    conn.commit()
    conn.close()


# =====================================================
# 4. LOAD OLLAMA MODEL
# =====================================================

@st.cache_resource
def load_llm(model_name, base_url):

    return ChatOllama(
        model=model_name,
        base_url=base_url,
        temperature=0.3,
        num_predict=2048,
        num_ctx=4096
    )


def ollama_is_running():

    try:

        response = requests.get(
            f"{OLLAMA_URL}/api/tags",
            timeout=3
        )

        return response.ok

    except requests.RequestException:

        return False


# =====================================================
# 5. LANGCHAIN MEMORY
# =====================================================

def create_memory(memory_type, llm):

    if memory_type == "Buffer Memory":

        return ConversationBufferMemory(
            memory_key="history",
            input_key="input",
            output_key="output",
            return_messages=False
        )

    elif memory_type == "Summary Memory":

        return ConversationSummaryMemory(
            llm=llm,
            memory_key="history",
            input_key="input",
            output_key="output",
            return_messages=False
        )

    elif memory_type == "Window Memory":

        return ConversationBufferWindowMemory(
            k=3,
            memory_key="history",
            input_key="input",
            output_key="output",
            return_messages=False
        )


def load_memory(chat_id, memory_type, llm):

    memory = create_memory(memory_type, llm)

    messages = get_messages(chat_id)

    # Restore saved conversation in pairs.
    # This also allows Summary Memory to rebuild its summary.

    pending_user_message = None

    for message in messages:

        if message["role"] == "user":

            pending_user_message = message["content"]

        elif (
            message["role"] == "assistant"
            and pending_user_message is not None
        ):

            memory.save_context(
                {"input": pending_user_message},
                {"output": message["content"]}
            )

            pending_user_message = None

    return memory


# =====================================================
# 6. AI RESPONSE GENERATION
# =====================================================

def generate_response(user_input, llm, memory):

    memory_data = memory.load_memory_variables({})

    history = memory_data.get("history", "")

    prompt = ChatPromptTemplate.from_messages([

        (
            "system",
            """
            You are Aivora AI, an intelligent and friendly AI assistant.

            YOUR MAIN RESPONSIBILITIES:

            - Understand the complete question.
            - Give accurate and meaningful answers.
            - Use simple and understandable English.
            - Answer the actual question instead of giving unrelated content.
            - Remember relevant previous conversations.
            - Do not invent information.

            ANSWER FORMATTING RULES:

            1. Use clear headings for different topics.
            2. Use numbered lists for explanations containing multiple points.
            3. Use bullet points for examples and subtopics.
            4. Use bold text for important keywords.
            5. Explain every point in complete sentences.
            6. Do not skip requested points.
            7. Do not combine multiple requested points into one sentence.
            8. Give examples when useful.
            9. For educational questions, provide structured answers.
            10. For programming questions, provide correct code
                and explain the important steps.
            11. Avoid unnecessary repetition.
            12. Never end an answer in the middle of a sentence.

            IMPORTANT NUMBERED LIST INSTRUCTION:

            When a user asks for points, features, types,
            characteristics, advantages, disadvantages,
            steps or applications, display each point separately.

            Example format:

            1. **Learning:** Explain the point here.

            2. **Reasoning:** Explain the point here.

            3. **Perception:** Explain the point here.

            4. **Natural Language Processing:** Explain the point here.

            Do not omit the numbers or the explanations.

            FORMAT YOUR ANSWERS USING MARKDOWN.

            PREVIOUS CONVERSATION:
            {history}
            """
        ),

        (
            "human",
            """
            User question:
            {input}

            Provide a complete and properly structured answer.
            If the question requests multiple points, include every
            requested point separately using numbered Markdown lists.
            """
        )

    ])

    chain = prompt | llm

    response = chain.invoke({
        "history": history,
        "input": user_input
    })

    answer = response.content

    if isinstance(answer, list):

        answer = "\n".join(
            str(part) for part in answer
        )

    answer = str(answer).strip()

    if not answer:

        raise ValueError("The AI returned an empty response.")

    # Save the exchange in LangChain memory.

    memory.save_context(
        {"input": user_input},
        {"output": answer}
    )

    return answer


# =====================================================
# 7. SESSION STATE
# =====================================================

if "chat_id" not in st.session_state:

    conversations = get_conversations()

    if conversations:

        st.session_state.chat_id = conversations[0]["id"]

    else:

        st.session_state.chat_id = create_conversation()


# =====================================================
# 8. WHITE AND PURPLE THEME
# =====================================================

st.markdown("""
<style>

/* MAIN BACKGROUND */

.stApp {
    background: linear-gradient(
        135deg,
        #FFFFFF 0%,
        #F8F3FF 50%,
        #EDE4FF 100%
    ) !important;

    color: #352052 !important;
}

/* MAIN CONTAINER */

[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background: transparent !important;
}

/* HEADER */

header[data-testid="stHeader"] {
    background: #F7F1FF !important;
}

/* SIDEBAR */

section[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #F7F0FF,
        #E5D8FF
    ) !important;

    border-right: 1px solid #D8C5FF;
}

/* SIDEBAR TEXT */

section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] span {
    color: #45266E !important;
}

/* SIDEBAR HEADINGS */

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #7028D8 !important;
}

/* MAIN TITLE */

.main-title {
    text-align: center;
    font-size: 42px;
    font-weight: 850;

    background: linear-gradient(
        90deg,
        #8B5CF6,
        #6D28D9,
        #A855F7
    );

    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;

    margin-top: 15px;
}

/* SUBTITLE */

.subtitle {
    text-align: center;
    color: #806A9E !important;
    font-size: 16px;
    margin-bottom: 25px;
}

/* CHAT MESSAGE BOX */

[data-testid="stChatMessage"] {
    background: #FFFFFF !important;
    border: 1px solid #D8C5FF !important;
    border-radius: 18px !important;
    padding: 18px !important;

    box-shadow: 0 3px 12px
        rgba(109, 40, 217, 0.06);
}

/* CHAT ANSWER TEXT */

[data-testid="stChatMessage"] .stMarkdown {
    color: #352052 !important;
}

/* PARAGRAPHS */

[data-testid="stChatMessage"] p {
    color: #352052 !important;
    -webkit-text-fill-color: #352052 !important;
    font-size: 16px !important;
    line-height: 1.8 !important;
}

/* NUMBERED LISTS */

[data-testid="stChatMessage"] ol {
    display: block !important;
    list-style-type: decimal !important;
    list-style-position: outside !important;
    padding-left: 35px !important;
    margin: 12px 0 !important;
}

/* BULLET LISTS */

[data-testid="stChatMessage"] ul {
    display: block !important;
    list-style-type: disc !important;
    padding-left: 35px !important;
    margin: 12px 0 !important;
}

/* LIST ITEMS */

[data-testid="stChatMessage"] li {
    display: list-item !important;
    color: #352052 !important;
    -webkit-text-fill-color: #352052 !important;
    font-size: 16px !important;
    line-height: 1.9 !important;
    margin-bottom: 9px !important;
    padding-left: 5px !important;
}

/* BOLD TEXT */

[data-testid="stChatMessage"] strong {
    color: #7028D8 !important;
    -webkit-text-fill-color: #7028D8 !important;
    font-weight: 750 !important;
}

/* ANSWER HEADINGS */

[data-testid="stChatMessage"] h1,
[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3,
[data-testid="stChatMessage"] h4 {
    color: #7028D8 !important;
    -webkit-text-fill-color: #7028D8 !important;
}

/* CODE BLOCK */

[data-testid="stChatMessage"] pre {
    background: #F1E9FF !important;
    border: 1px solid #D8C5FF !important;
    border-radius: 12px !important;
}

[data-testid="stChatMessage"] pre code {
    color: #352052 !important;
}

/* CHAT INPUT BACKGROUND */

[data-testid="stBottom"],
[data-testid="stBottomBlockContainer"],
.stChatFloatingInputContainer {
    background: #F5EEFF !important;
    box-shadow: none !important;
}

/* CHAT INPUT */

[data-testid="stChatInput"] {
    background: #FFFFFF !important;
    border: 1.5px solid #A78BFA !important;
    border-radius: 16px !important;
}

/* INPUT TEXT */

[data-testid="stChatInput"] textarea {
    background: #FFFFFF !important;
    color: #352052 !important;
    -webkit-text-fill-color: #352052 !important;
    caret-color: #7C3AED !important;
}

/* PLACEHOLDER */

[data-testid="stChatInput"] textarea::placeholder {
    color: #9B87B9 !important;
    -webkit-text-fill-color: #9B87B9 !important;
}

/* BUTTONS */

.stButton button {
    background: linear-gradient(
        100deg,
        #A78BFA,
        #7C3AED
    ) !important;

    color: #FFFFFF !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 650 !important;
}

/* BUTTON HOVER */

.stButton button:hover {
    background: linear-gradient(
        100deg,
        #8B5CF6,
        #6D28D9
    ) !important;
    color: #FFFFFF !important;
}

/* SELECT BOX */

[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background: #FFFFFF !important;
    border: 1px solid #C4B5FD !important;
    border-radius: 10px !important;
}

/* EXPANDER */

[data-testid="stExpander"] {
    background: #FFFFFF !important;
    border: 1px solid #C4B5FD !important;
    border-radius: 14px !important;
}

/* DIVIDER */

hr {
    border-color: #D8C5FF !important;
}

/* ALERTS */

[data-testid="stAlert"] {
    background: #F3E8FF !important;
    border: 1px solid #C4B5FD !important;
}

</style>
""", unsafe_allow_html=True)


# =====================================================
# 9. LOAD MODEL
# =====================================================

with st.sidebar:

    st.markdown("## 🧬 Aivora AI")

    st.caption("Your Intelligent AI Companion")

    st.divider()

    st.markdown("### ⚙️ AI Settings")

    model_name = st.selectbox(
        "Select Local LLM",
        [
            "llama3.2",
            "llama3.1",
            "mistral"
        ]
    )

    memory_type = st.selectbox(
        "Select Memory Type",
        [
            "Buffer Memory",
            "Summary Memory",
            "Window Memory"
        ]
    )

    memory_descriptions = {

        "Buffer Memory":
        "Stores the complete conversation history.",

        "Summary Memory":
        "Creates a running summary of previous conversations.",

        "Window Memory":
        "Stores the latest 3 conversation exchanges."
    }

    st.info(memory_descriptions[memory_type])

    st.divider()

    # NEW CHAT

    if st.button(
        "＋ New Chat",
        use_container_width=True
    ):

        st.session_state.chat_id = create_conversation()

        st.rerun()

    # CHAT HISTORY

    st.markdown("### 💬 Chat History")

    conversations = get_conversations()

    if conversations:

        chat_ids = [
            item["id"] for item in conversations
        ]

        chat_titles = {
            item["id"]: item["title"]
            for item in conversations
        }

        current_index = (
            chat_ids.index(st.session_state.chat_id)
            if st.session_state.chat_id in chat_ids
            else 0
        )

        selected_chat = st.selectbox(
            "Previous Conversations",
            options=chat_ids,
            index=current_index,
            format_func=lambda x: chat_titles[x],
            label_visibility="collapsed"
        )

        if selected_chat != st.session_state.chat_id:

            st.session_state.chat_id = selected_chat

            st.rerun()

    else:

        st.caption("No conversations available.")

    st.divider()

    # CLEAR CURRENT CHAT

    if st.button(
        "🗑 Clear Current Chat",
        use_container_width=True
    ):

        clear_current_chat(
            st.session_state.chat_id
        )

        st.rerun()

    # CLEAR ALL HISTORY

    if st.button(
        "⚠️ Clear All History",
        use_container_width=True
    ):

        clear_all_history()

        st.session_state.chat_id = create_conversation()

        st.rerun()

    st.divider()

    st.caption("⚡ Powered by Ollama")

    st.caption("💾 SQLite Storage")


# =====================================================
# 10. MAIN PAGE
# =====================================================

st.markdown(
    '<div class="main-title">🧬 AIVORA CHATBOT</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Intelligent Conversations Powered by Local LLM and LangChain Memory'
    '</div>',
    unsafe_allow_html=True
)

st.caption(
    f"Model: {model_name}  |  Memory: {memory_type}"
)

st.divider()


# =====================================================
# 11. CONNECTION STATUS
# =====================================================

if ollama_is_running():

    st.success("🟢 Ollama is connected")

else:

    st.error("🔴 Ollama is not responding")

    st.info(
        "Start Ollama using the command: ollama serve"
    )

    st.stop()


# =====================================================
# 12. INITIALIZE LLM AND MEMORY
# =====================================================

try:

    llm = load_llm(
        model_name,
        OLLAMA_URL
    )

    memory = load_memory(
        st.session_state.chat_id,
        memory_type,
        llm
    )

except Exception as error:

    st.error(f"Initialization error: {error}")

    st.stop()


# =====================================================
# 13. DISPLAY SAVED CONVERSATIONS
# =====================================================

messages = get_messages(
    st.session_state.chat_id
)

if not messages:

    st.markdown("## 👋 Hello! How can I help you today?")

    st.caption(
        "Start a conversation with Aivora AI."
    )


for message in messages:

    with st.chat_message(message["role"]):

        st.markdown(
            message["content"],
            unsafe_allow_html=False
        )


# =====================================================
# 14. VIEW MEMORY
# =====================================================

with st.expander("📚 View Memory Contents"):

    memory_data = memory.load_memory_variables({})

    st.markdown(
        f"**Active Memory:** {memory_type}"
    )

    st.write(
        memory_data.get(
            "history",
            "No memory available yet."
        )
    )


# =====================================================
# 15. CHAT INPUT AND RESPONSE
# =====================================================

user_input = st.chat_input(
    "Message Aivora AI..."
)

if user_input:

    # SHOW USER MESSAGE

    with st.chat_message("user"):

        st.markdown(
            user_input
        )

    # GENERATE AI ANSWER

    with st.chat_message("assistant"):

        with st.spinner("Aivora AI is thinking..."):

            try:

                answer = generate_response(
                    user_input,
                    llm,
                    memory
                )

                # DISPLAY COMPLETE MARKDOWN ANSWER

                st.markdown(
                    answer,
                    unsafe_allow_html=False
                )

                # SAVE CONVERSATION

                save_conversation(
                    st.session_state.chat_id,
                    user_input,
                    answer
                )

            except Exception as error:

                st.error(
                    f"Unable to generate response: {error}"
                )

                st.info(
                    "Check the selected Ollama model "
                    "and try again."
                )

    # REFRESH CHAT HISTORY

    st.rerun()
