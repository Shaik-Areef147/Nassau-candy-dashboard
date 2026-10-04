# 🍬 Nassau Candy Profitability Dashboard

Streamlit dashboard: product margin leaderboard, division performance, cost-vs-margin risk flags, Pareto analysis.
Reads `data/Nassau_Candy_Distributor.csv` automatically (you can also upload another CSV from the sidebar).

## Run locally
```
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Render (step by step)
1. Create a GitHub repo (e.g. `nassau-candy-dashboard`) and push this folder:
   ```
   git init
   git add .
   git commit -m "Nassau Candy dashboard"
   git branch -M main
   git remote add origin https://github.com/<your-username>/nassau-candy-dashboard.git
   git push -u origin main
   ```
2. Go to https://render.com and sign in with GitHub.
3. Click **New +** -> **Web Service** -> connect your repo.
4. Fill the form (or use **Blueprint** and it reads `render.yaml` automatically):
   - Runtime: **Python 3**
   - Build Command: `pip install --upgrade pip && pip install -r requirements.txt`
   - Start Command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
   - Instance type: **Free**
5. Under **Environment**, add `PYTHON_VERSION` = `3.11.9`.
6. Advanced -> Health Check Path: `/_stcore/health`.
7. Click **Create Web Service**. First build takes 3-5 minutes. Your URL looks like `https://nassau-candy-dashboard.onrender.com`.

## Troubleshooting
- **Page is slow the first time**: the free plan sleeps after inactivity; wait ~50 seconds.
- **Build fails on a package**: confirm `PYTHON_VERSION` is `3.11.9` and `requirements.txt` is unchanged.
- **Port error**: the start command must contain `--server.port $PORT --server.address 0.0.0.0`.
- **Upload says a column is missing**: the CSV needs at least `Product Name`, `Sales`, and `Gross Profit` or `Cost`.
