# C++ Agentic Latency Profiler 🚀

A deterministic, production-grade multi-agent system that profiles, benchmarks, and automatically optimizes C++ code for ultra-low latency execution. 

Built with **FastAPI**, **LangGraph**, and **Google Gemini**, this tool acts as an autonomous C++ Systems Architect. It compiles your code on bare-metal (via Docker), measures execution time, feeds the results to an LLM, and iteratively applies hardware-level architectural shifts to minimize CPU cycles—automatically rolling back any changes that degrade performance.

---

## 🧠 What It Does

1. **Deterministic Benchmarking:** Automatically synthesizes a secure `main()` harness around your raw C++ snippets.
2. **Self-Healing Execution Loop:** LangGraph orchestrates a cyclical state machine (`Generator -> Profiler -> Optimizer -> Profiler`). If the AI writes code that fails to compile, the pipeline catches the `g++` error and forces the AI to fix it.
3. **Performance Rollback:** The profiler strictly monitors execution latency. If an AI optimization unexpectedly increases execution time, the state machine automatically rolls back to the faster baseline.
4. **Real-time NDJSON Streaming:** The backend streams LangGraph node states directly to a sleek, vanilla JS frontend, providing real-time visibility into the agent's thought process and execution rounds.

---

## 🏗️ Architecture

- **Frontend:** Vanilla HTML/JS/CSS
- **Backend:** Python & FastAPI.
- **Agent Orchestration:** LangGraph (StateGraph) managing the multi-node compilation, profiling, and LLM optimization loop.
- **LLM Engine:** Google Gemini orchestrated via LangChain.
- **Execution Environment:** Fully isolated Docker container shipping with `g++` (GNU C++ Compiler) to safely compile and execute synthesized binaries.

---

## ⚙️ Optimization Engine

The AI acts strictly on two tiers of constraints via a highly modular prompt engine:

### Category 1: Universal Mandates (Always Enforced)
- **Strict RAII:** Bare `new/delete` are forbidden. Replaced with smart pointers.
- **Noexcept Move Semantics:** Forces `noexcept` on Rule of 5 constructors to unlock fast-path STL container resizing.
- **Cache Locality:** Reorders struct members from largest to smallest to eliminate compiler padding.
- **Compile-Time Evaluation:** Shifts runtime cycles to the compiler using `constexpr`/`consteval`.

### Category 2: User Options (Selectable via UI)
- **Modern Idiomatic STL:** Upgrades raw loops to parallelized `<algorithm>` executions.
- **Cache Line Padding:** Injects `alignas(std::hardware_destructive_interference_size)` to prevent false sharing across threads.
- **Memory Pre-faulting:** Injects `MAP_POPULATE` or memory-warming loops to eliminate lazy-loading page faults.
- **Direct File I/O:** Enforces `O_DIRECT` to completely bypass the OS page cache.
- **Lock-Free Atomics:** Replaces `std::mutex` with `std::atomic<T>` and strict acquire/release memory orderings.
- **std::pmr Arenas:** Binds standard containers to polymorphic memory resources to eliminate global heap contention.
- **Thread Management:** Upgrades legacy threads to C++20 `std::jthread`.

---

## 🚀 Getting Started

### Prerequisites
- [Docker](https://www.docker.com/products/docker-desktop) installed and running.
- A Google Gemini API Key.

### 1. Environment Setup
Clone the repository and create a `.env` file in the root directory. Add your Gemini API key:
```env
AI_API_KEY=your_google_gemini_api_key_here
```

### 2. Build the Docker Image
This command pulls a lightweight Python Linux image, installs the `g++` compiler, and installs the required Python dependencies (`langgraph`, `fastapi`, `langchain-google-genai`).
```bash
docker build -t cpp-profiler-agent .
```

### 3. Run the Container
Start the container, passing in your `.env` file to ensure the API key stays out of your source code:
```bash
docker run -p 8000:8000 --env-file .env cpp-profiler-agent
```

### 4. Access the UI
Open your web browser and navigate to:
```
http://localhost:8000
```

---

## 💻 Usage Instructions

1. **Select Optimization Targets:** Toggle the specific architectural shifts you want the AI to attempt (e.g., *Lock-Free Atomics* or *Cache Line Padding*).
2. **Input C++ Code:** Paste your raw C++ structs, classes, or standalone functions. **Do not include a `main()` function**—the agent will build the benchmarking loop for you.
3. **Run Profiler:** Click the Run button. Watch the LangGraph state machine synthesize the harness, baseline the latency, pass the code to the AI architect, and re-profile the result. 
4. **Review:** The final, fastest version of the C++ code will be displayed in the UI.