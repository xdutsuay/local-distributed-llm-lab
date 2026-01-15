/*
 * LLM Lab - Compute Worker
 * Executes JavaScript tasks distributed by the Coordinator.
 * Runs in a background thread to allow UI to stay responsive (Wake Lock).
 */

self.onmessage = async function (e) {
    const { task_id, code } = e.data;
    console.log(`[Worker] Received task ${task_id}`);

    try {
        // execute arbitrary code
        // The code is expected to return a value or a Promise
        // We wrap it in an async function to handle awaits
        const executor = new Function(`return (async () => { ${code} })();`);

        const result = await executor();

        // Send success result
        self.postMessage({
            task_id: task_id,
            status: "success",
            response: result,
            error: null
        });

    } catch (err) {
        console.error(`[Worker] Task execution error:`, err);

        // Send error result
        self.postMessage({
            task_id: task_id,
            status: "error",
            response: null,
            error: err.toString()
        });
    }
};
