#!/usr/bin/env python3

def sort_vocabulary_file(input_file, output_file):
    # Read all lines from the input file
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    # Parse each line to extract the vocabulary word and full entry
    entries = []
    for line in lines:
        line = line.strip()
        if line:
            if len(line) > 1:
                word_part = line.split(' (')[0]
                entries.append((word_part.lower(), line))  # Use lowercase for sorting, keep original line
    
    # Sort by the vocabulary word (case-insensitive)
    entries.sort(key=lambda x: x[0])
    
    # Write sorted entries to output file with new numbering
    with open(output_file, 'w') as f:
        for _, original_line in entries:
            f.write(f"{original_line}\n")

if __name__ == "__main__":
    sort_vocabulary_file('./../seed-data/words-list.txt', './../seed-data/words-list-sorted.txt')
    print("Vocabulary file sorted alphabetically and saved to words-list-sorted.txt")
