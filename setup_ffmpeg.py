import os
import requests
import zipfile
import io
import sys
import shutil
import subprocess

def download_ffmpeg():
    print("Downloading FFmpeg for Windows...")
    
    # URL for the FFmpeg Windows build
    url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    
    try:
        # Create a directory for FFmpeg if it doesn't exist
        ffmpeg_dir = os.path.join(os.getcwd(), "ffmpeg")
        if not os.path.exists(ffmpeg_dir):
            os.makedirs(ffmpeg_dir)
        
        # Download the zip file
        print("Downloading from:", url)
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Extract the zip file
        print("Extracting FFmpeg...")
        z = zipfile.ZipFile(io.BytesIO(response.content))
        z.extractall(ffmpeg_dir)
        
        # Find the extracted directory (it might have a version number)
        extracted_dirs = [d for d in os.listdir(ffmpeg_dir) if os.path.isdir(os.path.join(ffmpeg_dir, d))]
        if not extracted_dirs:
            print("Error: No directories found in the extracted content")
            return False
        
        extracted_dir = os.path.join(ffmpeg_dir, extracted_dirs[0])
        bin_dir = os.path.join(extracted_dir, "bin")
        
        if not os.path.exists(bin_dir):
            print(f"Error: bin directory not found in {extracted_dir}")
            return False
        
        # Copy the executables to the project directory
        for exe in ["ffmpeg.exe", "ffprobe.exe"]:
            src = os.path.join(bin_dir, exe)
            dst = os.path.join(os.getcwd(), exe)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"Copied {exe} to {dst}")
            else:
                print(f"Warning: {exe} not found in {bin_dir}")
        
        print("FFmpeg setup complete!")
        return True
    
    except Exception as e:
        print(f"Error downloading or extracting FFmpeg: {e}")
        return False

def test_ffmpeg():
    try:
        # Test if ffmpeg is accessible
        result = subprocess.run(["ffmpeg", "-version"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE,
                               text=True)
        if result.returncode == 0:
            print("FFmpeg is working correctly!")
            print(result.stdout.split('\n')[0])  # Print the version
            return True
        else:
            print("FFmpeg test failed with error:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"Error testing FFmpeg: {e}")
        return False

if __name__ == "__main__":
    if download_ffmpeg():
        test_ffmpeg()
    else:
        print("Failed to set up FFmpeg")
