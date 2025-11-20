from transformers import AutoImageProcessor, AutoModel
from PIL import Image
import torch

processor = AutoImageProcessor.from_pretrained("facebook/dinov2-small")
model = AutoModel.from_pretrained("facebook/dinov2-small")


# Load an image (replace 'path_to_image.jpg' with your image path)
image = Image.open("path_to_image.jpg")

# Preprocess the image
inputs = processor(images=image, return_tensors="pt")

# Perform inference
with torch.no_grad():
    outputs = model(**inputs)

# Example: Print the outputs (you may need to interpret them based on the model)
print(outputs)
