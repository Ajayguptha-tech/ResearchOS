cd "C:\Users\LENOVO\Desktop\master\ResearchOS\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 2>&1 | Out-File -Encoding utf8 ..\.freebuff\backend.log
