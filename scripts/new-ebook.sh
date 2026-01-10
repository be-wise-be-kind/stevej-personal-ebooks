#!/bin/bash

# Script to create a new ebook from template

if [ -z "$1" ]; then
    echo "Usage: ./scripts/new-ebook.sh <ebook-name>"
    echo "Example: ./scripts/new-ebook.sh learning-terraform"
    exit 1
fi

EBOOK_NAME=$1
EBOOK_DIR="ebooks/$EBOOK_NAME"

if [ -d "$EBOOK_DIR" ]; then
    echo "Error: Ebook '$EBOOK_NAME' already exists!"
    exit 1
fi

echo "Creating new ebook: $EBOOK_NAME"

# Copy template
cp -r ebooks/_template "$EBOOK_DIR"

# Update README with current date
CURRENT_DATE=$(date +%Y-%m-%d)
sed -i "s/\[Date\]/$CURRENT_DATE/" "$EBOOK_DIR/README.md"

echo "✓ Created ebook at $EBOOK_DIR"
echo ""
echo "Next steps:"
echo "1. Edit $EBOOK_DIR/README.md with your ebook details"
echo "2. Start writing chapters in $EBOOK_DIR/chapters/"
echo "3. Add any images or assets to $EBOOK_DIR/assets/"
