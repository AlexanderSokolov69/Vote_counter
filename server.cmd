call .venv_sql_pyqt\Scripts\activate
set DATABASE_URL=mssql+pyodbc://sa:Prestige2011!@172.16.1.12,1433/voteflow?driver=ODBC+Driver+17+for+SQL+Server
python app.py
