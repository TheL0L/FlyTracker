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

def get_basename(file_path: str) -> str:
    """
    Get the base name of a file path.

    This function returns the base name of a file path. The base name is the final component of the path.

    Args:
        file_path (str): The file path to get the base name from.

    Returns:
        str: The base name of the file path.
    """
    return os.path.basename(file_path)

def get_extension(file_path: str) -> str:
    """
    Get the file extension from a file path.

    This function returns the file extension of the specified file path. The extension is the portion of the file name
    after the last period.

    Args:
        file_path (str): The file path to get the extension from.

    Returns:
        str: The file extension of the file path.
    """
    return os.path.splitext(file_path)[1]

def get_basename_stem(file_path: str) -> str:
    """
    Get the base name of a file path without the extension.

    This function returns the base name of a file path, excluding the file extension. The base name is the final component of the path,
    and the extension is the portion of the file name after the last period.

    Args:
        file_path (str): The file path to get the base name without the extension from.

    Returns:
        str: The base name of the file path without the extension.
    """
    return os.path.splitext(os.path.basename(file_path))[0]
