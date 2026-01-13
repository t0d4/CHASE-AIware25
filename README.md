# CHASE: LLM Agents for Dissecting Malicious PyPI Packages

This repository contains the project page and the implementation for our AIware 2025 paper.

**Live Page**: [https://t0d4.github.io/CHASE-AIware25/](https://t0d4.github.io/CHASE-AIware25/)

## About CHASE

CHASE (Collaborative Hierarchical Agents for Security Exploration) is a high-reliability multi-agent architecture for detecting malicious packages on PyPI. It achieves:

- **98.4% Recall** — Catches even highly evasive malicious packages designed to escape detection.
- **0.08% False Positive Rate** — Only 2 false alarms out of 2,500 benign packages
- **4.5 min median analysis time** — Practical for operational deployment

## Project Structure

```
.
├── docs/                       # Project Webpage Content
├── chase/
│   ├── agents/                 # Worker agents
│   │   ├── deobfuscator/       # Deobfuscator and its tools
│   │   ├── web_researcher/     # Web Researcher and its tools
│   │   └── __init__.py
│   ├── graph.py                # Global agent graph definition
│   ├── state.py                # CHASE's state definition
│   ├── supervisor.py           # Supervisor graph definition
│   ├── supervisor_prompts.py   # Prompts for Supervisor
│   └── __init__.py
├── run_chase.py                # Utility script to try CHASE
├── .env.template               # Configuration environment variables
└── README.md
```

## Setup

### 1. Install softwares

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (a splendid Python package and project manager)
- [Ollama](https://ollama.com/download) (an easy-to-use LLM inference engine, recommended for PCs) or [SGLang](https://docs.sglang.io/get_started/install.html) (a very fast and efficient LLM inference engine, typically used with professional GPUs)
- [Deno Runtime](https://docs.deno.com/runtime/getting_started/installation/) (required by [langchain-sandbox](https://github.com/langchain-ai/langchain-sandbox))

### 2. Prepare Python virtual environment

```bash
git clone https://github.com/t0d4/CHASE-AIware25.git
cd /path/to/CHASE-AIware25
uv sync
```

### 3. Prepare LLM inference engine

**Ollama**

```bash
ollama pull qwen3:32b
ollama pull qwen3:8b
ollama pull gemma3:4b
```

**SGLang**

Serve models through OpenAI-compatible API

- [Qwen/Qwen3-32B](https://huggingface.co/Qwen/Qwen3-32B)
  - at `http://127.0.0.1:30000`
  - with reasoning parser
- [Qwen/Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B)
  - at `http://127.0.0.1:30001`
  - with reasoning parser and tool call parser
- [google/gemma3-4b-it](https://huggingface.co/google/gemma-3-4b-it)
  - at `http://127.0.0.1:30002`

### 4. Configure CHASE

1. Rename [.env.template](/.env.template) to .env
2. Open .env and review the Web Researcher Configurations and modify them if necessary
   - Paid services used during experiments are replaced or deactivated by default so that anyone can easily try out the implementation
     1. DuckDuckGo is subsistuted for Tavily
     2. VirusTotal Analysis Tool is deactivated by default
3. (optional but highly recommended for observability) Visit [LangSmith](https://docs.langchain.com/langsmith/home), issue an API key, set it to `LANGSMITH_API_KEY`, and change `LANGSMITH_TRACING` to true
   - Note: execution trace will be sent to LangSmith without any change of code when `LANGSMITH_TRACING=true`.

## Usage

```bash
$ uv run run_chase.py --help
usage: run_chase.py [-h] --pkg-dirpath PKG_DIRPATH [--llm-runner {ollama,sglang}]
                    [--low-memory-mode]

options:
  -h, --help            show this help message and exit
  --pkg-dirpath PKG_DIRPATH
                        path to the python package directory right under which
                        setup.py is located
  --llm-runner {ollama,sglang}
                        llm runner to use to execute llm inference (default: ollama)
  --low-memory-mode     use small llms powered by Ollama to reduce required memory
                        (at the SIGNIFICANT cost of performance)
```

> [!NOTE]
> When your system doesn't have much VRAM, utilize `--low-memory-mode` flag. This will reduce memory footprint by using the small LLMs (qwen3:4b for the supervisor and workers, gemma3:4b for formatting), at the expense of analysis performance. Download them with `ollama pull` before using the flag.

### Examples

Please extract the archive files in [samples directory](/samples) before executing the below commands.

- Analyze [libstrreplacecpu-7.3](/samples/libstrreplacecpu-7.3.tar.gz) with CHASE, with the three LLMs powered by Ollama
  ```bash
  uv run run_chase.py --pkg-dirpath ./samples/libstrreplacecpu-7.3
  ```

- Analyze [ethereim-1.0.0](/samples/ethereim-1.0.0.tar.gz) with CHASE, with small LLMs powered by Ollama
  ```bash
  uv run run_chase.py --low-memory-mode --pkg-dirpath ./samples/ethereim-1.0.0
  ```

- Analyze [ethertoolz-0.8](/samples/ethertoolz-0.8.tar.gz) with CHASE, with the three LLMs powered by SGLang
  ```bash
  uv run run_chase.py --llm-runner sglang --pkg-dirpath ./samples/ethertoolz-0.8
  ```


## Citation

```bibtex
@inproceedings{toda2025CHASE,
  author       = {Takaaki Toda and Tatsuya Mori},
  title        = {{CHASE}: {LLM} Agents for Dissecting Malicious {PyPI} Packages},
  booktitle    = {Proceedings of the 2nd ACM International Conference on AI-Powered Software (AIware '25)},
  series       = {AIware 2025},
  publisher    = {IEEE},
  organization = {ACM and IEEE},
  address      = {Seoul, South Korea},
  year         = {2025},
  date         = {2025-11-19/20},
  doi          = {10.48550/arXiv.2601.06838},
  url          = {https://arxiv.org/abs/2601.06838}
}
```