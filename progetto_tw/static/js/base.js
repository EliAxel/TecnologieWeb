(function() {
    const MAX_WS_QUERIES = window.COSTANTI.MAX_WS_QUERIES;
    let ws = null;
    let timeout = null;
    const input = document.getElementById('search-input');
    const suggestions = document.getElementById('search-suggestions');

    function connectWS() {
        if (ws && ws.readyState === WebSocket.OPEN) return;
        const loc = window.location;
        let wsStart = loc.protocol === "https:" ? "wss://" : "ws://";
        ws = new WebSocket(wsStart + loc.host + "/ws/search/");
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
                        input.value = item;
                        suggestions.style.display = 'none';
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

    document.addEventListener('click', function(e) {
        if (!suggestions.contains(e.target) && e.target !== input) {
            suggestions.style.display = 'none';
        }
    });
})();

document.getElementById('advanced-search-toggle').addEventListener('click', function() {
    const advBar = document.getElementById('advanced-search-bar');
    advBar.classList.toggle('slide-down');
});
document.addEventListener('DOMContentLoaded', function() {
    document.querySelector('#search-form').addEventListener('submit', function(event) {
        let queryInput = document.getElementById('search-input').value.trim();

        let categoryTags = [];
        document.querySelectorAll('#category-tags span').forEach(tag => {
            categoryTags.push(tag.textContent.trim().slice(0, -2)); // togli "×"
        });
        let inserzionista = document.getElementById('inserzionista-q').value;
        let priceMin = document.getElementById('price-min').value.trim();
        let priceMax = document.getElementById('price-max').value.trim();
        let sortOrder = document.getElementById('sort-order').value;
        let qtaMag = document.getElementById('qta-m-order').value;
        let conditions = document.getElementById('condition-type').value;
        let rating = document.getElementById('search_by_rating').value;

        let params = new URLSearchParams();
        if (queryInput) {
            params.set('q', queryInput);
        }
        if (categoryTags.length > 0) {
            params.set('categoria', categoryTags.join(','));
        }
        if (inserzionista){
            params.set('inserzionista', inserzionista);
        }
        if (priceMin) {
            params.set('prezzo_min', priceMin);
        }
        if (priceMax) {
            params.set('prezzo_max', priceMax);
        }
        if (sortOrder) {
            params.set('sort', sortOrder);
        }
        if (conditions) {
            params.set('condition', conditions);
        }
        if (rating) {
            params.set('search_by_rating', rating);
        }
        if (qtaMag){
            params.set('qta_mag', qtaMag);
        }

        let baseUrl = '/ricerca/';
        let finalUrl = baseUrl + '?' + params.toString();

        window.location.href = finalUrl;

        event.preventDefault();
    });
});
