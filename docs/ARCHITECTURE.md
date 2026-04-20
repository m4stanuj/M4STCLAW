# M4STCLAW Architecture

## System Overview

``nUser Request
    |
    v
[Task Router] --classify--> [9 Task Chains]
    |                            |
    v                            v
[Memory MCP]              [LLM Providers]
    |                       (56 keys)
    v                            |
[ChromaDB]                      v
 3-tier                   [Response]
    |                            |
    +--------merge--------------+
                |
                v
          [User Output]
``n
## MCP Server Map

| Server | Port | Purpose |
|--------|------|---------|
| task-router | 3100 | Request classification |
| memory | 3101 | 3-tier ChromaDB storage |
| shell | 3102 | Safe command execution |
| browser | 3103 | Playwright automation |
| vision | 3104 | 5-layer screen analysis |
| research | 3105 | Multi-depth web search |
| pentest | 3106 | Nmap/Nuclei/Shodan |
| notify | 3107 | Desktop notifications |
| scrapling | 3108 | Anti-bot extraction |
| agents | 3109 | Multi-agent orchestration |
| scheduler | 3110 | Cron-style task scheduling |
| skills | 3111 | Learned skill storage |

## Data Flow

1. User sends natural language request
2. Task Router classifies intent (speed/reason/code/vision/research/write/agent/pentest)
3. Best chain selected from 9 available pipelines
4. Memory consulted for context (working -> episodic -> semantic)
5. LLM processes with provider failover (56 keys across 21 providers)
6. Response cached in semantic cache (0.92 similarity threshold)
7. Skills extracted if task was novel and successful

