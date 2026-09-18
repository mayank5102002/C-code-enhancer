import os
import re
import json
import time
from typing import TypedDict
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI

from src.prompts import build_system_prompt
from src.prompts import HARNESS_GENERATOR_PROMPT
from src.tools import run_cpp_profiler

load_dotenv()

# Shared language model used by the harness and optimization agents.
llm = ChatGoogleGenerativeAI(
    model=os.getenv("AI_MODEL"),
    google_api_key=os.getenv("AI_API_KEY"),
    temperature=0.2
)

# FastAPI application that exposes the profiling endpoint and static client.
app = FastAPI(title="Multi-Agent C++ Profiler API")

# Request payload accepted by the profiling endpoint.
class ProfilerRequest(BaseModel):
    cpp_code: str
    optimization_targets: list[str] = ["modern_stl"]

# State passed between the harness, profiler, and optimizer graph nodes.
class ProfilerState(TypedDict):
    cpp_code: str
    baseline_code: str
    baseline_executable: str
    baseline_latency: float
    executable_code: str
    optimization_targets: list[str]
    status: str
    optimization_iterations: int
    profiling_logs: str

# Remove optional Markdown code fences from generated C++ source.
def strip_markdown(text) -> str:
    if isinstance(text, list):
        if len(text) > 0 and isinstance(text[0], dict):
            text = text[0].get("text", "")
        else:
            text = str(text[0])
            
    cleaned = re.sub(r"^```(?:cpp|c\+\+|c)?\n", "", text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\n```$", "", cleaned.strip())
    return cleaned

# Create a benchmark harness unless the submitted code already has main().
def harness_generator_node(state: ProfilerState) -> dict:
    print("\n[AGENT NODE] ⚙️ Running: Benchmark Harness Generator...")

    code = state["cpp_code"]
    
    if re.search(r"\b(int|auto)\s+main\s*\(", code):
        return {
            "executable_code": code,
            "status": "harness_present",
            "profiling_logs": "User-supplied main() detected. Skipping harness synthesis.\n"
        }
    
    messages = [
        ("system", HARNESS_GENERATOR_PROMPT),
        ("human", f"Wrap this C++ snippet into a benchmark program:\n\n{code}")
    ]

    time.sleep(3)
    response = llm.invoke(messages)
    generated_code = strip_markdown(response.content)
    
    return {
        "executable_code": generated_code,
        "status": "harness_generated",
        "profiling_logs": "Synthesized benchmark harness with high-volume test loop.\n"
    }

# Compile and benchmark the current executable, recording its latency and result.
def execution_profiler_node(state: ProfilerState) -> dict:
    iters = state.get("optimization_iterations", 0)
    print(f"\n[AGENT NODE] ⏱️ Running: Execution Profiler (Run {iters})...")

    executable_code = state.get("executable_code", "")
    
    result = run_cpp_profiler(executable_code)
    
    current_logs = state.get("profiling_logs", "")
    new_logs = current_logs + f"\n--- Profiler Run {iters} ---\n" + result["logs"] + "\n"
    
    new_status = "profiled_success" if result["success"] else "profiled_failed"

    state_updates = {
        "status": new_status,
        "optimization_iterations": iters + 1,
        "profiling_logs": new_logs
    }

    latency_match = re.search(r"Latency:\s*([0-9.]+)\s*s", result["logs"])
    
    if latency_match:
        current_latency = float(latency_match.group(1))
        
        if iters == 0:
            state_updates["baseline_latency"] = current_latency
            state_updates["baseline_code"] = state.get("cpp_code", "")
            state_updates["baseline_executable"] = executable_code
            
        elif iters > 0:
            baseline_lat = state.get("baseline_latency", float('inf'))
            
            # Keep only optimizations that match or improve the best measured latency.
            if current_latency > baseline_lat:
                state_updates["cpp_code"] = state.get("baseline_code", "")
                state_updates["executable_code"] = state.get("baseline_executable", "")
                state_updates["profiling_logs"] += (
                    f"\n[⚠️ ROLLBACK] AI Optimization degraded performance "
                    f"({current_latency:.6f}s > baseline {baseline_lat:.6f}s). "
                    f"Reverted to original code.\n"
                )
            else:
                state_updates["baseline_latency"] = current_latency
                state_updates["baseline_code"] = state.get("cpp_code", "")
                state_updates["baseline_executable"] = executable_code
                state_updates["profiling_logs"] += (
                    f"\n[✅ ACCEPTED] AI Optimization improved latency "
                    f"({current_latency:.6f}s < {baseline_lat:.6f}s).\n"
                )
    
    return state_updates

# Ask the language model to produce a faster version of the current C++ program.
def optimizer_node(state: ProfilerState) -> dict:
    print("\n[AGENT NODE] 🧠 Running: AI Architect Optimizer...")

    targets = state.get("optimization_targets", [])
    system_prompt = build_system_prompt(targets)
    
    human_message = f"""
    Current Latency/Execution Logs:
    {state.get('profiling_logs', '')}
    
    Current C++ Code:
    {state.get('executable_code', '')}
    
    Rewrite the code to minimize latency using the strictly provided system mandates.
    Return ONLY the raw C++ code. Do not wrap it in markdown block quotes.
    """
    
    messages = [
        ("system", system_prompt),
        ("human", human_message)
    ]

    time.sleep(3)
    response = llm.invoke(messages)
    optimized_code = strip_markdown(response.content)
    
    display_code = optimized_code
    if state.get("status") != "harness_present":
        import re
        match = re.search(r"\b(?:int|auto)\s+main\s*\(", optimized_code)
        if match:
            # Hide the generated benchmark harness from the code shown to the user.
            display_code = optimized_code[:match.start()].strip()
    
    return {
        "executable_code": optimized_code,
        "cpp_code": display_code,
        "status": "optimized",
        "profiling_logs": state.get("profiling_logs", "") + "--- AI Optimization Applied ---\n"
    }

# Decide whether the workflow should optimize again or finish profiling.
def router(state: ProfilerState) -> str:
    iters = state.get("optimization_iterations", 0)
    status = state.get("status")
    
    if iters >= 4:
        return END
        
    if status == "profiled_success" and iters >= 2:
        return END
        
    return "optimizer"
 

# Build and compile the profiler workflow graph.
graph_builder = StateGraph(ProfilerState)
graph_builder.add_node("harness_generator", harness_generator_node)
graph_builder.add_node("profiler", execution_profiler_node)
graph_builder.add_node("optimizer", optimizer_node)
graph_builder.add_edge(START, "harness_generator")
graph_builder.add_edge("harness_generator", "profiler")
graph_builder.add_conditional_edges("profiler", router)
graph_builder.add_edge("optimizer", "profiler")
# Compiled graph executed for each profiling request.
agent_app = graph_builder.compile()


# Stream each graph node's state update as newline-delimited JSON.
@app.post("/profile")
async def run_profiler(request: ProfilerRequest):
    # Generate the initial state and forward workflow events to the client.
    def generate_updates():
        initial_state = {
            "cpp_code": request.cpp_code,
            "executable_code": "",
            "baseline_code": "",
            "baseline_executable": "",
            "baseline_latency": 0.0,
            "optimization_targets": request.optimization_targets,
            "status": "pending",
            "optimization_iterations": 0,
            "profiling_logs": ""
        }
        
        # Preserve incremental progress instead of waiting for the full workflow.
        for event in agent_app.stream(initial_state):
            node_name = list(event.keys())[0]
            state_update = event[node_name]
            
            payload = json.dumps({"node": node_name, "state": state_update})
            yield payload + "\n"

    return StreamingResponse(generate_updates(), media_type="application/x-ndjson")

app.mount("/", StaticFiles(directory="static", html=True), name="static")