document.addEventListener('DOMContentLoaded', () => {
    const immagini = document.querySelectorAll('.immagine-carosello');
    const prodottoId = immagini.length ? immagini[0].dataset.prodottoId : null;

    if (prodottoId) {
        fetch(`/api/immagini/${prodottoId}/`)
            .then(response => response.json())
            .then(data => {
                immagini.forEach((img, index) => {
                    if (data.urls[index]) {
                        img.src = data.urls[index];
                    }
                });
            })
            .catch(err => {
                console.error("Errore nel caricamento immagini:", err);
            });
    }
});