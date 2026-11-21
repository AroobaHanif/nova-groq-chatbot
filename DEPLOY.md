# NOVA deployment

## GitHub

If GitHub CLI is available and authenticated, publish as `nova-groq-chatbot`. Otherwise create a public repository named `nova-groq-chatbot` at https://github.com/new, then run:

```powershell
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/nova-groq-chatbot.git
git push -u origin main
```

Never commit `.streamlit/secrets.toml`. Before pushing verify `git ls-files`, `git grep -n "gsk_"`, and `git check-ignore .streamlit/secrets.toml`.

## Streamlit Community Cloud

1. Open https://share.streamlit.io and sign in with GitHub.
2. Click **Create app**, choose repository `nova-groq-chatbot`, branch `main`, and main file `chatbot.py`.
3. In Advanced settings choose Python 3.11 or 3.12 and paste `GROQ_API_KEY = "my key"` in Secrets. Replace `my key` with the real key there and nowhere else.
4. Click **Deploy**, wait for the build, and copy the public URL.

## Troubleshooting

- Dependency errors: choose Python 3.11/3.12 and redeploy; locally run `pip install -r requirements.txt`.
- `ModuleNotFoundError`: confirm the main file is `chatbot.py` and the build used the latest `main` commit.
- Sleeping after inactivity is expected on free hosting; opening the URL wakes the app.
- Reboot from the app menu with **Reboot app**, or redeploy the latest commit.
- If a key was exposed, revoke/regenerate it at https://console.groq.com and replace the Cloud secret immediately.
