# Offline compromised-password screening

At registration, password change, and successful password verification during login, UCM checks the entire normalized password against a local list. No submitted password or hash is sent to a breach API. The small checked-in text list works immediately. A larger local SHA-1 lookup database can be prepared separately.

If a password becomes known as compromised after registration, a web sign-in receives a restricted session that can only view account identity and recent security events, change the password, or sign out. Existing ordinary sessions are revoked. Android password sign-in is refused until the password is changed on the web or reset through the enrolled phone. A successful password change revokes the restricted session too. An API regression test verifies that the restricted session cannot open the sample resource or trust routes.

## Prepare the demo corpus

From the repository root, after installing the backend virtual environment and while the demo is stopped, run:

```powershell
.\scripts\Prepare-Blocklist.ps1
```

The script downloads a pinned copy of SecLists' `Pwdb_top-1000000.txt`, checks its SHA-256 checksum, and builds an ignored local lookup database. The tested copy produced **999,982 distinct hashes**; **5,406** source entries are at least 15 characters long and can be directly relevant under UCM's minimum-length rule. The generated database is not committed. Restart the backend after preparing it.

The source is [SecLists](https://github.com/danielmiessler/SecLists), [MIT-licensed](https://github.com/danielmiessler/SecLists/blob/master/LICENSE). This corpus is a useful lab demonstration, not a comprehensive list of breached 15-character passwords. Record its pinned commit and checksum when reporting results.

## Add verified breach hashes without a runtime API

The separate `download_pwned_ranges.py` operator command downloads a reproducible, evenly spaced **partial sample** from [Have I Been Pwned's published SHA-1 hash ranges](https://haveibeenpwned.com/API/v3#PwnedPasswords). It accepts no user password. UCM never calls that service during authentication. The command writes an ignored source file and a JSON manifest with retrieval time, number of prefixes, hash count, and SHA-256 checksum. From the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\download_pwned_ranges.py --prefix-count 256 --include-prefix E6A92
```

Stop the demo, retain a backup of the existing lookup database, and merge the downloaded hashes:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.core.build_blocklist ..\.demo\hibp-ranges-sha1.txt --format sha1-count --merge
```

The November 3 local run retrieved **510,495 entries from 257 of 1,048,576 possible prefixes**. After merging with the pinned common-password database, the lookup contained **1,510,213 distinct hashes** and passed SQLite integrity check. The previously accepted 16-character example `thisisalongpassword` appeared in the breach source with count 826 and was rejected by the running registration route after restart. The source and backup are retained in ignored `.demo/` files; the generated lookup database is also ignored. These figures describe this one local run. Most Pwned Passwords prefixes are not included, so a negative result does **not** establish that a password has never been breached. A full offline corpus can be imported with the same `sha1-count` format when adequate storage is available.

## Import a different offline corpus

The importer accepts either one plaintext password per line or `40-hex-character-SHA1:positive-count` lines. For example, after obtaining a local [Pwned Passwords SHA-1 download](https://haveibeenpwned.com/api/v3/#DownloadingAllPwnedPasswordsHashes):

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.core.build_blocklist C:\path\to\local-hashes.txt --format sha1-count
```

Stop the backend before replacing an existing lookup file on Windows. The importer writes to a temporary database, checks it, and replaces the old file only after a successful import. The API queries the local indexed database at request time.

SHA-1 here is only an exact lookup key for a public breach list. **Stored user passwords still use independently salted Argon2id verifiers.** An SHA-1 corpus can reveal its known password candidates to someone who obtains the database, so restrict file access like other security data. A match rejects the password; absence from the corpus does not prove a password is safe.
