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
        // content: predefined helpers available to the dynamic code
        const search = async (query) => {
            // Simple Google Custom Search or similar mock via fetch
            // For now, we fetch a dummy JSON to prove network access works from mobile
            const response = await fetch(`https://jsonplaceholder.typicode.com/posts?q=${encodeURIComponent(query)}`);
            return await response.json();
        };

        const cacheStore = async (key, value) => {
            const cache = await caches.open('llm-lab-v1');
            await cache.put(new Request(key), new Response(JSON.stringify(value)));
            return "stored";
        };

        const cacheRetrieve = async (key) => {
            const cache = await caches.open('llm-lab-v1');
            const response = await cache.match(new Request(key));
            return response ? await response.json() : null;
        };

        // The code is expected to return a value or a Promise
        // We wrap it in an async function to handle awaits
        const executor = new Function('search', 'cacheStore', 'cacheRetrieve', `return (async () => { ${code} })();`);
        const result = await executor(search, cacheStore, cacheRetrieve);

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
