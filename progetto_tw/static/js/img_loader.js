document.addEventListener('DOMContentLoaded', () => {
    const immagini = document.querySelectorAll('.immagine-asincrona');

    immagini.forEach(img => {
        const prodottoId = img.getAttribute('data-prodotto-id');
        fetch(`/api/immagine/${prodottoId}/`)
            .then(response => response.json())
            .then(data => {
                img.src = data.url;
            })
            .catch(err => {
                console.error("Errore nel caricamento immagine:", err);
                img.src = '/static/img/default_product.png';
            });
    });
});