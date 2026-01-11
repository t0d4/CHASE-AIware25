---
layout: default
---

<h1 align="center">CHASE: LLM Agents for Dissecting Malicious PyPI Packages</h1>

<p align="center">
  <a href="mailto:todatakaaki@nsl.cs.waseda.ac.jp">Takaaki Toda</a><sup>1,2</sup> &nbsp;&nbsp;
  <a href="https://nsl.cs.waseda.ac.jp/">Tatsuya Mori</a><sup>1,2,3</sup>
</p>

<p align="center">
  <sup>1</sup>Waseda University &nbsp;&nbsp;
  <sup>2</sup>RIKEN AIP &nbsp;&nbsp;
  <sup>3</sup>NICT
</p>

<p align="center">
  <a href="#">
    <img src="https://img.shields.io/badge/Paper-PDF-red?style=flat-square" alt="Paper">
  </a>
  <a href="https://github.com/t0d4/CHASE-AIware25">
    <img src="https://img.shields.io/badge/Code-GitHub-blue?style=flat-square&logo=github" alt="Code">
  </a>
  <a href="https://github.com/lxyeternal/pypi_malregistry">
    <img src="https://img.shields.io/badge/Dataset-pypi__malregistry-green?style=flat-square" alt="Dataset">
  </a>
</p>

---

## Abstract

Modern software package registries like PyPI have become critical infrastructure for software development, but are increasingly exploited by threat actors distributing malicious packages with sophisticated multi-stage attack chains. While Large Language Models (LLMs) offer promising capabilities for automated code analysis, their application to security-critical malware detection faces fundamental challenges, including **hallucination** and **context confusion**, which can lead to missed detections or false alarms.

We present **CHASE** (**C**ollaborative **H**ierarchical **A**gents for **S**ecurity **E**xploration), a high-reliability multi-agent architecture that addresses these limitations through:
- A **Plan-and-Execute** coordination model
- **Specialized Worker Agents** focused on specific analysis aspects
- Integration with **deterministic security tools** for critical operations

Our key insight is that **reliability in LLM-based security analysis emerges not from improving individual model capabilities but from architecting systems that compensate for LLM weaknesses while leveraging their semantic understanding strengths**.

---

## Key Results

<table align="center">
  <thead>
    <tr>
      <th>Method</th>
      <th>Precision</th>
      <th>Recall</th>
      <th>F1</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>MalGuard (RF)</td>
      <td>0.972</td>
      <td>0.922</td>
      <td>0.946</td>
    </tr>
    <tr>
      <td>GuardDog</td>
      <td>0.675</td>
      <td>0.854</td>
      <td>0.754</td>
    </tr>
    <tr>
      <td><strong>CHASE (Ours)</strong></td>
      <td><strong>0.996</strong></td>
      <td><strong>0.984</strong></td>
      <td><strong>0.990</strong></td>
    </tr>
  </tbody>
</table>

Evaluated on a dataset of **3,000 real-world packages** (500 malicious, 2,500 benign), CHASE achieves:

- :dart: **98.4% Recall** — Catches nearly all malicious packages
- :shield: **0.08% False Positive Rate** — Only 2 false alarms out of 2,500 benign packages
- :clock1: **4.5 min median analysis time** — Practical for operational deployment

---

## Why CHASE?

Existing detection methods face a fundamental limitation: they can identify *where* suspicious code exists, but struggle to explain *what* it actually does.

| Capability | MalGuard | GuardDog | CHASE |
|:-----------|:--------:|:--------:|:-----:|
| Detection Performance | :white_check_mark: Strong | :small_orange_diamond: Limited | :white_check_mark: Strong |
| **Where is suspicious?** | :white_check_mark: Yes | :white_check_mark: Yes | :white_check_mark: Yes |
| **What does it do?** | :x: Limited | :x: Limited | :white_check_mark: **Yes** |

CHASE actively **deobfuscates layered payloads** and **retrieves remote content** to reveal the attacker's true intent, producing high-fidelity, actionable reports that include:

- Complete attack chain reconstruction
- Attacker's ultimate goal
- Indicators of Compromise (IoCs)

---

## Architecture

CHASE's design is inspired by how human security experts analyze malicious code. Professional analysts dynamically switch between **exploratory activities** (surveying code to form hypotheses) and **exploitative activities** (focusing on specific tasks like deobfuscation).

<!-- TODO: Insert Figure 1 from the paper -->
*Figure 1: The multi-agent architecture of CHASE, using a Plan-and-Execute workflow and a Supervisor-Worker model.*

### Design Principles

**1. Supervisor-Worker Multi-Agent Architecture**

A single **Supervisor** agent maintains the global analysis perspective, while specialized **Worker** agents execute domain-specific tasks:
- **Deobfuscator**: Handles code deobfuscation, decryption, and safe execution
- **Web Researcher**: Investigates external resources and queries threat intelligence

**2. Plan-and-Execute Workflow**

Unlike reactive approaches (e.g., ReAct) that get trapped in repetitive failures, CHASE's Supervisor dynamically adjusts its analysis plan based on Worker results—crucial for malware analysis where outcomes are unpredictable.

**3. Reliability-Oriented Coordination**

- **State-Based Communication**: Avoids context poisoning by maintaining all information in a central state variable
- **Minimal Toolsets**: Each Worker has only the tools it needs, preventing cognitive overload
- **Budget-Aware Planning**: Prevents infinite loops common in multi-agent systems

---

## Analysis Example

The following trace shows CHASE analyzing `libstrreplacecpu-7.3`, a malicious package that downloads and executes a malicious executable via an obfuscated PowerShell command.

<!-- TODO: Insert Figure 3 from the paper -->
*Figure 3: The analysis trace for `libstrreplacecpu-7.3` as generated by CHASE.*

### Step-by-Step Analysis

1. **Supervisor** creates an initial plan after observing the raw source code
2. **Supervisor** delegates the obfuscated PowerShell command to **Deobfuscator**
3. **Deobfuscator** decrypts the base64 payload, revealing a Dropbox download URL
4. **Supervisor** updates the plan based on the new finding
5. **Web Researcher** investigates the URL via VirusTotal — flagged by 7/63 vendors
6. **Web Researcher** investigates the author's email and suspicious domain
7. **Supervisor** compiles the final analysis report

### Generated Report (Excerpt)

```markdown
## Final Verdict
**Malicious logic detected**

The code contains explicit malicious logic that downloads and executes
an external executable ('Esquele.exe') without user consent.

## Indicators of Compromise (IOCs)
- **URL:** 'https://dl.dropbox.com/.../Esquele.exe' (flagged by 7/63 vendors)
- **Domain:** 'esquelesquad.rip' (flagged by 9/65 vendors)
- **Email:** 'tahgoficial@proton.me'
```

---

## Model Configuration

CHASE employs a tiered hierarchy of **local LLMs** via [SGLang](https://docs.sglang.ai/) to balance capability with cost:

| Role | Model | Purpose |
|:-----|:------|:--------|
| Supervisor | Qwen3:32B | Multi-step reasoning, plan orchestration |
| Workers | Qwen3:8B | Focused, domain-specific tasks |
| Structurizer | Gemma3:4B | JSON output conversion |

This configuration runs on a **single NVIDIA H100 NVL**, making it economically feasible for continuous monitoring.

---

## Expert Evaluation

We conducted a user study with **three cybersecurity professionals** (security strategist, red team engineer, threat intelligence analyst) to evaluate report quality across five dimensions:

| Dimension | Benign | Malicious 1 | Malicious 2 |
|:----------|:------:|:-----------:|:-----------:|
| Accuracy | 3.6 | 3.8 | 3.7 |
| Completeness | 2.9 | 4.0 | 4.2 |
| Clarity | 4.1 | 3.9 | 4.3 |
| Actionability | 3.1 | 4.0 | 3.8 |
| Reliability | 3.0 | 4.0 | 4.0 |

*(5-point Likert scale: 1 = Strongly Disagree, 5 = Strongly Agree)*

**Key Findings:**
- :white_check_mark: Strong ratings for **Completeness** of threat overview and **Clarity** of terminology
- :warning: Tendency to over-assess risks in benign code (generating overly cautious warnings)
- :bulb: Evaluations varied by professional role — threat analysts rated highest, red team engineers requested more technical precision

---

## BibTeX

```bibtex
@inproceedings{toda2025chase,
  title     = {\{CHASE\}: \{LLM\} Agents for Dissecting Malicious \{PyPI\} Packages},
  author    = {Toda, Takaaki and Mori, Tatsuya},
  booktitle = {Proceedings of the 2nd ACM International Conference on
               AI-Powered Software (AIware '25)},
  year      = {2025},
  publisher = {ACM},
  address   = {Ottawa, Canada}
}
```

---

## Acknowledgments

A part of this work is based on the results obtained from a project, JPNP24003, commissioned by the New Energy and Industrial Technology Development Organization (NEDO).
