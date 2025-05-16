📬 Mail Mentor – Smart Gmail Semantic Search & Insights
A full-stack application that ingests your Gmail inbox, stores the data securely, and allows semantic search and email intelligence through a user-friendly Streamlit UI.

🚀 Features
🔒 OAuth2-based Gmail API integration

💾 Stores email metadata, content & attachments

📊 Interactive UI with Streamlit

🧹 Email caching for fast reloads


⚙️ Prerequisites
Before running the project, ensure you have:

Python 3.10+

A Gmail account with developer access

A Google Cloud project with Gmail API enabled

PostgreSQL installed and a database created

virtualenv (optional, but recommended)


🔧 Setup Instructions
1. Clone the Repository
   
bash
git clone https://github.com/akhil1020/Mail_Mentor.git
cd Mail_Mentor

2. Create a Virtual Environment (optional but recommended)

bash
python -m venv venv
Windows: venv\Scripts\activate

ex; (venv) PS D:\Mail-Mentor> # you gonna see after run this command.    

3. Install Required Packages

bash
pip install -r requirements.txt


4. Add Your Google API Credentials

--> open google cloud console using your gmail id
--> create project 
==> Refer google cloud documentatin and watch latest video tutorial.
==> At the end you gonna to create desctop app (xyz........json) rename this file as credentials.json and store into root directory of your project.


5 Launch the Streamlit UI
bash
streamlit run ui.py 

ex; (venv) PS D:\Mail-Mentor> streamlit run ui.py      "like this"



## 📁 Folder Structure

| File / Folder         | Description                                   |
|-----------------------|-----------------------------------------------|
| `app.py`              | FastAPI backend logic                         |
| `ui.py`               | Streamlit frontend UI                         |
| `semantic_search.py`  | Embedding and semantic search logic           |
| `email_cache.json`    | Local cache of fetched emails                 |
| `.env`                | Environment variables                         |
| `requirements.txt`    | Python package dependencies                   |
| `credentials.json`    | Gmail OAuth credentials (ignored by Git)      |
| `token.json`          | Gmail OAuth token (ignored by Git)            |



🔐 Security Notes
.env, token.json, and credentials.json are excluded via .gitignore

Be sure to revoke your Gmail token from your Google account if sharing


🧹 TODO / Coming Soon

Attachment preview
Email clustering
Daily email summary
Full-text search fallback
Docker container support

🤝 Contributing
Feel free to open issues or submit pull requests!


🧠 Built with ❤️ by Akhil




