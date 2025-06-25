# Sylvelius
Installazione:
1. Clonare l'intero progetto in una cartella
2. Installare python ad una versione uguale o superiore alla 3.10 (progetto testato fino alla versione 3.12 compresa)
3. Installare pipenv alla versione 2025.0.3 o superiori
4. Eseguire da riga di comando nella stessa cartella contenente Pipfile e Pipfile.lock "pipenv install" dopo aver impostato su Pipfile la versione di python scelta fra le disponibili
5. Eseguire "pipenv shell"
6. Successivamente se su Windows, digitare "cd .\progetto_tw\", altrimenti su Linux/GNU "cd ./progetto_tw/"
7. Andare a ./progetto_tw/urls.py e commentare sia delete_db() che init_db()
8. Digitare se su Windows "python.exe .\manage.py migrate" o se su Linux/GNU "python3 ./manage.py migrate"
9. Ritornare a ./progetto_tw/urls.py e decommentare sia #delete_db() che #init_db()
10. Infine digitare, se su Windows "python.exe .\manage.py runserver" o se su Linux/GNU "python3 ./manage.py runserver"
11. Sul browser, cercare nella barra degli indirizzi localhost:8000

Note:
- PayPal NON funzionerà, mancano le credenziali segrete di .env

Programmi supportati:
- Python 3.10, 3.11, 3.12
- Django 5.2.1
- pipenv 2025.0.3
- channels 4.2.2 (gestione web sockets)
- daphne 4.2.0 (server ASGI)
- pillow 11.2.1 (gestione immagini)
- python-dotenv 1.1.0 (gestione files .env)

Librerie usate:
- django.*
- asgiref.* (gestione ASGI)
- channels.* (gestione web sockets)
- PIL.* (gestione immagini Pillow)
- json (gestione files json)
- uuid (generatore codici univoci)
- re (regular expressions)
- requests (usato in parte per comunicare con paypal)
- Decimal (gestione numeri decimali)

Librerie per il testing:
- tempfile (generazione file temporanei)
- shutil (rimozione ad albero file temporanei)
- unittest.*

Scripts lato template:
- bootstrap 4.6.1 (abbellimento con css e js)
- bootstrap-icons 1.10.5 (icone)
- jquery 3.6.0 (animazioni)
- paypal (pagamenti)
