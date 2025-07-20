import os
from llama_cpp import Llama

path = os.getenv("LLAMA_MODEL_PATH", "tinyllama-1.1b-chat-v1.0.Q5_K_M.gguf")
print("Looking for model at:", path)
# This will raise immediately if the file is missing or invalid:
llm = Llama(model_path=path, n_ctx=1024, embedding=True, n_threads=1)
print("✅ Loaded model successfully!")

