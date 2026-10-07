# llm.py
#
# Two shared clients:
#
# - `llm`      : general-purpose, plain-text completions.
# - `llm_json` : identical model/config, but with Groq's native JSON mode
#                (response_format={"type": "json_object"}) turned on.


import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

_MODEL = "openai/gpt-oss-120b"
_API_KEY = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    model=_MODEL,
    api_key=_API_KEY,
    temperature=0.2,
    max_retries=5,
    max_tokens=4096,
)

llm_json = ChatGroq(
    model=_MODEL,
    api_key=_API_KEY,
    temperature=0.2,
    max_retries=5,
    max_tokens=4096,
    model_kwargs={"response_format": {"type": "json_object"}},
)