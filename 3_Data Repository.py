
Akash Dagar
7:47 PM (2 minutes ago)
to me

https://docs.google.com/spreadsheets/d/e/2PACX-1vTnwAI3hP_FT9bVyrkDIKU-1xivyg-2vvsKlzSh2IaS_AMx8iJrG_PjiUGB6Xd2YRnPsGR1vkn_mPzK/pub?gid=1389029386&single=true&outp

   GOOGLE_SHEET_CSV_URL = os.environ.get(
       "GOOGLE_SHEET_CSV_URL",
       "https://docs.google.com/spreadsheets/d/<SHEET_ID>/export?format=csv&id=<SHEET_ID>&gid=<GID>",
   )

   @app.route("/data/sdoh_data.csv")
   def sdoh_data():
       r = requests.get(GOOGLE_SHEET_CSV_URL, stream=True, allow_redirects=True)
       r.raise_for_status()
       return Response(
           r.iter_content(chunk_size=8192),
           mimetype="text/csv",
           headers={"Content-Disposition": "inline; filename=sdoh_data.csv"},
       )
