"""
Prepares Label Studio project with your asset classes and batches.
"""
import json
from pathlib import Path

class LabelStudioPrep:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.load_config()

    def load_config(self):
        if Path(self.config_path).exists():
            with open(self.config_path) as f:
                self.config = json.load(f)
        else:
            raise FileNotFoundError("Run 1_sample_frames.py first!")

    def load_asset_classes(self, asset_json="image_urls/joker_images.json"):
        """Load class names from your JSON files"""
        with open(asset_json) as f:
            assets = json.load(f)
        return list(assets.keys())

    def create_label_config(self, classes, output_path="label_studio_config.xml"):
        """
        Create Label Studio labeling configuration XML
        This defines what the labeling interface looks like
        """
        # Create choices XML for all classes
        choices_xml = "\n    ".join([
            f'<Choice value="{cls}"/>' for cls in classes
        ])

        config = f"""<View>
  <Image name="image" value="$image"/>
  <RectangleLabels name="label" toName="image">
    {choices_xml}
  </RectangleLabels>
</View>"""

        with open(output_path, 'w') as f:
            f.write(config)

        print(f"✅ Created Label Studio config: {output_path}")
        print(f"📋 Classes: {len(classes)}")
        return output_path

    def create_import_file(self, batch_num=None):
        """
        Create a JSON file for importing into Label Studio

        If batch_num is None, creates file for ALL batches
        If batch_num is specified, creates file for that batch only
        """
        batches = self.config["batches"]

        if batch_num is not None:
            batches = [b for b in batches if b["batch_num"] == batch_num]
            if not batches:
                print(f"❌ Batch {batch_num} not found!")
                return None

        # Create import JSON
        tasks = []
        for batch in batches:
            for file_path in batch["files"]:
                # Label Studio expects relative or absolute paths
                tasks.append({
                    "data": {
                        "image": f"/data/local-files/?d={Path(file_path).absolute()}"
                    }
                })

        output_file = f"label_studio_import_batch_{batch_num if batch_num else 'all'}.json"
        with open(output_file, 'w') as f:
            json.dump(tasks, f, indent=2)

        print(f"✅ Created import file: {output_file}")
        print(f"📸 Total images: {len(tasks)}")
        return output_file

    def print_instructions(self, config_xml, import_json):
        """Print setup instructions for Label Studio"""
        print("\n" + "="*70)
        print("🚀 LABEL STUDIO SETUP INSTRUCTIONS")
        print("="*70)
        print("\n1. Start Label Studio:")
        print("   $ label-studio start")
        print("\n2. Open browser to: http://localhost:8080")
        print("\n3. Create New Project:")
        print("   - Project Name: 'Balatro Joker Detection'")
        print("   - Click 'Object Detection with Bounding Boxes'")
        print("\n4. Import Labeling Configuration:")
        print(f"   - Go to Settings → Labeling Interface")
        print(f"   - Click 'Code' and paste contents of: {config_xml}")
        print("\n5. Configure Local Storage:")
        print("   - Go to Settings → Cloud Storage → Add Source Storage")
        print("   - Choose 'Local files'")
        print(f"   - Absolute local path: {Path('dataset/batches').absolute()}")
        print("   - Click 'Add Storage'")
        print("\n6. Import Images:")
        print("   - Go to project page")
        print("   - Click 'Import'")
        print(f"   - Upload: {import_json}")
        print("\n7. Start Annotating!")
        print("   - Click on an image")
        print("   - Draw rectangles around jokers")
        print("   - Label each rectangle")
        print("   - Click 'Submit' when done")
        print("\n💡 Tips:")
        print("   - Use keyboard shortcuts: numbers 1-9 for quick class selection")
        print("   - Press 'Ctrl+Enter' to submit")
        print("   - Take breaks every 50 images!")
        print("="*70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Prepare Label Studio project with asset classes and batches",
        epilog="""
Examples:
  python 2_prepare_for_labeling.py                                    # Prepare all batches
  python 2_prepare_for_labeling.py --batch 2                          # Prepare only batch 2
  python 2_prepare_for_labeling.py --asset-json ../image_urls/voucher_images.json  # Different asset type
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--asset-json", default="image_urls/joker_images.json",
                       help="Path to asset JSON file containing class names (default: image_urls/joker_images.json)")
    parser.add_argument("--batch", type=int, default=None,
                       help="Prepare specific batch number only (optional, default: all batches)")

    args = parser.parse_args()

    prep = LabelStudioPrep()

    # Load classes
    classes = prep.load_asset_classes(args.asset_json)

    # Create Label Studio config
    config_xml = prep.create_label_config(classes)

    # Create import file
    import_json = prep.create_import_file(args.batch)

    if import_json:
        # Print instructions
        prep.print_instructions(config_xml, import_json)
