import cv2
import matplotlib.pyplot as plt
from pathlib import Path
import random
from PIL import Image
import torch
import numpy as np
import json
from transformers import AutoImageProcessor, AutoModel
from sklearn.metrics.pairwise import cosine_similarity

class AutomaticCardLabeler:
    """
    Automatically detect and identify cards in gameplay screenshots
    by comparing them to reference images.
    """

    def __init__(self, reference_images_dir='images'):
        print("Loading DINOv2 model...")
        self.processor = AutoImageProcessor.from_pretrained("facebook/dinov2-small")
        self.model = AutoModel.from_pretrained("facebook/dinov2-small")
        self.model.eval()

        # Load all reference images and their embeddings
        print("Loading reference images...")
        self.reference_db = self._build_reference_database(reference_images_dir)
        print(f"Loaded {len(self.reference_db)} reference cards\n")

    def _build_reference_database(self, reference_dir):
        """
        Create a database of all reference card images and their embeddings.

        Returns a list of dicts:
        [
            {
                'category': 'tarots',
                'name': 'The Fool',
                'path': 'images/tarots/The_Fool.png',
                'embedding': [...],
                'image': PIL.Image
            },
            ...
        ]
        """
        reference_dir = Path(reference_dir)
        database = []

        for category_dir in reference_dir.iterdir():
            if not category_dir.is_dir():
                continue

            category = category_dir.name
            print(f"  Processing {category}...")

            for img_path in category_dir.glob('*.png'):
                # Load image
                img = Image.open(img_path).convert('RGB')

                # Get embedding
                embedding = self._get_embedding(img)

                database.append({
                    'category': category,
                    'name': img_path.stem.replace('_', ' '),
                    'path': str(img_path),
                    'embedding': embedding,
                    'width': img.width,
                    'height': img.height
                })

        return database

    def _get_embedding(self, pil_image):
        """Extract DINOv2 embedding from a PIL Image."""
        inputs = self.processor(images=pil_image, return_tensors="pt")

        with torch.no_grad():
            outputs = self.model(**inputs)

        # Get [CLS] token embedding
        embedding = outputs.last_hidden_state[:, 0, :].squeeze()
        return embedding.numpy()

    def detect_card_regions(self, screenshot_path):
        """
        Find potential card regions in a screenshot.

        This uses basic computer vision to find rectangular regions
        that might be cards based on edges and contours.
        """
        img = cv2.imread(str(screenshot_path))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply edge detection
        edges = cv2.Canny(gray, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        card_regions = []
        for contour in contours:
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)

            # Filter by size and aspect ratio
            # (cards are typically portrait-oriented rectangles)
            aspect_ratio = h / w if w > 0 else 0
            area = w * h

            # Tune these thresholds based on your game
            if (0.8 < aspect_ratio < 2.0 and  # Reasonable aspect ratio
                area > 1000 and                 # Not too small
                w > 30 and h > 30):             # Minimum size

                card_regions.append({
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h
                })

        return img, card_regions

    def identify_card(self, card_image, top_k=3):
        """
        Identify what card this is by comparing to reference database.

        Args:
            card_image: PIL Image of the cropped card region
            top_k: Return top K most similar matches

        Returns:
            List of matches with similarity scores
        """
        # Get embedding of the card from screenshot
        query_embedding = self._get_embedding(card_image)

        # Compare to all reference embeddings
        similarities = []
        for ref in self.reference_db:
            # Cosine similarity: 1.0 = identical, 0.0 = completely different
            sim = cosine_similarity(
                query_embedding.reshape(1, -1),
                ref['embedding'].reshape(1, -1)
            )[0][0]

            similarities.append({
                'category': ref['category'],
                'name': ref['name'],
                'similarity': float(sim),
                'path': ref['path']
            })

        # Sort by similarity and return top K
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:top_k]

    def process_screenshot(self, screenshot_path, similarity_threshold=0.6):
        """
        Automatically detect and identify all cards in a screenshot.

        Args:
            screenshot_path: Path to gameplay screenshot
            similarity_threshold: Only accept matches above this confidence

        Returns:
            List of detected cards with their locations and identities
        """
        print(f"\nProcessing: {screenshot_path}")

        # Step 1: Find potential card regions
        img, regions = self.detect_card_regions(screenshot_path)
        print(f"  Found {len(regions)} potential card regions")

        # Step 2: Identify each region
        detected_cards = []
        for i, region in enumerate(regions):
            # Crop the region
            x, y, w, h = region['x'], region['y'], region['width'], region['height']
            card_crop = img[y:y+h, x:x+w]

            # Convert to PIL
            card_pil = Image.fromarray(cv2.cvtColor(card_crop, cv2.COLOR_BGR2RGB))

            # Identify
            matches = self.identify_card(card_pil, top_k=1)
            best_match = matches[0]

            # Only accept if confident enough
            if best_match['similarity'] >= similarity_threshold:
                detected_cards.append({
                    'bbox': region,
                    'category': best_match['category'],
                    'name': best_match['name'],
                    'confidence': best_match['similarity']
                })
                print(f"    Region {i+1}: {best_match['name']} "
                      f"({best_match['category']}) - "
                      f"confidence: {best_match['similarity']:.2%}")
            else:
                print(f"    Region {i+1}: No confident match "
                      f"(best: {best_match['similarity']:.2%})")

        return detected_cards, img

    def visualize_detections(self, screenshot_path, detected_cards, img):
        """Draw bounding boxes and labels on the image."""
        img_vis = img.copy()

        for card in detected_cards:
            x, y, w, h = (card['bbox']['x'], card['bbox']['y'],
                         card['bbox']['width'], card['bbox']['height'])

            # Draw box
            cv2.rectangle(img_vis, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # Draw label
            label = f"{card['name']} ({card['confidence']:.0%})"
            cv2.putText(img_vis, label, (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Save visualization
        output_path = Path('detections') / Path(screenshot_path).name
        output_path.parent.mkdir(exist_ok=True)
        cv2.imwrite(str(output_path), img_vis)
        print(f"  Saved visualization to: {output_path}")

        return img_vis

    def batch_process(self, screenshots_dir, output_json='auto_labels.json'):
        """Process all screenshots in a directory."""
        screenshots_dir = Path(screenshots_dir)
        all_results = {}

        count = 0
        for screenshot in screenshots_dir.glob('*.png'):
            detected_cards, img = self.process_screenshot(screenshot)

            if detected_cards:
                all_results[str(screenshot)] = detected_cards
                self.visualize_detections(screenshot, detected_cards, img)

            if count > 30:
                break

            count += 1

        # Save results
        with open(output_json, 'w') as f:
            json.dump(all_results, f, indent=2)

        print(f"\n✓ Processed {len(all_results)} screenshots")
        print(f"✓ Results saved to {output_json}")

        return all_results



def visual_validation(labeler, screenshot_path, num_crops=5):
    """
    Manually inspect what the model is seeing vs what it's matching to.
    This helps us understand WHY scores are low.
    """
    print(f"\n{'='*60}")
    print(f"VALIDATING: {screenshot_path}")
    print(f"{'='*60}\n")

    # Detect regions
    img, regions = labeler.detect_card_regions(screenshot_path)

    print(f"Found {len(regions)} potential regions")

    # Sample a few regions to inspect
    sample_regions = random.sample(regions, min(num_crops, len(regions)))

    for i, region in enumerate(sample_regions):
        x, y, w, h = region['x'], region['y'], region['width'], region['height']

        # Crop the region
        card_crop = img[y:y+h, x:x+w]
        card_pil = Image.fromarray(cv2.cvtColor(card_crop, cv2.COLOR_BGR2RGB))

        # Get top 5 matches
        matches = labeler.identify_card(card_pil, top_k=5)

        print(f"\n--- Region {i+1} ---")
        print(f"Location: ({x}, {y}), Size: {w}x{h}")
        print(f"Top 5 matches:")
        for j, match in enumerate(matches):
            print(f"  {j+1}. {match['name']:30s} ({match['category']:15s}) - {match['similarity']:.1%}")

        # Create visualization
        fig, axes = plt.subplots(1, 6, figsize=(18, 3))

        # Show the cropped region
        axes[0].imshow(card_pil)
        axes[0].set_title(f"Detected Region\n{w}x{h}px", fontsize=10)
        axes[0].axis('off')

        # Show top 5 reference matches
        for j, match in enumerate(matches):
            ref_img = Image.open(match['path'])
            axes[j+1].imshow(ref_img)
            axes[j+1].set_title(f"{match['name']}\n{match['similarity']:.1%}", fontsize=8)
            axes[j+1].axis('off')

        plt.tight_layout()

        # Save comparison
        output_dir = Path('validation_images')
        output_dir.mkdir(exist_ok=True)
        plt.savefig(output_dir / f"validation_{i+1}.png", dpi=100, bbox_inches='tight')
        plt.close()

        print(f"  Saved comparison to: validation_images/validation_{i+1}.png")

    # Show the full image with all detected regions
    img_vis = img.copy()
    for region in regions:
        x, y, w, h = region['x'], region['y'], region['width'], region['height']
        cv2.rectangle(img_vis, (x, y), (x+w, y+h), (0, 255, 0), 2)

    plt.figure(figsize=(15, 10))
    plt.imshow(cv2.cvtColor(img_vis, cv2.COLOR_BGR2RGB))
    plt.title(f"All {len(regions)} Detected Regions")
    plt.axis('off')
    plt.savefig('validation_images/all_detections.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\nSaved full detection visualization to: validation_images/all_detections.png")

# Run validation
labeler = AutomaticCardLabeler(reference_images_dir='images')
visual_validation(
    labeler,
    screenshot_path='gameplay_screenshots/11-19-2025-BU-01_000042.png',
    num_crops=5
)
