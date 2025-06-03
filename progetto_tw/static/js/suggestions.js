function setupSuggestions({
    inputId,
    suggestionsId,
    wsUrl,
    onSelect,
    isMulti = false,
    containerId = null,
    hiddenInputId = null
}) {
    const MAX_WS_QUERIES = window.COSTANTI.MAX_WS_QUERIES;
    let ws = null;
    let timeout = null;
    const input = document.getElementById(inputId);
    const suggestions = document.getElementById(suggestionsId);
    const container = containerId ? document.getElementById(containerId) : null;
    const hiddenInput = hiddenInputId ? document.getElementById(hiddenInputId) : null;
    let items = [];

    function connectWS() {
        if (ws && ws.readyState === WebSocket.OPEN) return;
        const loc = window.location;
        let wsStart = loc.protocol === "https:" ? "wss://" : "ws://";
        ws = new WebSocket(wsStart + loc.host + wsUrl);
        ws.onmessage = function(e) {
            const data = JSON.parse(e.data);
            if (data.suggestions && input.value.length > 0) {
                suggestions.innerHTML = '';
                const limited = data.suggestions.slice(0, MAX_WS_QUERIES);
                limited.forEach(function(item) {
                    const el = document.createElement('a');
                    el.className = 'list-group-item list-group-item-action';
                    el.textContent = item;
                    el.href = "#";
                    el.onclick = function(ev) {
                        ev.preventDefault();
                        if (isMulti) {
                            if (!items.includes(item)) {
                                items.push(item);
                                renderItems();
                            }
                            input.value = '';
                        } else {
                            input.value = item;
                        }
                        suggestions.style.display = 'none';
                        onSelect && onSelect(item);
                    };
                    suggestions.appendChild(el);
                });
                suggestions.style.display = 'block';
            } else {
                suggestions.style.display = 'none';
            }
        };
        ws.onclose = function() { ws = null; };
    }

    function renderItems() {
        if (!container) return;
        container.innerHTML = '';
        items.forEach(function(tag, idx) {
            const tagEl = document.createElement('span');
            tagEl.className = 'badge badge-pill badge-primary mr-1 mb-1';
            tagEl.style.cursor = 'pointer';
            tagEl.textContent = tag + ' ×';
            tagEl.onclick = function() {
                items.splice(idx, 1);
                renderItems();
            };
            container.appendChild(tagEl);
        });
        if (hiddenInput) hiddenInput.value = items.join(',');
    }

    input.addEventListener('input', function() {
        if (timeout) clearTimeout(timeout);
        if (input.value.trim().length === 0) {
            suggestions.style.display = 'none';
            return;
        }
        timeout = setTimeout(function() {
            connectWS();
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ query: input.value }));
            } else if (ws) {
                ws.onopen = function() {
                    ws.send(JSON.stringify({ query: input.value }));
                };
            }
        }, 200);
    });

    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && isMulti && input.value.trim()) {
            const val = input.value.trim();
            if (!items.includes(val)) {
                items.push(val);
                renderItems();
            }
            input.value = '';
            suggestions.style.display = 'none';
            e.preventDefault();
        }
    });

    document.addEventListener('click', function(e) {
        if (!suggestions.contains(e.target) && e.target !== input) {
            suggestions.style.display = 'none';
        }
    });
}
