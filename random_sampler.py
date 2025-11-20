from pathlib import Path
import random
import shutil

def sample_screenshots(source_dir, dest_dir, num_samples=100):
    """
    Randomly select a subset of screenshots to label.
    Labeling 100-200 diverse images is usually enough to start!
    """
    source_dir = Path(source_dir)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(exist_ok=True)

    # Get all screenshots
    all_images = list(source_dir.glob('*.png'))

    # Randomly sample
    samples = random.sample(all_images, min(num_samples, len(all_images)))

    # Copy to new directory
    for img in samples:
        shutil.copy(img, dest_dir / img.name)

    print(f"Copied {len(samples)} images to {dest_dir}")

# Usage
sample_screenshots(
    source_dir="gameplay_screenshots",
    dest_dir="screenshots_to_label",
    num_samples=100
)
