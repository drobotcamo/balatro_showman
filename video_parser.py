import cv2
from pathlib import Path
import os

def extract_frames_from_video(video_path, output_dir, frame_interval=30):
    """
    Extract frames from a video file.

    Args:
        video_path: Path to your gameplay video
        output_dir: Where to save the screenshots
        frame_interval: Extract 1 frame every N frames (30 = 1 per second at 30fps)
    """
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Open the video
    video = cv2.VideoCapture(str(video_path))

    # Get video properties
    fps = video.get(cv2.CAP_PROP_FPS)  # Frames per second
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))  # Total frames in video
    duration = total_frames / fps  # Video duration in seconds

    print(f"Video Info:")
    print(f"  FPS: {fps}")
    print(f"  Total Frames: {total_frames}")
    print(f"  Duration: {duration:.2f} seconds")
    print(f"  Will extract ~{total_frames // frame_interval} frames\n")

    frame_count = 0
    saved_count = 0

    while True:
        # Read next frame
        success, frame = video.read()

        if not success:
            break  # End of video

        # Save frame at intervals
        if frame_count % frame_interval == 0:
            filename = output_dir / f"{Path(video_path).stem}_{saved_count:06d}.png"
            cv2.imwrite(str(filename), frame)
            saved_count += 1

            if saved_count % 100 == 0:
                print(f"Extracted {saved_count} frames...")

        frame_count += 1

    video.release()
    print(f"\n✓ Done! Extracted {saved_count} frames to {output_dir}")

# Specify the directory path
directory = "gameplay_footage"

# Iterate through files in the directory
for filename in os.listdir(directory):
    file_path = os.path.join(directory, filename)
    if os.path.isfile(file_path):  # Check if it's a file
        extract_frames_from_video(
            video_path=file_path,
            output_dir="gameplay_screenshots",
            frame_interval=20  # Extract 1 frame per second (adjust based on your needs)
        )
        print(f"Processed: {file_path}")
