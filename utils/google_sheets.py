from oauth2client.service_account import ServiceAccountCredentials
import gspread
import datetime

def update_sheet(df, config):
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(config["creds_path"], scope)
    client = gspread.authorize(creds)
    
    # Open the spreadsheet by URL and then select the sheet dynamically using the sheet name from config
    spreadsheet = client.open_by_url(config["google_sheets_url"])
    sheet = spreadsheet.worksheet(config["sheet_name"])
    
    sheet.clear()
    today = datetime.datetime.now().strftime("%-m/%-d/%Y %-I:%M %p")
    service_account_email = creds.service_account_email
    
    sheet.update([[f"Last updated {today} by {service_account_email}"]], "A1")
    data_to_write = [df.columns.tolist()] + df.values.tolist()
    sheet.update(data_to_write, "A2")
