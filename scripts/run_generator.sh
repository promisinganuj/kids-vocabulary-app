#!/bin/bash

# VCE Vocabulary Flashcard Generator Runner
# This script runs the Python flashcard generator and optionally opens the result

echo "🚀 Generating VCE Vocabulary Flashcards..."
echo ""

# Run the Python script and capture the output
cd "$(dirname "$0")" || exit 1
output=$(python generate_flashcards.py)
echo "$output"

# Extract the generated filename from the output
generated_file=$(echo "$output" | grep -o "selective-vocabulary-flashcard-[0-9_]*.html" | tail -1)

if [ -n "$generated_file" ]; then
    echo ""
    echo "🌐 Would you like to open the flashcards in your browser? (y/N)"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            open "$generated_file"
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux
            xdg-open "$generated_file"
        elif [[ "$OSTYPE" == "msys" ]]; then
            # Windows Git Bash
            start "$generated_file"
        else
            echo "Please open the file manually: $generated_file"
        fi
        echo "✅ Opening flashcards in your default browser..."
    else
        echo "📁 You can open the file manually: $generated_file"
    fi
else
    echo "❌ Could not detect generated file. Please check the output above."
fi
