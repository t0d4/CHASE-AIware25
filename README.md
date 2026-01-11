# CHASE: LLM Agents for Dissecting Malicious PyPI Packages

This repository contains the project page for our AIware 2025 paper.

**Live Page**: [https://t0d4.github.io/CHASE-AIware25/](https://t0d4.github.io/CHASE-AIware25/)

## About CHASE

CHASE (Collaborative Hierarchical Agents for Security Exploration) is a high-reliability multi-agent architecture for detecting malicious packages on PyPI. It achieves:

- **98.4% Recall** — Catches even highly evasive malicious packages designed to escape detection.
- **0.08% False Positive Rate** — Only 2 false alarms out of 2,500 benign packages
- **4.5 min median analysis time** — Practical for operational deployment

## Project Structure

```
.
├── docs/                   # Project Webpage Content
├── chase/
│   ├── agents/
│   │   ├── deobfuscator     # Site favicon (replace with your own)
│   │   └── web_researcher  # Social media preview image
│   ├── graph.py
│   ├── state.py
│   ├── supervisor.py
│   └── supervisor_prompts.py
├── run_agent.py            # Entrypoint of the implementation
└── README.md
```

## Setup

{TO BE FILLED}

## Citation

```bibtex
@inproceedings{toda2025chase,
  title        = {{CHASE}: {LLM} Agents for Dissecting Malicious {PyPI} Packages},
  author       = {Takaaki Toda and Tatsuya Mori},
  booktitle    = {Proceedings of the 2nd ACM International Conference on AI-Powered Software (AIware '25)},
  series       = {AIware 2025},
  year         = {2025},
  date         = {2025-11-19/20},
  address      = {Seoul, South Korea},
  publisher    = {IEEE},
  organization = {ACM and IEEE}
}
```