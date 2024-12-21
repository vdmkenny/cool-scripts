from PIL import Image
import sys

# Check arguments
if len(sys.argv) != 4:
    print("Usage: python 1bit_dither_scaled.py input_image output_image width")
    print("Example: python 1bit_dither_scaled.py input.jpg output.png 384")
    sys.exit(1)

# Input arguments
input_path = sys.argv[1]
output_path = sys.argv[2]
target_width = int(sys.argv[3])

# Open the input image and convert to grayscale
image = Image.open(input_path).convert("L")

# Rotate 90 degrees if width > height
if image.width > image.height:
    image = image.rotate(90, expand=True)

# Calculate the new height to maintain aspect ratio
aspect_ratio = image.height / image.width
new_height = int(target_width * aspect_ratio)

# Resize the image
image_resized = image.resize((target_width, new_height), Image.Resampling.LANCZOS)

# Apply 1-bit Floyd-Steinberg dithering
bw_image = image_resized.convert("1", dither=Image.Dither.FLOYDSTEINBERG)

# Save the output image
bw_image.save(output_path)
print(f"Processed image saved to {output_path}")
print(f"Image resized to {target_width}x{new_height} pixels")
if image.width > image.height:
    print("Image was rotated 90 degrees to portrait mode.")

