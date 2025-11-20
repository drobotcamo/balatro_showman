import cv2
import torch
import numpy as np
from pathlib import Path
from PIL import Image
import json
from transformers import AutoImageProcessor, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt

class ImprovedCardLabeler:
    """
    Fixed version that handles gameplay screenshots better.
    """

    def __init__(self, reference_images_dir='images'):
        print("Loading DINOv2 model...")
        self.processor = AutoImageProcessor.from_pretrained("facebook/dinov2-small")
        self.model = AutoModel.from_pretrained("facebook/dinov2-small")
        self.model.eval()

        print("Loading reference images...")
        self.reference_db = self._build_reference_database(reference_images_dir)
        print(f"Loaded {len(self.reference_db)} reference cards\n")

    def _build_reference_database(self, reference_dir):
        """Build reference database with augmentations."""
        reference_dir = Path(reference_dir)
        database = []

        for category_dir in reference_dir.iterdir():
            if not category_dir.is_dir():
                continue
            if not category_dir.name in ['joker_images', 'planet_images']:
                continue

            category = category_dir.name
            print(f"  Processing {category}...")

            for img_path in category_dir.glob('*.png'):
                img = Image.open(img_path).convert('RGB')

                # Store multiple versions of each reference
                # Original
                embedding_original = self._get_embedding(img)

                # With simulated background (more like gameplay)
                img_with_bg = self._simulate_gameplay_appearance(img)
                embedding_with_bg = self._get_embedding(img_with_bg)

                database.append({
                    'category': category,
                    'name': img_path.stem.replace('_', ' '),
                    'path': str(img_path),
                    'embedding': embedding_original,
                    'embedding_augmented': embedding_with_bg,
                    'width': img.width,
                    'height': img.height
                })

        return database

    def _simulate_gameplay_appearance(self, pil_image):
        """
        Make reference images look more like they do in-game.
        Adds slight blur, brightness variation, etc.
        """
        img = np.array(pil_image)

        # Add slight blur (simulates non-perfect screenshots)
        img = cv2.GaussianBlur(img, (3, 3), 0.5)

        # Adjust brightness slightly
        img = cv2.convertScaleAbs(img, alpha=0.95, beta=5)

        return Image.fromarray(img)

    def _get_embedding(self, pil_image):
        """Extract embedding from PIL Image."""
        inputs = self.processor(images=pil_image, return_tensors="pt")

        with torch.no_grad():
            outputs = self.model(**inputs)

        embedding = outputs.last_hidden_state[:, 0, :].squeeze()
        return embedding.numpy()

    def detect_card_regions(self, screenshot_path):
        """
        Improved detection that filters out UI elements.
        """
        img = cv2.imread(str(screenshot_path))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Edge detection
        edges = cv2.Canny(gray, 30, 100)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        card_regions = []
        img_height, img_width = img.shape[:2]

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = h / w if w > 0 else 0
            area = w * h

            # Calculate contour properties
            perimeter = cv2.arcLength(contour, True)
            if perimeter == 0:
                continue

            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

            # Solidity = how "filled" the shape is
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            solidity = area / hull_area if hull_area > 0 else 0

            # STRICTER FILTERS - Cards should be:
            # 1. Portrait orientation (taller than wide)
            # 2. Reasonable size (not tiny UI elements)
            # 3. Rectangular (approximately 4 corners)
            # 4. Solid shapes (not just outlines)
            # 5. Not too close to screen edges (usually UI)

            margin = 50  # Pixels from edge
            too_close_to_edge = (x < margin or y < margin or
                                x + w > img_width - margin or
                                y + h > img_height - margin)

            if (1.2 < aspect_ratio < 1.8 and      # Portrait cards
                area > 3000 and                    # Minimum size (increased)
                area < 40000 and                   # Maximum size
                w > 50 and h > 60 and              # Absolute minimum dimensions
                solidity > 0.85 and                # Very solid shape
                not too_close_to_edge):            # Not edge UI

                card_regions.append({
                    'x': x, 'y': y,
                    'width': w, 'height': h,
                    'aspect_ratio': aspect_ratio,
                    'solidity': solidity
                })

        # Sort by size (largest first) - cards are usually prominent
        card_regions.sort(key=lambda r: r['width'] * r['height'], reverse=True)

        return img, card_regions

    def identify_card(self, card_image, top_k=3):
        """
        Identify card using both original and augmented embeddings.
        """
        query_embedding = self._get_embedding(card_image)

        similarities = []
        for ref in self.reference_db:
            # Compare to both versions and take the max
            sim_original = cosine_similarity(
                query_embedding.reshape(1, -1),
                ref['embedding'].reshape(1, -1)
            )[0][0]

            sim_augmented = cosine_similarity(
                query_embedding.reshape(1, -1),
                ref['embedding_augmented'].reshape(1, -1)
            )[0][0]

            # Use the better match
            sim = max(sim_original, sim_augmented)

            similarities.append({
                'category': ref['category'],
                'name': ref['name'],
                'similarity': float(sim),
                'path': ref['path']
            })

        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:top_k]

    def process_screenshot(self, screenshot_path, similarity_threshold=0.70):
        """
        Process with lowered threshold since gameplay images are harder.
        """
        print(f"\nProcessing: {screenshot_path}")

        img, regions = self.detect_card_regions(screenshot_path)
        print(f"  Found {len(regions)} potential card regions")

        detected_cards = []
        for i, region in enumerate(regions):
            x, y, w, h = region['x'], region['y'], region['width'], region['height']
            card_crop = img[y:y+h, x:x+w]
            card_pil = Image.fromarray(cv2.cvtColor(card_crop, cv2.COLOR_BGR2RGB))

            matches = self.identify_card(card_pil, top_k=3)
            best_match = matches[0]

            if best_match['similarity'] >= similarity_threshold:
                detected_cards.append({
                    'bbox': region,
                    'category': best_match['category'],
                    'name': best_match['name'],
                    'confidence': best_match['similarity'],
                    'top_3_matches': matches  # Keep alternatives
                })
                print(f"    ✓ Region {i+1}: {best_match['name']} "
                      f"({best_match['category']}) - {best_match['similarity']:.1%}")
                print(f"      Alternatives: {matches[1]['name']} ({matches[1]['similarity']:.1%}), "
                      f"{matches[2]['name']} ({matches[2]['similarity']:.1%})")
            else:
                print(f"    ✗ Region {i+1}: Below threshold "
                      f"(best: {best_match['name']} at {best_match['similarity']:.1%})")

        return detected_cards, img

    def visualize_detections(self, screenshot_path, detected_cards, img):
        """Enhanced visualization with detailed comparison."""
        img_vis = img.copy()

        for card in detected_cards:
            x, y, w, h = (card['bbox']['x'], card['bbox']['y'],
                         card['bbox']['width'], card['bbox']['height'])

            # Color code by confidence
            if card['confidence'] > 0.85:
                color = (0, 255, 0)  # Green - high confidence
            elif card['confidence'] > 0.75:
                color = (0, 255, 255)  # Yellow - medium
            else:
                color = (0, 165, 255)  # Orange - low

            cv2.rectangle(img_vis, (x, y), (x+w, y+h), color, 3)

            # Multi-line label
            label1 = f"{card['name']}"
            label2 = f"{card['confidence']:.0%} ({card['category']})"

            # Background for text
            cv2.rectangle(img_vis, (x, y-45), (x+250, y), color, -1)
            cv2.putText(img_vis, label1, (x+5, y-25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            cv2.putText(img_vis, label2, (x+5, y-8),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

        # Save visualization
        output_path = Path('detections_improved') / Path(screenshot_path).name
        output_path.parent.mkdir(exist_ok=True)
        cv2.imwrite(str(output_path), img_vis)
        print(f"  Saved to: {output_path}")

        # Additional visualization for all detected regions
        plt.figure(figsize=(15, 10))
        plt.imshow(cv2.cvtColor(img_vis, cv2.COLOR_BGR2RGB))
        plt.title(f"All {len(detected_cards)} Detected Regions")
        plt.axis('off')
        plt.savefig('detections_improved/all_detections.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\nSaved full detection visualization to: detections_improved/all_detections.png")

        return img_vis

# Test it
labeler = ImprovedCardLabeler(reference_images_dir='images')
detected_cards, img = labeler.process_screenshot('gameplay_screenshots/11-19-2025-BU-01_002028.png')
labeler.visualize_detections('gameplay_screenshots/11-19-2025-BU-01_002028.png', detected_cards, img)
