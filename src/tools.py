# tools.py
import subprocess
import tempfile
import os
import re

def run_cpp_profiler(executable_code: str) -> dict:
    """
    Writes C++ code to disk, compiles it with g++ -O3, and executes it to measure latency.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        cpp_file_path = os.path.join(temp_dir, "benchmark.cpp")
        exe_file_path = os.path.join(temp_dir, "benchmark.out")
        
        # 1. Write the code to disk
        with open(cpp_file_path, "w") as f:
            f.write(executable_code)
            
        # 2. Compile the code
        compile_cmd = [
            "g++", "-O3", "-std=c++20", 
            cpp_file_path, "-o", exe_file_path
        ]
        
        try:
            compile_process = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            # Compilation failed
            return {
                "success": False,
                "latency": -1.0,
                "logs": f"COMPILATION ERROR:\n{e.stderr}"
            }
            
        # 3. Execute the binary
        try:
            # timeout ensures infinite loops don't hang the server
            exec_process = subprocess.run(
                [exe_file_path],
                capture_output=True,
                text=True,
                timeout=10 
            )
            
            if exec_process.returncode != 0:
                return {
                    "success": False,
                    "latency": -1.0,
                    "logs": f"RUNTIME ERROR:\n{exec_process.stderr}"
                }
                
            # 4. Parse the Latency from stdout
            output = exec_process.stdout
            match = re.search(r"Latency:\s*([0-9.]+)\s*s", output)
            
            if match:
                latency = float(match.group(1))
                return {
                    "success": True,
                    "latency": latency,
                    "logs": f"Execution successful. Raw latency: {latency:.6f} seconds."
                }
            else:
                return {
                    "success": False,
                    "latency": -1.0,
                    "logs": f"Execution succeeded, but failed to parse latency. Stdout:\n{output}"
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "latency": -1.0,
                "logs": "RUNTIME TIMEOUT: Execution exceeded 10 seconds."
            }