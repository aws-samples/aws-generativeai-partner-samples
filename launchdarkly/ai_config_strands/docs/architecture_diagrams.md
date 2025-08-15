# Multi-Agent System Architecture Diagrams

This document provides various diagrams to illustrate the AI agent relationships and system architecture.

## 🏗️ **1. High-Level System Architecture**

```mermaid
graph TB
    User[👤 User Query] --> TO[🎓 Teacher Orchestrator]
    
    TO --> MA[🧮 Math Assistant]
    TO --> CSA[🖥️ Computer Science Assistant]
    TO --> LA[🌍 Language Assistant]
    TO --> EA[📝 English Assistant]
    TO --> GA[🌐 General Assistant]
    
    subgraph "LaunchDarkly AI Config"
        LDAC[🚀 AI Config<br/>multi-agent-llm-prompt-1]
        LDAC --> |role: teacher-orchestrator| TO
        LDAC --> |role: math-assistant| MA
        LDAC --> |role: computer-science-assistant| CSA
        LDAC --> |role: language-assistant| LA
        LDAC --> |role: english-assistant| EA
        LDAC --> |role: general-assistant| GA
    end
    
    subgraph "AWS Bedrock"
        BM[🤖 Bedrock Models<br/>Claude, etc.]
        BM --> TO
        BM --> MA
        BM --> CSA
        BM --> LA
        BM --> EA
        BM --> GA
    end
    
    subgraph "Fallback System"
        FB[📁 Fallback Prompts]
        FB -.-> |backup| TO
        FB -.-> |backup| MA
        FB -.-> |backup| CSA
        FB -.-> |backup| LA
        FB -.-> |backup| EA
        FB -.-> |backup| GA
    end
```

## 🔄 **2. Agent Interaction Flow**

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant TO as 🎓 Teacher Orchestrator
    participant LD as 🚀 LaunchDarkly
    participant SA as 🎯 Specialized Agent
    participant BR as 🤖 AWS Bedrock
    participant ET as 📊 Event Tracker
    
    U->>TO: Submit Query
    TO->>LD: Load Dynamic Prompt (role-based)
    LD-->>TO: Return AI Config + Prompt
    TO->>BR: Initialize Bedrock Model
    BR-->>TO: Model Ready
    TO->>TO: Analyze Query & Select Agent
    TO->>SA: Route Query to Specialist
    SA->>LD: Load Specialist Prompt
    LD-->>SA: Return Specialist Config
    SA->>BR: Process with Specialist Model
    BR-->>SA: Generate Response
    SA->>ET: Track Event
    SA-->>TO: Return Specialist Response
    TO->>ET: Track Orchestration Event
    TO-->>U: Return Final Response
```

## 🛠️ **3. Tool Integration Architecture**

```mermaid
graph LR
    subgraph "Teacher Orchestrator Tools"
        TO[🎓 Teacher Orchestrator]
        TO --> |routes to| MA[🧮 Math Assistant]
        TO --> |routes to| CSA[🖥️ CS Assistant]
        TO --> |routes to| LA[🌍 Language Assistant]
        TO --> |routes to| EA[📝 English Assistant]
        TO --> |routes to| GA[🌐 General Assistant]
    end
    
    subgraph "Specialized Tools"
        MA --> CALC[🔢 Calculator]
        
        CSA --> PYTHON[🐍 Python REPL]
        CSA --> SHELL[💻 Shell]
        CSA --> FREAD[📖 File Read]
        CSA --> FWRITE[📝 File Write]
        CSA --> EDITOR[✏️ Editor]
        
        LA --> HTTP[🌐 HTTP Request]
        
        EA --> FREAD2[📖 File Read]
        EA --> FWRITE2[📝 File Write]
        EA --> EDITOR2[✏️ Editor]
        
        GA --> NONE[❌ No Tools<br/>Knowledge Only]
    end
```

## 🔧 **4. LaunchDarkly Integration Architecture**

```mermaid
graph TB
    subgraph "LaunchDarkly Dashboard"
        PROJ[📋 Project: mp-webinar-25]
        AICONF[🚀 AI Config: multi-agent-llm-prompt-1]
        PROJ --> AICONF
    end
    
    subgraph "Context Targeting"
        CTX[🎯 Context Builder]
        CTX --> |role: teacher-orchestrator| TOCTX[Teacher Context]
        CTX --> |role: math-assistant| MACTX[Math Context]
        CTX --> |role: computer-science-assistant| CSCTX[CS Context]
        CTX --> |role: language-assistant| LACTX[Language Context]
        CTX --> |role: english-assistant| EACTX[English Context]
        CTX --> |role: general-assistant| GACTX[General Context]
    end
    
    subgraph "AI Config Variations"
        AICONF --> |targets| TOCTX
        AICONF --> |targets| MACTX
        AICONF --> |targets| CSCTX
        AICONF --> |targets| LACTX
        AICONF --> |targets| EACTX
        AICONF --> |targets| GACTX
    end
    
    subgraph "Fallback Strategy"
        TOCTX -.-> |fallback| TFB[Teacher Fallback File]
        MACTX -.-> |fallback| MFB[Math Fallback File]
        CSCTX -.-> |fallback| CSFB[CS Fallback File]
        LACTX -.-> |fallback| LAFB[Language Fallback File]
        EACTX -.-> |fallback| EAFB[English Fallback File]
        GACTX -.-> |fallback| GAFB[General Fallback File]
    end
```

## 📊 **5. Event Tracking & Monitoring**

```mermaid
graph LR
    subgraph "Agent Events"
        TO[🎓 Teacher Orchestrator] --> |tracks| TOET[📊 TO Event Loop Tracker]
        MA[🧮 Math Assistant] --> |tracks| MAET[📊 MA Event Loop Tracker]
        CSA[🖥️ CS Assistant] --> |tracks| CSAET[📊 CSA Event Loop Tracker]
        LA[🌍 Language Assistant] --> |tracks| LAET[📊 LA Event Loop Tracker]
        EA[📝 English Assistant] --> |tracks| EAET[📊 EA Event Loop Tracker]
        GA[🌐 General Assistant] --> |tracks| GAET[📊 GA Event Loop Tracker]
    end
    
    subgraph "LaunchDarkly Platform"
        TOET --> LDANA[📈 LD AI Config]
        MAET --> LDANA
        CSAET --> LDANA
        LAET --> LDANA
        EAET --> LDANA
        GAET --> LDANA
    end
    
    subgraph "Available Metrics"
        LDANA --> METRICS[📊 Usage Metrics - token usage]
        LDANA --> PERF[⚡ Performance Data - duration, time to first token, output satisfaction]
        LDANA --> ERRORS[🚨 Error Tracking - generation error / success]
    end
```

## 🏢 **6. Code Organization Structure**

```mermaid
graph TB
    ROOT[📁 strands-multi-agent/]
    
    ROOT --> TO[🎓 teacher_orchestrator.py]
    ROOT --> ENV[⚙️ .env]
    ROOT --> REQ[📋 requirements.txt]
    
    ROOT --> UTILS[📁 utils/]
    UTILS --> LDUTIL[🔧 ld_ai_config_utils.py]
    UTILS --> LOGUTIL[📊 logging_config.py]
    UTILS --> STRUTIL[🔄 strands_utils.py]
    
    ROOT --> AGENTS[📁 sub_agents/]
    AGENTS --> MA[🧮 math_assistant.py]
    AGENTS --> CSA[🖥️ computer_science_assistant.py]
    AGENTS --> LA[🌍 language_assistant.py]
    AGENTS --> EA[📝 english_assistant.py]
    AGENTS --> GA[🌐 general_assistant.py]
    
    ROOT --> FALLBACK[📁 fallback_prompts/]
    FALLBACK --> TFB[📄 teacher_orchestrator_fallback_prompt.txt]
    FALLBACK --> MFB[📄 math_assistant_fallback_prompt.txt]
    FALLBACK --> CSFB[📄 computer_science_assistant_fallback_prompt.txt]
    FALLBACK --> LAFB[📄 language_assistant_fallback_prompt.txt]
    FALLBACK --> EAFB[📄 english_assistant_fallback_prompt.txt]
    FALLBACK --> GAFB[📄 general_assistant_fallback_prompt.txt]
    
    ROOT --> DOCS[📁 docs/]
    DOCS --> ARCH[📄 architecture_diagrams.md]
```

## 🔄 **7. Data Flow Architecture**

```mermaid
flowchart TD
    START([👤 User Input]) --> PARSE{🔍 Query Analysis}
    
    PARSE --> |Math Query| MATH[🧮 Math Assistant]
    PARSE --> |Code Query| CS[🖥️ CS Assistant]
    PARSE --> |Language Query| LANG[🌍 Language Assistant]
    PARSE --> |Writing Query| ENG[📝 English Assistant]
    PARSE --> |General Query| GEN[🌐 General Assistant]
    
    MATH --> CALC[🔢 Calculator Tool]
    CS --> CODE[💻 Code Execution Tools]
    LANG --> API[🌐 Translation APIs]
    ENG --> FILE[📁 File Operations]
    GEN --> KNOW[🧠 Knowledge Base]
    
    CALC --> RESULT[📊 Processed Result]
    CODE --> RESULT
    API --> RESULT
    FILE --> RESULT
    KNOW --> RESULT
    
    RESULT --> TRACK[📈 Event Tracking]
    TRACK --> RESPONSE([📤 User Response])
```

## 🎯 **8. Agent Specialization Matrix**

```mermaid
graph TB
    subgraph "Domain Expertise"
        MATH_DOM[🧮 Mathematics<br/>• Arithmetic<br/>• Algebra<br/>• Geometry<br/>• Statistics]
        CS_DOM[🖥️ Computer Science<br/>• Programming<br/>• Algorithms<br/>• Debugging<br/>• Architecture]
        LANG_DOM[🌍 Languages<br/>• Translation<br/>• Cultural Context<br/>• Pronunciation<br/>• Grammar]
        ENG_DOM[📝 English<br/>• Writing<br/>• Literature<br/>• Grammar<br/>• Style]
        GEN_DOM[🌐 General<br/>• Basic Facts<br/>• Simple Explanations<br/>• Non-specialized<br/>• Disclaimers]
    end
    
    subgraph "Tool Capabilities"
        MATH_TOOLS[🔢 Calculator]
        CS_TOOLS[💻 Code Execution<br/>📁 File Operations<br/>🐍 Python REPL<br/>💻 Shell Access]
        LANG_TOOLS[🌐 HTTP Requests<br/>🔗 API Access]
        ENG_TOOLS[📝 Text Editing<br/>📁 File Operations<br/>✏️ Content Creation]
        GEN_TOOLS[❌ No Specialized Tools]
    end
    
    MATH_DOM --> MATH_TOOLS
    CS_DOM --> CS_TOOLS
    LANG_DOM --> LANG_TOOLS
    ENG_DOM --> ENG_TOOLS
    GEN_DOM --> GEN_TOOLS
```

---
