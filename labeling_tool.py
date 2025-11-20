import cv2
import json
from pathlib import Path

class CardLabeler:
    """
    Interactive tool to label cards in screenshots.
    Click and drag to draw boxes around cards, then type the card name.
    """

    def __init__(self, screenshots_dir, output_json="labels.json"):
        self.screenshots_dir = Path(screenshots_dir)
        self.output_json = output_json
        self.labels = {}  # Will store: {image_path: [card annotations]}

        # Load existing labels if any
        if Path(output_json).exists():
            with open(output_json, 'r') as f:
                self.labels = json.load(f)

        # Drawing state
        self.drawing = False
        self.start_point = None
        self.current_image = None
        self.current_path = None
        self.boxes = []  # Boxes for current image

    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse events for drawing bounding boxes."""

        if event == cv2.EVENT_LBUTTONDOWN:
            # Start drawing
            self.drawing = True
            self.start_point = (x, y)

        elif event == cv2.EVENT_MOUSEMOVE:
            # Show rectangle while dragging
            if self.drawing:
                img_copy = self.current_image.copy()
                cv2.rectangle(img_copy, self.start_point, (x, y), (0, 255, 0), 2)
                cv2.imshow('Label Cards', img_copy)

        elif event == cv2.EVENT_LBUTTONUP:
            # Finish drawing
            self.drawing = False
            end_point = (x, y)

            # Calculate box coordinates
            x1, y1 = self.start_point
            x2, y2 = end_point

            # Make sure x1,y1 is top-left and x2,y2 is bottom-right
            box = {
                'x': min(x1, x2),
                'y': min(y1, y2),
                'width': abs(x2 - x1),
                'height': abs(y2 - y1),
                'card_name': None  # Will be filled in by user
            }

            # Ask user for card name
            print(f"\nBox drawn: {box}")
            card_name = input("Enter card name (or 'skip' to discard this box): ")

            if card_name.lower() != 'skip':
                box['card_name'] = card_name
                self.boxes.append(box)
                print(f"Added: {card_name}")

            # Redraw image with all boxes
            self.draw_current_boxes()

    def draw_current_boxes(self):
        """Draw all labeled boxes on current image."""
        img_copy = self.current_image.copy()

        for box in self.boxes:
            x, y, w, h = box['x'], box['y'], box['width'], box['height']
            cv2.rectangle(img_copy, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # Draw card name
            if box['card_name']:
                cv2.putText(img_copy, box['card_name'], (x, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow('Label Cards', img_copy)

    def label_images(self):
        """Main labeling loop."""
        image_files = sorted(self.screenshots_dir.glob('*.png'))

        if not image_files:
            print(f"No PNG images found in {self.screenshots_dir}")
            return

        print(f"Found {len(image_files)} images to label")
        print("\nInstructions:")
        print("  - Click and drag to draw box around a card")
        print("  - Type the card name when prompted")
        print("  - Press 'n' for next image")
        print("  - Press 's' to save and continue")
        print("  - Press 'q' to save and quit")
        print("  - Press 'u' to undo last box\n")

        for img_path in image_files:
            img_str = str(img_path)

            # Skip already labeled images
            if img_str in self.labels:
                print(f"Skipping (already labeled): {img_path.name}")
                continue

            print(f"\nLabeling: {img_path.name}")

            # Load image
            self.current_image = cv2.imread(str(img_path))
            self.current_path = img_str
            self.boxes = []

            # Show image
            cv2.imshow('Label Cards', self.current_image)
            cv2.setMouseCallback('Label Cards', self.mouse_callback)

            while True:
                key = cv2.waitKey(1) & 0xFF

                if key == ord('n'):  # Next image
                    if self.boxes:
                        self.labels[img_str] = self.boxes
                    break

                elif key == ord('s'):  # Save
                    if self.boxes:
                        self.labels[img_str] = self.boxes
                    self.save_labels()
                    print("Labels saved!")

                elif key == ord('q'):  # Quit
                    if self.boxes:
                        self.labels[img_str] = self.boxes
                    self.save_labels()
                    cv2.destroyAllWindows()
                    return

                elif key == ord('u'):  # Undo
                    if self.boxes:
                        removed = self.boxes.pop()
                        print(f"Removed: {removed['card_name']}")
                        self.draw_current_boxes()

        cv2.destroyAllWindows()
        self.save_labels()
        print(f"\n✓ Labeling complete! Labeled {len(self.labels)} images")

    def save_labels(self):
        """Save labels to JSON file."""
        with open(self.output_json, 'w') as f:
            json.dump(self.labels, f, indent=2)

# Usage
labeler = CardLabeler(
    screenshots_dir="screenshots_to_label",
    output_json="card_labels.json"
)
labeler.label_images()
