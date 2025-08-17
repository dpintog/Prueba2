# bot-demandas


## Ambiente virtual

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución bot

```powershell
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

## Comando de ejecución app service

```powershell
gunicorn -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 backend.main:app
```


## Ejecución indexador

```powershell
python -m indexacion.create_index
```
