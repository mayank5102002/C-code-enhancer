async function submitCode() {
    const btn = document.getElementById('runBtn');
    const code = document.getElementById('code').value;
    const outputCard = document.getElementById('outputCard');
    const statusBadge = document.getElementById('statusBadge');
    const iterCount = document.getElementById('iterCount');
    const optimizedCode = document.getElementById('optimizedCode');

    // Get checked targets
    const targetCheckboxes = document.querySelectorAll('input[name="target"]:checked');
    const targets = Array.from(targetCheckboxes).map(el => el.value);

    // Update UI to initializing state
    btn.disabled = true;
    btn.innerText = "Running Graph...";
    outputCard.style.display = 'block';
    statusBadge.innerText = "INITIALIZING PIPELINE...";
    statusBadge.style.backgroundColor = "#0369a1";

    iterCount.innerText = "0";
    optimizedCode.value = "";

    try {
        const response = await fetch('/profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                cpp_code: code,
                optimization_targets: targets
            })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            let newlineIndex;
            while ((newlineIndex = buffer.indexOf('\n')) >= 0) {
                const line = buffer.slice(0, newlineIndex).trim();
                buffer = buffer.slice(newlineIndex + 1);

                if (line) {
                    try {
                        const data = JSON.parse(line);
                        const state = data.state;
                        const node = data.node;

                        if (node === 'harness_generator') {
                            statusBadge.innerText = "SYNTHESIZING BENCHMARK HARNESS...";
                        } else if (node === 'profiler') {
                            statusBadge.innerText = `PROFILING EXECUTION (Run ${state.optimization_iterations || 0})...`;
                        } else if (node === 'optimizer') {
                            statusBadge.innerText = "AI OPTIMIZING C++ LOGIC...";
                        }

                        if (state.optimization_iterations !== undefined) {
                            iterCount.innerText = state.optimization_iterations;
                        }
                        if (state.cpp_code !== undefined) {
                            optimizedCode.value = state.cpp_code;
                        }

                    } catch (parseError) {
                        console.error("PARSE ERROR DETECTED!");
                        console.error("Error Trace:", parseError);
                        console.error("The string that broke it was:", line);
                    }
                }
            }
        }

        statusBadge.innerText = "PIPELINE COMPLETE";
        statusBadge.style.backgroundColor = "#16a34a";

    } catch (err) {
        statusBadge.innerText = "PIPELINE ERROR";
        statusBadge.style.backgroundColor = "#dc2626";
        console.error("[FATAL ERROR]", err);
    } finally {
        btn.disabled = false;
        btn.innerText = "Run Profiler Pipeline";
    }
}