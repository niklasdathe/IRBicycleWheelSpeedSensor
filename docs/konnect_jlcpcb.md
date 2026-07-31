# Konnect JLCPCB database connection

In **Konnect Settings**:

1. Leave `kicad-cli` at
   `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe`.
2. Set `JLCPCB DB` to
   `%APPDATA%\konnect\jlcpcb.db`.
3. Leave `IPC Socket` empty for normal automatic discovery.
4. Keep `Transport` at `both`, click **Save**, then close the dialog.

The screenshot already shows the server running. KiCad must be open with IPC
available for live editor operations.

Konnect's effective-config API was queried after setup and returns this exact
database path plus `prefer_jlc_basic: true` and the project JLCPCB rules.

The database currently contains 21 integrity-checked rows used by this
project: 9 Basic and 12 Extended. It is deliberately a project-BOM subset,
not the complete JLCPCB catalog.

Rebuild and verify:

```powershell
py -3.14 tools\refresh_jlc_links.py
py -3.14 tools\build_konnect_jlc_db.py
py -3.14 -m unittest tests.test_system.TestSystem.test_konnect_database_matches_expected_schema_and_scope -v
```

After a rebuild, restart the Konnect server if it does not notice the replaced
SQLite file. `hardware/konnect_database_manifest.json` records scope, counts,
source timestamp and SHA-256.
