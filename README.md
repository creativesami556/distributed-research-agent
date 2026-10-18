# 🔬 Distributed Autonomous Research Agent

This repository contains a Streamlit-based autonomous AI research agent designed to run on top of a **distributed local LLM cluster**. 

By pooling the RAM of multiple low-resource computers using the `llama.cpp` RPC backend, you can run large open-weights models (like `Qwen2.5-7B`) entirely locally. The agent queries arXiv, searches the web via DuckDuckGo (`ddgs`), and synthesizes the findings into fully formatted IEEE `.docx` research papers.

## ⚙️ Phase 1: Set Up the Distributed Cluster

You need multiple computers on the same local network. 

1. **Download `llama.cpp`**: Download the compiled Windows `.zip` binaries from the [official llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases) on all machines.
2. **Launch Worker Nodes**: On your secondary computers (the workers), open Command Prompt in the extracted folder and run:
   ```cmd
   ggml-rpc-server.exe --host 0.0.0.0 --port 50052
