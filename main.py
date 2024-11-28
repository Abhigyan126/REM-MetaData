import os
import random
import string
import subprocess
import imghdr
import piexif
from PIL import Image
from multiprocessing import Pool, cpu_count

def random_string(length=20):
    """Generate a random string of given length."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def remove_all_metadata(input_tuple):
    """
    Comprehensively remove all possible metadata from images.
    Supports PNG, JPEG, TIFF, and other common image formats.
    
    :param input_tuple: Tuple containing input_path and output_folder
    :return: Tuple of (success, input_filename, error_message)
    """
    input_path, output_folder = input_tuple
    
    try:
        # Determine image type
        image_type = imghdr.what(input_path)
        if not image_type:
            return (False, os.path.basename(input_path), "Unsupported or invalid image file")

        # Generate completely random filename
        output_filename = f"{random_string()}.{image_type}"
        output_path = os.path.join(output_folder, output_filename)

        # Open image with Pillow
        with Image.open(input_path) as img:
            # Strip out all metadata
            data = list(img.getdata())
            img_without_metadata = Image.new(img.mode, img.size)
            img_without_metadata.putdata(data)
            
            # Save without preserving exif
            img_without_metadata.save(output_path, optimize=True, compress_level=9)

        # Additional metadata removal for JPEG files
        if image_type in ['jpg', 'jpeg']:
            # Remove EXIF data completely
            try:
                piexif.remove(output_path)
            except Exception:
                pass

        # Remove extended attributes
        if os.name == 'posix':
            try:
                subprocess.run(["xattr", "-c", output_path], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                pass

        # Modify timestamps to epoch start
        try:
            os.utime(output_path, (0, 0))
        except Exception:
            pass

        return (True, os.path.basename(input_path), None)

    except Exception as e:
        return (False, os.path.basename(input_path), str(e))

def process_folder(input_folder, output_folder):
    """Process all images in the folder, removing all metadata using multiprocessing."""
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Collect image files
    image_files = []
    for filename in os.listdir(input_folder):
        input_path = os.path.join(input_folder, filename)
        
        # Skip non-files
        if not os.path.isfile(input_path):
            continue

        # Skip non-image files
        try:
            image_type = imghdr.what(input_path)
            if image_type:
                image_files.append((input_path, output_folder))
        except Exception:
            continue

    # Determine optimal number of processes
    num_processes = min(cpu_count(), len(image_files))

    # Use multiprocessing to process images
    with Pool(processes=num_processes) as pool:
        results = pool.map(remove_all_metadata, image_files)

    # Print processing results
    successful = [r for r in results if r[0]]
    failed = [r for r in results if not r[0]]

    print(f"\nProcessing Summary:")
    print(f"Total images processed: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    # Print detailed error information if any files failed
    if failed:
        print("\nFailed Files:")
        for _, filename, error in failed:
            print(f"- {filename}: {error}")

def main():
    input_folder = "input"  # Input folder with images to clean
    output_folder = "output"  # Folder to save cleaned images

    print(f"Starting comprehensive metadata removal from: {input_folder}")
    process_folder(input_folder, output_folder)
    print(f"Completed. Cleaned images saved to: {output_folder}")

if __name__ == "__main__":
    main()