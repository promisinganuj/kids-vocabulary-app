# Vocabulary JSON Populator

This script populates missing word details (definitions and examples) in the `words-list.json` file using Azure OpenAI.

## Features

- 🔍 **Smart Detection**: Automatically finds words with "To be added" placeholders
- 🤖 **AI-Powered**: Uses Azure OpenAI to generate high-quality definitions and examples
- 📊 **Progress Tracking**: Shows real-time progress with ETA and success rates
- 💾 **Safe Operation**: Creates automatic backups before making changes
- ⚡ **Rate Limiting**: Configurable delays to respect API limits
- 🎯 **Flexible Processing**: Process all words or specify batches

## Setup

### 1. Configure Azure OpenAI

Copy the environment configuration file:
```bash
cp app/.env.example .env
```

Edit `.env` and add your Azure OpenAI credentials:
```bash
AZURE_OPENAI_API_KEY="your_azure_openai_api_key_here"
AZURE_OPENAI_ENDPOINT="https://your-resource-name.openai.azure.com/"
AZURE_OPENAI_DEPLOYMENT="gpt-4o-mini"
AZURE_OPENAI_API_VERSION="2024-12-01-preview"
```

### 2. Install Dependencies

Make sure you have the required packages:
```bash
pip install requests python-dotenv
```

## Usage

### Quick Analysis

First, check how many words need updating:
```bash
python analyze_vocabulary.py
```

Example output:
```
📊 Vocabulary File Analysis
========================================
Total words: 770
Words needing definition: 334
Words needing example: 560
Words needing any update: 560
🤖 Estimated API calls needed: 560
⏱️  Estimated time (8s per call): 74.7 minutes
```

### Running the Populator

#### Process All Words
```bash
python populate_vocabulary.py
```

#### Process Limited Number of Words
```bash
# Process first 10 incomplete words
python populate_vocabulary.py 10

# Process 5 words starting from index 10
python populate_vocabulary.py 5 10

# Process 10 words with 5-second delays between API calls
python populate_vocabulary.py 10 0 5.0
```

#### Get Help
```bash
python populate_vocabulary.py --help
```

## Script Behavior

### What Gets Updated

The script will update any word that has:
- `"definition": "To be added"` or empty definition
- `"example": "To be added"` or empty example  
- `"type": "To be added"` or empty type

### Rate Limiting

- **Default**: 8 seconds between API calls
- **Why**: Prevents hitting Azure OpenAI rate limits
- **Customizable**: Use the third parameter to adjust

### Safety Features

1. **Automatic Backup**: Creates timestamped backup before changes
2. **Progress Saving**: Each update is saved immediately 
3. **Error Handling**: Continues processing even if individual words fail
4. **Confirmation**: Asks for confirmation before starting batch operations

## Examples

### Test Run (Recommended First)
```bash
# Test with just 3 words to make sure everything works
python populate_vocabulary.py 3
```

### Production Runs
```bash
# Process in batches to monitor progress
python populate_vocabulary.py 50    # First 50 words
python populate_vocabulary.py 50 50 # Next 50 words (starting from index 50)
python populate_vocabulary.py 50 100 # Next 50 words (starting from index 100)
```

### Resume Processing
```bash
# If script was interrupted, resume from where you left off
python populate_vocabulary.py 100 200  # Process 100 words starting from index 200
```

## Output Example

```
🚀 Starting Vocabulary JSON Populator
==================================================
📖 Loading vocabulary file: /path/to/words-list.json
✅ Loaded 770 words from vocabulary file
💾 Creating backup: /path/to/words-list.json.backup_20250822_233745
✅ Backup created successfully
🔍 Found 560 words needing updates
📝 Sample words to be updated:
   • Abate (missing: example)
   • Aberrant (missing: definition, example)
   • Abscond (missing: definition, example)

🔧 Configuration:
   • Rate limit: 8.0 seconds between requests
   • Words to process: 560
   • Estimated time: 74.7 minutes

⚠️  This will make 560 API calls to Azure OpenAI.
Continue? (y/N): y

📊 Progress: 1/560 (0.2%) | ETA: 74.6m | Success: 0 | Failed: 0

🤖 Processing: Abate (missing: example)
   ✅ Updated: example
   📝 Type: Verb
   📝 Definition: Make or become less intense or widespread
   📝 Example: The storm began to abate by morning, allowing residents to venture outside...
   ⏳ Waiting 8.0 seconds...
```

## Troubleshooting

### Configuration Issues
- Make sure `.env` file is in the project root (not in `app/` folder)
- Verify your Azure OpenAI credentials are correct
- Check that your deployment name matches exactly

### API Errors
- **Rate Limits**: Increase the delay between calls (third parameter)
- **Timeout**: Check your internet connection
- **Authentication**: Verify your API key is valid

### Backup and Recovery
- Backups are created automatically with timestamp
- To restore: `cp words-list.json.backup_TIMESTAMP words-list.json`
- Original file is preserved until script completes successfully

## Cost Estimation

Rough cost estimates for Azure OpenAI:
- **Per word**: $0.002 - $0.01 (varies by model and usage)
- **560 words**: $1.12 - $5.60
- **Monitor usage** in Azure portal for actual costs

## Tips

1. **Start Small**: Test with 3-5 words first
2. **Monitor Progress**: Check output for errors and quality
3. **Batch Processing**: Process in chunks of 50-100 words
4. **Review Results**: Manually check a few updated words for quality
5. **Keep Backups**: Don't delete backup files until you're satisfied

## Files Created

- `words-list.json` - Updated vocabulary file
- `words-list.json.backup_TIMESTAMP` - Automatic backup
- `analyze_vocabulary.py` - Analysis helper script
- `populate_vocabulary.py` - Main population script
- `openai_search.py` - OpenAI integration module
