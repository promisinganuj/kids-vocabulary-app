# Backup Words as JSON

This utility script allows you to export vocabulary words from the database to JSON files with timestamped filenames.

## Usage

```bash
# Export base vocabulary (system-wide words)
python app/utils/backup-words-as-json.py

# Export all user vocabulary words
python app/utils/backup-words-as-json.py --all-users

# Export words for a specific user
python app/utils/backup-words-as-json.py --user-id 1

# Export only unique words (removes duplicates)
python app/utils/backup-words-as-json.py --unique

# Use custom output file path
python app/utils/backup-words-as-json.py --output custom-backup.json

# Show database statistics only
python app/utils/backup-words-as-json.py --stats-only
```

## Output Format

The exported JSON file contains:

```json
{
  "export_info": {
    "timestamp": "2025-08-20T21:33:56.980981",
    "type": "unique",
    "total_words": 244,
    "database_path": "vocabulary_multiuser.db"
  },
  "words": [
    {
      "word": "Example",
      "type": "Noun",
      "definition": "A thing characteristic of its kind",
      "example": "This is an example sentence.",
      "source": "base",
      "also_in_user_vocab": true
    }
  ]
}
```

## File Naming

By default, files are saved to `seed-data/words-list-YYYYMMDDHHMMSS.json` where:
- YYYY = Year (4 digits)
- MM = Month (2 digits)
- DD = Day (2 digits)
- HH = Hour (24-hour format, 2 digits)
- MM = Minute (2 digits)
- SS = Second (2 digits)

## Export Types

- **base**: Base vocabulary words (system-wide collection)
- **all-users**: All user vocabulary words from all users (may include duplicates)
- **user-X**: Words for specific user ID X
- **unique**: Unique words from both base and user vocabularies (duplicates removed)

## Unique Words Export

The `--unique` option exports only unique words based on case-insensitive word text comparison. It includes:
- All words from base vocabulary
- Additional words from user vocabularies that don't already exist in base vocabulary
- Special fields:
  - `source`: Indicates if word comes from "base" or "user" vocabulary
  - `also_in_user_vocab`: Added to base words that also appear in user vocabularies
  - `user_id`: Included for words that originate from user vocabulary

## Database Statistics

The script shows statistics including:
- Base vocabulary words count
- User vocabulary words count (may include duplicates)
- Number of users with words
- Total unique words across all tables

## Database Tables

- `base_vocabulary`: System-wide words available to all users
- `vocabulary`: User-specific words with learning progress data (may contain duplicates across users)
