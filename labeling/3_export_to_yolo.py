"""
Converts Label Studio annotations to YOLO format for training.
Splits data into train/val sets and creates dataset.yaml
"""
import json
import shutil
from pathlib import Path
from collections import defaultdict
import random

class YOLOExporter:
    def __init__(self, label_studio_export, asset_json="image_urls/joker_images.json"):
        """
        Args:
            label_studio_export: Path to exported JSON from Label Studio
            asset_json: Path to your asset JSON to get class names
        """
        self.export_path = label_studio_export
        self.load_annotations()
        self.load_classes(asset_json)

    def load_annotations(self):
        """Load Label Studio export JSON"""
        with open(self.export_path) as f:
            self.annotations = json.load(f)
        print(f"✅ Loaded {len(self.annotations)} annotated images")

    def load_classes(self, asset_json):
        """Load class names in consistent order"""
        with open(asset_json) as f:
            assets = json.load(f)
        self.classes = sorted(list(assets.keys()))  # Sort for consistency
        self.class_to_id = {cls: idx for idx, cls in enumerate(self.classes)}
        print(f"✅ Loaded {len(self.classes)} classes")

    def convert_to_yolo_format(self, annotation):
        """
        Convert Label Studio bounding box to YOLO format

        Label Studio format: x, y, width, height (percentages 0-100)
        YOLO format: x_center, y_center, width, height (normalized 0-1)
        """
        yolo_boxes = []

        for result in annotation.get("annotations", []):
            for item in result.get("result", []):
                if item.get("type") == "rectanglelabels":
                    # Get box coordinates (in percentages)
                    value = item["value"]
                    x = value["x"] / 100  # Convert to 0-1
                    y = value["y"] / 100
                    w = value["width"] / 100
                    h = value["height"] / 100

                    # Convert to center coordinates
                    x_center = x + w / 2
                    y_center = y + h / 2

                    # Get class
                    labels = value.get("rectanglelabels", [])
                    if labels:
                        class_name = labels[0]
                        class_id = self.class_to_id.get(class_name)

                        if class_id is not None:
                            yolo_boxes.append(
                                f"{class_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}"
                            )

        return yolo_boxes

    def export_dataset(self, output_dir="dataset/yolo", train_split=0.8):
        """
        Export complete YOLO dataset with train/val split

        Args:
            output_dir: Where to save the dataset
            train_split: Fraction of data for training (rest is validation)
        """
        output_path = Path(output_dir)

        # Create directory structure
        (output_path / "images" / "train").mkdir(parents=True, exist_ok=True)
        (output_path / "images" / "val").mkdir(parents=True, exist_ok=True)
        (output_path / "labels" / "train").mkdir(parents=True, exist_ok=True)
        (output_path / "labels" / "val").mkdir(parents=True, exist_ok=True)

        # Filter annotations with boxes
        valid_annotations = [
            ann for ann in self.annotations
            if ann.get("annotations") and
            any(r.get("result") for r in ann.get("annotations", []))
        ]

        if not valid_annotations:
            print("❌ No valid annotations found!")
            return

        # Shuffle and split
        random.shuffle(valid_annotations)
        split_idx = int(len(valid_annotations) * train_split)
        train_anns = valid_annotations[:split_idx]
        val_anns = valid_annotations[split_idx:]

        print(f"📊 Split: {len(train_anns)} train, {len(val_anns)} val")

        # Stats
        stats = {"train": defaultdict(int), "val": defaultdict(int)}

        # Process each split
        for split_name, annotations in [("train", train_anns), ("val", val_anns)]:
            for ann in annotations:
                # Get image path
                image_path = ann["data"].get("image", "")

                # Extract actual file path (Label Studio stores various formats)
                if "local-files/?d=" in image_path:
                    # Local file format
                    image_path = image_path.split("local-files/?d=")[-1]
                elif image_path.startswith("/data/"):
                    # Some other format
                    image_path = image_path.replace("/data/", "")

                image_file = Path(image_path)

                if not image_file.exists():
                    print(f"⚠️  Image not found: {image_file}")
                    continue

                # Convert boxes to YOLO format
                yolo_boxes = self.convert_to_yolo_format(ann)

                if not yolo_boxes:
                    continue

                # Copy image
                dest_image = output_path / "images" / split_name / image_file.name
                shutil.copy(image_file, dest_image)

                # Save labels
                label_file = output_path / "labels" / split_name / f"{image_file.stem}.txt"
                with open(label_file, 'w') as f:
                    f.write("\n".join(yolo_boxes))

                # Update stats
                stats[split_name]["images"] += 1
                stats[split_name]["boxes"] += len(yolo_boxes)

        # Create dataset.yaml
        yaml_content = f"""# Balatro Joker Detection Dataset
path: {output_path.absolute()}
train: images/train
val: images/val

# Classes
nc: {len(self.classes)}
names: {self.classes}
"""

        yaml_path = output_path / "dataset.yaml"
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        # Save class mapping
        with open(output_path / "classes.txt", 'w') as f:
            f.write("\n".join(self.classes))

        print("\n✅ Export complete!")
        print(f"📁 Dataset location: {output_path}")
        print(f"📊 Train: {stats['train']['images']} images, {stats['train']['boxes']} boxes")
        print(f"📊 Val:   {stats['val']['images']} images, {stats['val']['boxes']} boxes")
        print(f"📄 Config: {yaml_path}")
        print(f"\n🚀 Ready to train with:")
        print(f"   yolo detect train data={yaml_path} model=yolov8n.pt epochs=100")

        return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert Label Studio annotations to YOLO training format",
        epilog="""
Examples:
  python 3_export_to_yolo.py label_studio_export.json                # Standard conversion
  python 3_export_to_yolo.py export.json --train-split 0.9           # 90% train, 10% val
  python 3_export_to_yolo.py export.json --output ../my_dataset      # Custom output directory
  python 3_export_to_yolo.py export.json --asset-json ../image_urls/voucher_images.json  # Different assets
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("export_json",
                       help="Path to Label Studio export JSON file (download from Label Studio)")
    parser.add_argument("--asset-json", default="image_urls/joker_images.json",
                       help="Path to asset JSON file for class names (default: image_urls/joker_images.json)")
    parser.add_argument("--output", default="dataset/yolo",
                       help="Output directory for YOLO dataset (default: dataset/yolo)")
    parser.add_argument("--train-split", type=float, default=0.8,
                       help="Training split ratio, between 0.0 and 1.0 (default: 0.8 = 80%% train, 20%% val)")

    args = parser.parse_args()

    exporter = YOLOExporter(args.export_json, args.asset_json)
    exporter.export_dataset(args.output, args.train_split)
