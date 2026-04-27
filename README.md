# Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
export DATABASE_URL="mysql+pymysql://root:root@localhost:3306/software_license"
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.
