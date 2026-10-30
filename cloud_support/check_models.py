"""Real chat and embedding smoke test; never print credentials."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import load_settings
from app.llm import LLMClient

client = LLMClient(load_settings())
reply = client.chat([{'role': 'user', 'content': 'Reply with OK.'}])
vectors = client.embed(['TokoKita shipping policy'])
assert vectors and vectors[0], 'Empty embedding'
print('chat:', reply.get('content'))
print('embedding dimensions:', len(vectors[0]))
