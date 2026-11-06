# Lucra warehouse

The warehouse finder publishes block codes, positions, bundle counts, and a
refresh timestamp. The Google Sheet stays private.

## Enable scheduled refresh

1. Enable the Google Sheets API in a Google Cloud project. Give a dedicated
   service account Viewer access to the warehouse Sheet.
2. Store the service account's JSON credential as the repository Actions secret
   `GOOGLE_SHEETS_CREDENTIALS`. The spreadsheet ID is stored separately in
   `LUCRA_WAREHOUSE_SHEET_ID`.
3. In **Settings → Pages → Build and deployment**, select **GitHub Actions**.
4. Run **Refresh warehouse** from the **Actions** tab and verify the timestamp
   on the live site.

Refresh runs hourly at :23 and can also be started manually. A failed read or
invalid Sheet entry leaves the last successful site online.
