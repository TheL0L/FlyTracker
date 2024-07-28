import os

def normalize_path(file_path: str) -> str:
    """
    Normalize a filesystem path.

    This function takes a string representing a file path and normalizes it by collapsing redundant separators
    and up-level references.

    Args:
        file_path (str): The file path to normalize.

    Returns:
        str: The normalized file path.
    """
    return os.path.normpath(file_path).replace('\\', '/')

def prepare_output_path(output_path: str) -> None:
    """
    Prepare an output directory path.

    This function ensures that the directory specified by the output path exists. If the directory does not exist,
    it creates all necessary parent directories.

    Args:
        output_path (str): The path of the directory to prepare.

    Returns:
        None
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)

def check_existance(path: str) -> bool:
    """
    Check the existence of a file or directory.

    This function checks whether a file or directory exists at the specified path.

    Args:
        file_path (str): The file or directory path to check.

    Returns:
        bool: True if the file or directory exists, False otherwise.
    """
    return os.path.exists(path)

def join_paths(path: str, *paths: str) -> str:
    """
    Join one or more path components.

    This function joins one or more path components intelligently. It returns a normalized version of the joined path.

    Args:
        path (str): The first path component.
        *paths (str): Additional path components to join.

    Returns:
        str: The normalized, joined path.
    """
    return normalize_path(os.path.join(path, *paths))

def split_path(path: str) -> tuple[str, str, str]:
    """
    Split a given path into directory, filename, and extension.

    This function splits a given file path into its directory, base filename, and file extension components.
    The directory is the portion of the path leading up to the final component, the filename is the name of the file
    without the extension, and the extension is the portion of the file name after the last period.

    Args:
        path (str): The file path to split into directory, filename, and extension.

    Returns:
        tuple: A tuple containing the directory, filename, and extension.
            - directory (str): The directory of the file path.
            - filename (str): The base name of the file without the extension.
            - extension (str): The file extension, including the period.
    """
    directory, filename = os.path.split(path)
    filename, extension = os.path.splitext(filename)
    return directory, filename, extension
