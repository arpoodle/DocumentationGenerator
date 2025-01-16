import os
import re
import requests

# -----------------------------
# CONFIGURATION
# -----------------------------

# OpenAI API Configuration
OPENAI_API_KEY = "XXXXXXXXXXXXXXXX"  # Set your OpenAI API key here
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MODEL_NAME = "gpt-4o"

# Local Filesystem Configuration
LOCAL_REPO_PATH = "./"  # Path to the local repository

# We only care about these file extensions
FILE_EXTENSIONS = [".sql", ".sh", ".php"]

# Overview file name
OVERVIEW_FILENAME = "PROJECT_OVERVIEW.md"

# Regex patterns for includes/requires (simple approach)
PHP_INCLUDE_PATTERN = r'(include|require)(_once)?\s*\(?[\'"]([^\'"]+)[\'"]\)?'
SQL_INCLUDE_PATTERN = r'\\i\s+([^;\s]+)'

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------

def traverse_local_files(path, file_list=None):
    """
    Recursively traverses the local filesystem starting at 'path'.
    Builds a list of all files with their paths.
    """
    if file_list is None:
        file_list = []

    for root, dirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            file_list.append(file_path)

    return file_list

def read_file_content(path):
    """
    Reads the content of a local file and returns it as a string.
    """
    with open(path, "r", encoding="utf-8") as file:
        return file.read()

def save_file_in_same_directory(original_file_path, content, suffix="_doc.txt"):
    """
    Saves content to a file in the same directory as the original file.
    """
    base_dir = os.path.dirname(original_file_path)
    base_name = os.path.splitext(os.path.basename(original_file_path))[0]
    output_file_path = os.path.join(base_dir, f"{base_name}{suffix}")

    os.makedirs(base_dir, exist_ok=True)
    with open(output_file_path, "w", encoding="utf-8") as file:
        file.write(content)
    print(f"File saved: {output_file_path}")
    return output_file_path

def generate_documentation_with_openai(file_path, file_content):
    """
    Calls OpenAI API to generate documentation for a file's content.
    """
    prompt_text = f"""
Can you write a short page documenting this scrfipt? {os.path.splitext(file_path)[1]}
File content:
{file_content}
"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }
    data = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.7,
    }

    response = requests.post(OPENAI_API_URL, headers=headers, json=data)
    response.raise_for_status()
    completion = response.json()
    return completion["choices"][0]["message"]["content"]

def find_references_in_content(file_path, content):
    """
    Naively scan content for references.
    - For PHP, we look for includes/requires using `PHP_INCLUDE_PATTERN`.
    - For SQL, we look for `i filename` references using `SQL_INCLUDE_PATTERN`.
    Returns a list of referenced filenames (strings).
    """
    ext = os.path.splitext(file_path)[1].lower()
    references = []

    if ext == ".php":
        matches = re.findall(PHP_INCLUDE_PATTERN, content)
        references.extend(m[2] for m in matches)
    elif ext == ".sql":
        matches = re.findall(SQL_INCLUDE_PATTERN, content)
        references.extend(m.strip() for m in matches)

    return references

def generate_overview_document(file_docs, file_references):
    """
    Creates a single 'PROJECT_OVERVIEW.md' that includes:
    1) A structured breakdown of each file's doc plus references.

    - file_docs: dict {file_path: doc_text}
    - file_references: dict {file_path: [list_of_referenced_paths]}
    """
    lines = []
    lines.append("# Project Overview")
    lines.append("")
    lines.append("This document provides a high-level summary of the codebase, including file-by-file documentation and references.")
    lines.append("")

    for path in sorted(file_docs.keys()):
        doc_text = file_docs[path]
        refs = file_references.get(path, [])
        lines.append(f"## {path}")
        lines.append("")
        lines.append("**Documentation**")
        lines.append("")
        lines.append(doc_text.strip())
        lines.append("")

        if refs:
            lines.append("**References / Includes**")
            lines.append("")
            for r in refs:
                lines.append(f"- {r}")
            lines.append("")

    return "\n".join(lines)

# -----------------------------
# MAIN LOGIC
# -----------------------------

def main():
    print("Traversing local repository...")
    all_files = traverse_local_files(LOCAL_REPO_PATH)

    relevant_files = [
        f for f in all_files if os.path.splitext(f)[1].lower() in FILE_EXTENSIONS
    ]

    if not relevant_files:
        print("No relevant files found for processing.")
        return

    print(f"Total relevant files found: {len(relevant_files)}")

    file_docs = {}        # { file_path : doc_text }
    file_references = {}  # { file_path : [list_of_references] }

    for file_path in relevant_files:
        print(f"Processing file: {file_path}")
        try:
            content = read_file_content(file_path)
            print(f"Read content of {file_path} successfully.")

            doc_text = generate_documentation_with_openai(file_path, content)
            print(f"Generated documentation for {file_path}.")

            file_docs[file_path] = doc_text

            refs = find_references_in_content(file_path, content)
            file_references[file_path] = refs
            print(f"Found {len(refs)} references in {file_path}.")

            save_file_in_same_directory(file_path, doc_text)
        except Exception as e:
            print(f"Failed to process file {file_path}: {e}")

    print("Generating overview document...")
    overview_text = generate_overview_document(file_docs, file_references)
    overview_path = os.path.join(LOCAL_REPO_PATH, OVERVIEW_FILENAME)
    with open(overview_path, "w", encoding="utf-8") as file:
        file.write(overview_text)
    print(f"Overview saved: {overview_path}")

    print("All done.")

if __name__ == "__main__":
    main()
