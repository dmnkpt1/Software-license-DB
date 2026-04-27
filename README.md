# Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
cp .env.example .env
set -a
source .env
set +a
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.
