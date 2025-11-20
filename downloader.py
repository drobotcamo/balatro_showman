import json
import os
import requests
from pathlib import Path
from urllib.parse import urlparse

def download_image(url, filepath):
    """Download an image from a URL and save it to filepath."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"Downloaded: {filepath}")
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def sanitize_filename(name):
    """Remove or replace characters that are problematic in filenames."""
    # Replace spaces and special characters
    replacements = {
        ' ': '_',
        '/': '_',
        '\\': '_',
        ':': '_',
        '*': '_',
        '?': '_',
        '"': '_',
        '<': '_',
        '>': '_',
        '|': '_',
        "'": ''
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    return name

def main():
    # Create images directory
    images_dir = Path('images')
    images_dir.mkdir(exist_ok=True)

    # Get all JSON files from image_urls directory
    image_urls_dir = Path('image_urls')
    json_files = list(image_urls_dir.glob('*.json'))

    if not json_files:
        print("No JSON files found in image_urls directory!")
        return

    print(f"Found {len(json_files)} JSON files to process\n")

    # Process each JSON file
    for json_file in json_files:
        # Use the JSON filename (without .json) as the folder name
        category_name = json_file.stem
        category_dir = images_dir / category_name
        category_dir.mkdir(exist_ok=True)

        print(f"\nProcessing category: {category_name}")
        print(f"Output directory: {category_dir}")

        # Load JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Download each image
        for name, url in data.items():
            # Get file extension from URL
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.split('/')

            # Find the image filename in the URL (usually has the extension)
            image_filename = None
            for part in path_parts:
                if '.png' in part.lower() or '.jpg' in part.lower() or '.jpeg' in part.lower():
                    ext = os.path.splitext(part)[1].split('?')[0]  # Remove query parameters
                    image_filename = sanitize_filename(name) + ext
                    break

            if not image_filename:
                # Default to .png if we can't determine extension
                image_filename = sanitize_filename(name) + '.png'

            filepath = category_dir / image_filename

            # Skip if already downloaded
            if filepath.exists():
                print(f"Skipping (already exists): {filepath}")
                continue

            download_image(url, filepath)

        print(f"Completed category: {category_name}")

    print("\n✓ All downloads complete!")

if __name__ == "__main__":
    main()
