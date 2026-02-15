# Contact sync tool

Sync and clean up contacts when switching between Google/Android and iOS/iPhone. Automatically merges duplicates and optionally filters out unwanted contacts.

## Quick start

```bash
# Install dependencies
uv venv && uv sync

# Merge all contacts and remove duplicates
uv run scripts/create_master_contacts.py --google data/input/google_contacts.vcf --ios data/input/icloud_contacts.vcf

# Optional: Filter out unwanted contacts
cp config/filter_config.example.yaml data/filter_config.yaml
# Edit data/filter_config.yaml with your exclusion rules
uv run scripts/filter_contacts.py --input data/output/master_contacts.vcf

# Import the result to your iPhone via iCloud.com
```

## Project structure

```
contacts/
├── scripts/                    # Main scripts
│   ├── create_master_contacts.py
│   ├── filter_contacts.py
│   └── merge_contacts.py
├── lib/                        # Core libraries
│   ├── vcard_parser.py
│   └── detect_duplicates.py
├── config/                     # Configuration templates
│   └── filter_config.example.yaml
├── data/                       # Your data (git-ignored)
│   ├── input/                  # Contact exports
│   └── output/                 # Generated files
├── pyproject.toml
└── README.md
```

## What it does

- Merges contacts from Google Contacts and iCloud exports (vCard format)
- Automatically deduplicates based on phone numbers, emails and name matching
- Optionally filters out unwanted contacts (old employers, etc.)
- Generates clean vCard files ready for iPhone import

## Installation

Install [uv](https://github.com/astral-sh/uv) and set up the project:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
uv sync
```

All dependencies are defined in `pyproject.toml`.

## Usage

### Step 1: Export your contacts

**From Google Contacts:**
1. Go to [contacts.google.com](https://contacts.google.com)
2. Click "Export" → Select "vCard format (for iOS Contacts)" → Export
3. Save to `data/input/google_contacts.vcf`

**From iCloud (optional):**
1. Go to [icloud.com](https://icloud.com) → Contacts
2. Select All → Click gear icon → Export vCard
3. Save to `data/input/icloud_contacts.vcf`

### Step 2: Merge and deduplicate

```bash
uv run scripts/create_master_contacts.py --google data/input/google_contacts.vcf --ios data/input/icloud_contacts.vcf
```

This creates `data/output/master_contacts.vcf` with all duplicates merged.

### Step 3: Filter (optional)

To exclude old contacts from specific organizations or email domains:

```bash
# Copy and edit the filter config
cp config/filter_config.example.yaml data/filter_config.yaml
# Edit data/filter_config.yaml with your exclusion rules

# Apply filters
uv run scripts/filter_contacts.py --input data/output/master_contacts.vcf
```

This creates `data/output/filtered_contacts.vcf`.

### Step 4: Import to iPhone

**Option A: Mac Contacts.app (recommended for 1,000+ contacts)**

Mac's Contacts app has no import limit and syncs automatically via iCloud:

1. Enable iCloud Contacts sync: System Settings → Apple ID → iCloud → Contacts (on)
2. Open Contacts.app
3. File → Import → Select your file (`filtered_contacts.vcf` or `master_contacts.vcf`)
4. Wait for import to complete
5. Contacts sync to iPhone automatically (check after 1-2 minutes)

**Option B: iCloud.com web interface (for lists under 1,000 contacts)**

Note: iCloud.com has an ~1,000 contact import limit. Use Option A for larger files.

1. Go to [icloud.com](https://icloud.com) → Contacts
2. Click gear icon → Import vCard
3. Select your file (`filtered_contacts.vcf` or `master_contacts.vcf`)
4. Wait for sync (check your iPhone after a few minutes)

## Files created

- `data/output/master_contacts.vcf` - Merged and deduplicated contacts
- `data/output/filtered_contacts.vcf` - Master contacts with filters applied (if using filters)
- `data/output/merge_log.txt` - Log showing which contacts were merged
- `data/output/exclusion_report.txt` - Report of filtered contacts (if using filters)
