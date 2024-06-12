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
    return os.path.normpath(file_path)

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

