# Lucra warehouse

The warehouse finder publishes block codes, positions, bundle counts, and a
refresh timestamp. The source Google Sheet is shared with anyone who has its
link. The website does not include that link or the Sheet ID.

## Enable scheduled refresh

1. Keep the Sheet accessible to anyone with its link, using Viewer access.
2. Store the Sheet ID as the repository Actions secret `LUCRA_WAREHOUSE_SHEET_ID`.
3. In **Settings → Pages → Build and deployment**, select **GitHub Actions**.
4. Run **Refresh warehouse** from the **Actions** tab and verify the timestamp
   on the live site.

Refresh runs hourly at :23 and can also be started manually. A failed read or
invalid Sheet entry leaves the last successful site online.

Downloads retry temporary DNS, connection, timeout, and server errors for up to
four attempts, waiting 2, 4, then 8 seconds. This applies to both the warehouse workbook
and product catalogue. Permanent HTTP errors and invalid warehouse entries still
stop the refresh; the previous published site stays online if recovery fails.
