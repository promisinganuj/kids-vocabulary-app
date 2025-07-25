#!/usr/bin/env python3
"""
Selective Vocabulary Flashcard Generator

This script reads vocabulary words from `data/words-list.txt` and generates an HTML flashcard file.

Author: Python Flash Card Generator
Date: 2025
"""

import re
import os
from datetime import datetime
from typing import List, Dict, Tuple


class VocabularyWord:
    """Class to represent a vocabulary word with its definition and example."""
    
    def __init__(self, word: str, word_type: str, definition: str, example: str):
        self.word = word.strip()
        self.word_type = word_type.strip()
        self.definition = definition.strip()
        self.example = example.strip()
    
    def __repr__(self):
        return f"VocabularyWord(word='{self.word}', type='{self.word_type}')"


class FlashcardGenerator:
    """Main class to generate HTML flashcards from vocabulary text file."""
    
    def __init__(self, input_file: str, output_dir: str = '.'):
        self.input_file = input_file
        self.output_dir = output_dir
        self.words: List[VocabularyWord] = []
    
    def parse_words_file(self) -> None:
        """Parse the vocabulary words from the text file."""
        if not os.path.exists(self.input_file):
            raise FileNotFoundError(f"Input file '{self.input_file}' not found.")
        
        with open(self.input_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Updated pattern to match both old numbered format and new unnumbered format
        # Old format: "Number. Word (Type) - Definition - Example."
        # New format: "Word (Type) - Definition - Example."
        
        # Try new format first (without numbering)
        pattern_new = r'([A-Za-z]+)\s+\(([^)]+)\)\s+-\s+([^-]+)\s+-\s+(.+)'
        matches_new = re.findall(pattern_new, content)
        
        if matches_new:
            # Use new format
            for match in matches_new:
                word, word_type, definition, example = match
                vocab_word = VocabularyWord(word, word_type, definition, example)
                self.words.append(vocab_word)
        else:
            # Fall back to old format (with numbering)
            pattern_old = r'(\d+)\.\s+([A-Za-z]+)\s+\(([^)]+)\)\s+-\s+([^-]+)\s+-\s+(.+)'
            matches_old = re.findall(pattern_old, content)
            
            for match in matches_old:
                number, word, word_type, definition, example = match
                vocab_word = VocabularyWord(word, word_type, definition, example)
                self.words.append(vocab_word)
        
        print(f"Successfully parsed {len(self.words)} vocabulary words.")
    
    def generate_html_template(self) -> str:
        """Generate the complete HTML template with all words."""
        
        # Generate word cards HTML
        word_cards_html = ""
        for word in self.words:
            word_cards_html += f"""
      <div class="word-card" onclick="flipCard(this)">
        <button class="hide-button" onclick="event.stopPropagation(); toggleHideCard(this.parentElement);" title="Hide card">×</button>
        <div class="flip-indicator">Click to flip</div>
        <div class="word-front">
          <div class="word">{word.word}</div>
        </div>
        <div class="word-back">
          <div class="word">{word.word}</div>
          <div class="definition">{word.definition}</div>
          <div class="example">{word.example}</div>
        </div>
      </div>
"""
        
        # Complete HTML template
        html_template = f"""<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>New Words Vocabulary Flashcards</title>
  <style>
    body {{
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      line-height: 1.6;
      margin: 0;
      padding: 20px;
      background-color: #f5f5f5;
    }}

    .container {{
      max-width: 1200px;
      margin: 0 auto;
      background-color: white;
      padding: 30px;
      border-radius: 10px;
      box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
    }}

    h1 {{
      text-align: center;
      color: #2c3e50;
      margin-bottom: 30px;
      font-size: 2.5em;
      border-bottom: 3px solid #3498db;
      padding-bottom: 10px;
    }}

    .instructions {{
      text-align: center;
      margin-bottom: 20px;
      padding: 15px;
      background-color: #e8f4fd;
      border-radius: 8px;
      color: #2c3e50;
      font-size: 1.1em;
    }}

    .word-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 20px;
      margin-top: 30px;
    }}

    .word-card {{
      background-color: #ffffff;
      border: 2px solid #3498db;
      border-radius: 12px;
      padding: 25px;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
      transition: all 0.3s ease;
      cursor: pointer;
      min-height: 120px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      position: relative;
    }}

    .word-card:hover {{
      transform: translateY(-3px);
      box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
      border-color: #2980b9;
    }}

    .word-card.flipped {{
      background-color: #f8f9fa;
      border-color: #27ae60;
    }}

    .word {{
      font-size: 1.5em;
      font-weight: bold;
      color: #2c3e50;
      text-align: center;
      margin-bottom: 15px;
    }}

    .word-front {{
      display: block;
    }}

    .word-back {{
      display: none;
    }}

    .word-card.flipped .word-front {{
      display: none;
    }}

    .word-card.flipped .word-back {{
      display: block;
    }}

    .word-card.hidden {{
      opacity: 0.3;
      transform: scale(0.95);
      filter: grayscale(100%);
    }}

    .definition {{
      color: #555;
      margin-bottom: 15px;
      font-style: italic;
      font-size: 1.05em;
      text-align: center;
    }}

    .example {{
      color: #666;
      font-size: 0.95em;
      background-color: #ffffff;
      padding: 12px;
      border-radius: 6px;
      border-left: 4px solid #27ae60;
      font-style: normal;
    }}

    .search-container {{
      margin-bottom: 20px;
      text-align: center;
    }}

    #searchInput {{
      width: 300px;
      padding: 12px;
      font-size: 16px;
      border: 2px solid #3498db;
      border-radius: 25px;
      outline: none;
    }}

    #searchInput:focus {{
      border-color: #2980b9;
      box-shadow: 0 0 10px rgba(52, 152, 219, 0.3);
    }}

    .stats {{
      text-align: center;
      margin-bottom: 20px;
      color: #666;
      font-size: 1.1em;
    }}

    .controls {{
      text-align: center;
      margin: 20px 0;
    }}

    .control-button {{
      background-color: #3498db;
      color: white;
      border: none;
      padding: 10px 20px;
      margin: 0 10px;
      border-radius: 25px;
      cursor: pointer;
      font-size: 16px;
      transition: background-color 0.3s ease;
    }}

    .control-button:hover {{
      background-color: #2980b9;
    }}

    .flip-indicator {{
      position: absolute;
      top: 10px;
      right: 15px;
      font-size: 0.9em;
      color: #7f8c8d;
      font-weight: normal;
    }}

    .hide-button {{
      position: absolute;
      top: 10px;
      left: 15px;
      background-color: #e74c3c;
      color: white;
      border: none;
      border-radius: 50%;
      width: 25px;
      height: 25px;
      cursor: pointer;
      font-size: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.3s ease;
    }}

    .hide-button:hover {{
      background-color: #c0392b;
      transform: scale(1.1);
    }}

    .word-card.hidden .hide-button {{
      background-color: #27ae60;
    }}

    .word-card.hidden .hide-button:hover {{
      background-color: #219a52;
    }}

    .generation-info {{
      text-align: center;
      margin-bottom: 20px;
      padding: 10px;
      background-color: #d4edda;
      border-radius: 6px;
      color: #155724;
      font-size: 0.9em;
    }}

    @media (max-width: 768px) {{
      .container {{
        padding: 15px;
      }}

      h1 {{
        font-size: 2em;
      }}

      .word-grid {{
        grid-template-columns: 1fr;
      }}

      #searchInput {{
        width: 250px;
      }}

      .control-button {{
        margin: 5px;
        padding: 8px 16px;
        font-size: 14px;
      }}
    }}
  </style>
</head>

<body>
  <div class="container">
    <h1>🃏 New Words Vocabulary Flashcards</h1>

    <div class="generation-info">
      <strong>📅 Generated on:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')} | 
      <strong>📊 Total Words:</strong> {len(self.words)}
    </div>

    <div class="instructions">
      <strong>📖 How to use:</strong> Click on any card to flip between the word and its definition/example.
      Use the buttons below to flip all cards at once or search for specific words.
      Click the <strong>×</strong> button on each card to hide it (useful for words you've mastered).
    </div>

    <div class="search-container">
      <input type="text" id="searchInput" placeholder="Search words..." onkeyup="searchWords()">
    </div>

    <div class="controls">
      <button class="control-button" onclick="showAllWords()">Show All Words</button>
      <button class="control-button" onclick="showAllDefinitions()">Show All Definitions</button>
      <button class="control-button" onclick="shuffleCards()">Shuffle Cards</button>
      <button class="control-button" onclick="showAllCards()">Show All Cards</button>
      <button class="control-button" onclick="hideAllCards()">Hide All Cards</button>
    </div>

    <div class="stats">
      <strong>Total Words: <span id="wordCount">{len(self.words)}</span></strong>
    </div>

    <div class="word-grid" id="wordGrid">{word_cards_html}
    </div>
  </div>

  <script>
    function flipCard(card) {{
      card.classList.toggle('flipped');
    }}

    function showAllWords() {{
      document.querySelectorAll('.word-card').forEach(card => card.classList.remove('flipped'));
    }}

    function showAllDefinitions() {{
      document.querySelectorAll('.word-card').forEach(card => card.classList.add('flipped'));
    }}

    function shuffleCards() {{
      const grid = document.getElementById('wordGrid');
      const cards = Array.from(grid.children);
      for (let i = cards.length - 1; i > 0; i--) {{
        const j = Math.floor(Math.random() * (i + 1));
        grid.appendChild(cards[j]);
        cards.splice(j, 1);
      }}
    }}

    function searchWords() {{
      const input = document.getElementById('searchInput').value.toLowerCase();
      let visibleCount = 0;
      document.querySelectorAll('.word-card').forEach(card => {{
        const word = card.querySelector('.word-front .word')?.textContent.toLowerCase() || '';
        const definition = card.querySelector('.definition')?.textContent.toLowerCase() || '';
        const example = card.querySelector('.example')?.textContent.toLowerCase() || '';

        if (word.includes(input) || definition.includes(input) || example.includes(input)) {{
          card.style.display = '';
          visibleCount++;
        }} else {{
          card.style.display = 'none';
        }}
      }});

      document.getElementById('wordCount').textContent = visibleCount;
    }}

    function toggleHideCard(card) {{
      card.classList.toggle('hidden');
      const button = card.querySelector('.hide-button');
      if (card.classList.contains('hidden')) {{
        button.textContent = '↺';
        button.title = 'Show card';
      }} else {{
        button.textContent = '×';
        button.title = 'Hide card';
      }}
    }}

    function hideAllCards() {{
      document.querySelectorAll('.word-card').forEach(card => {{
        card.classList.add('hidden');
        const button = card.querySelector('.hide-button');
        button.textContent = '↺';
        button.title = 'Show card';
      }});
    }}

    function showAllCards() {{
      document.querySelectorAll('.word-card').forEach(card => {{
        card.classList.remove('hidden');
        const button = card.querySelector('.hide-button');
        button.textContent = '×';
        button.title = 'Hide card';
      }});
    }}

    // Initialize word count
    document.addEventListener('DOMContentLoaded', function () {{
      const totalWords = document.getElementsByClassName('word-card').length;
      document.getElementById('wordCount').textContent = totalWords;
    }});
  </script>
</body>

</html>"""
        
        return html_template
    
    def generate_flashcard_file(self) -> str:
        """Generate the HTML flashcard file with datetime suffix."""
        
        # Create output filename with datetime suffix
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"vce_vocabulary_flashcard_{timestamp}.html"
        output_path = os.path.join(self.output_dir, output_filename)
        
        # Generate HTML content
        html_content = self.generate_html_template()
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(html_content)
        
        print(f"✅ Successfully generated flashcard file: {output_filename}")
        print(f"📁 Location: {output_path}")
        
        return output_path
    
    def run(self) -> str:
        """Main method to parse words and generate flashcard file."""
        try:
            print("🚀 Starting VCE Vocabulary Flashcard Generator...")
            print(f"📖 Reading words from: {self.input_file}")
            
            self.parse_words_file()
            output_path = self.generate_flashcard_file()
            
            print("🎉 Flashcard generation completed successfully!")
            return output_path
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            raise


def main():
    """Main function to run the flashcard generator."""
    
    # Configuration
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    
    input_file = os.path.join(parent_dir, 'seed-data', 'words-list.txt')
    output_dir = script_dir  # Output to the app directory
    
    print("=" * 60)
    print("    SELECTIVE VOCABULARY FLASHCARD GENERATOR")
    print("=" * 60)
    
    # Create generator instance and run
    generator = FlashcardGenerator(input_file, output_dir)
    output_path = generator.run()
    
    print("\n" + "=" * 60)
    print(f"🎯 Ready to use! Open the file in your browser:")
    print(f"   {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
