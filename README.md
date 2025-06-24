# Sylvelius
Installazione:
1. Clonare l'intero progetto in una cartella
2. Installare pipenv alla versione 2025.0.3 o superiori
3. Eseguire da riga di comando nella stessa cartella contenente Pipfile e Pipfile.lock "pipenv install"
4. Successivamente al completamento, se su Windows, digitare "cd .\progetto_tw\", altrimenti su Linux/GNU "cd ./progetto_tw/"
5. Andare a ./progetto_tw/progetto_tw/urls.py e commentare sia delete_db() che init_db()
6. Digitare se su Windows "python.exe .\manage.py migrate" o se su Linux/GNU "python.exe ./manage.py migrate"
7. Ritornare a ./progetto_tw/progetto_tw/urls.py e decommentare sia #delete_db() che #init_db()
8. Infine digitare, se su Windows "python.exe .\manage.py runserver" o se su Linux/GNU "python.exe ./manage.py runserver"
9. Sul browser, cercare nella barra degli indirizzi localhost:8000

Note:
- PayPal NON funzionerà, mancano le credenziali segrete in .env

Programmi supportati:
- Python 3.10, 3.11, 3.12
- Django 5.2.1
- pipenv 2025.0.3
- channels 4.2.2 (gestione web sockets)
- daphne 4.2.0 (server ASGI)
- pillow 11.2.1 (gestione immagini)
- python-dotenv 1.1.0 (gestione files .env)
Le dipendenze varie sono in requirements.txt o Pipfile

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
