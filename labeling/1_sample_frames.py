"""
Smart frame sampler that remembers what's been sampled and allows incremental batches.
"""
import json
import random
import shutil
from pathlib import Path
from datetime import datetime

class FrameSampler:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.load_config()

    def load_config(self):
        """Load or create config"""
        if Path(self.config_path).exists():
            with open(self.config_path) as f:
                self.config = json.load(f)
        else:
            self.config = {
                "screenshots_dir": "../gameplay_sources/gameplay_screenshots",
                "output_dir": "../dataset",
                "sampled_frames": [],
                "batches": [],
                "current_batch": 0
            }
            self.save_config()

    def save_config(self):
        """Save config state"""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, indent=2, fp=f)

    def get_available_frames(self):
        """Get frames that haven't been sampled yet"""
        screenshots_dir = Path(self.config["screenshots_dir"])
        all_frames = list(screenshots_dir.glob("*.png")) + list(screenshots_dir.glob("*.jpg"))

        # Filter out already sampled
        sampled_set = set(self.config["sampled_frames"])
        available = [f for f in all_frames if str(f) not in sampled_set]

        return available

    def sample_batch(self, batch_size=50, strategy="random"):
        """
        Sample a new batch of frames

        Args:
            batch_size: Number of frames to sample
            strategy: "random" or "distributed"
        """
        available = self.get_available_frames()

        if len(available) == 0:
            print("❌ No more frames available to sample!")
            return None

        # Adjust batch size if not enough frames
        batch_size = min(batch_size, len(available))

        # Sample based on strategy
        if strategy == "random":
            sampled = random.sample(available, batch_size)
        elif strategy == "distributed":
            # Take evenly spaced frames
            step = len(available) // batch_size
            sampled = [available[i * step] for i in range(batch_size)]
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Create batch directory
        self.config["current_batch"] += 1
        batch_num = self.config["current_batch"]
        batch_name = f"batch_{batch_num:03d}"
        batch_dir = Path(self.config["output_dir"]) / "batches" / batch_name
        batch_dir.mkdir(parents=True, exist_ok=True)

        # Copy frames to batch directory
        batch_files = []
        for i, frame in enumerate(sampled):
            dest_name = f"{batch_name}_{i:04d}{frame.suffix}"
            dest_path = batch_dir / dest_name
            shutil.copy(frame, dest_path)
            batch_files.append(str(dest_path))

        # Update config
        self.config["sampled_frames"].extend([str(f) for f in sampled])
        self.config["batches"].append({
            "batch_num": batch_num,
            "batch_name": batch_name,
            "batch_dir": str(batch_dir),
            "frame_count": batch_size,
            "sampled_at": datetime.now().isoformat(),
            "files": batch_files
        })
        self.save_config()

        print(f"✅ Created {batch_name} with {batch_size} frames")
        print(f"📁 Location: {batch_dir}")
        print(f"📊 Total sampled so far: {len(self.config['sampled_frames'])}")
        print(f"📊 Remaining frames: {len(self.get_available_frames())}")

        return batch_dir

    def get_stats(self):
        """Print sampling statistics"""
        total_frames = len(list(Path(self.config["screenshots_dir"]).glob("*.png")))
        sampled = len(self.config["sampled_frames"])
        remaining = len(self.get_available_frames())
        batches = len(self.config["batches"])

        print("\n📊 Sampling Statistics")
        print("=" * 50)
        print(f"Total frames available:  {total_frames}")
        print(f"Frames sampled:          {sampled} ({sampled/total_frames*100:.1f}%)")
        print(f"Frames remaining:        {remaining}")
        print(f"Batches created:         {batches}")
        print("=" * 50)

        if batches > 0:
            print("\n📦 Batch History:")
            for batch in self.config["batches"]:
                print(f"  {batch['batch_name']}: {batch['frame_count']} frames ({batch['sampled_at'][:10]})")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Sample frames from gameplay footage for annotation",
        epilog="""
Examples:
  python 1_sample_frames.py                          # Sample 50 frames (default)
  python 1_sample_frames.py --batch-size 100         # Sample 100 frames
  python 1_sample_frames.py --strategy distributed   # Evenly distributed frames
  python 1_sample_frames.py --stats                  # Show sampling statistics
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--batch-size", type=int, default=50,
                       help="Number of frames to sample (default: 50)")
    parser.add_argument("--strategy", choices=["random", "distributed"], default="random",
                       help="Sampling strategy: 'random' for random frames, 'distributed' for evenly spaced (default: random)")
    parser.add_argument("--stats", action="store_true",
                       help="Show sampling statistics without sampling new frames")

    args = parser.parse_args()

    sampler = FrameSampler()

    if args.stats:
        sampler.get_stats()
    else:
        sampler.sample_batch(batch_size=args.batch_size, strategy=args.strategy)
        sampler.get_stats()
