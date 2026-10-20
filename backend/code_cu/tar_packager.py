import tarfile
import os
import shutil

def make_tarfile(output_filename: str, source_dir: str):
    """
    Create a tar.gz file from the source directory
    
    Args:
        output_filename: Path to the output .tar.gz file
        source_dir: Directory containing the course structure
    """
    try:
        with tarfile.open(output_filename, "w:gz") as tar:
            # Add all files and directories from source_dir
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Calculate the arcname (path within the tar file)
                    arcname = os.path.relpath(file_path, source_dir)
                    tar.add(file_path, arcname=arcname)
        
        print(f"Successfully created {output_filename}")
        return True
    except Exception as e:
        print(f"Error creating tar file: {e}")
        return False

def cleanup_temp_directory(temp_dir: str):
    """Clean up temporary directory after creating tar file"""
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        print(f"Error cleaning up directory: {e}") 