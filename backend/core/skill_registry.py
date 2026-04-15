from pathlib import Path
import sys
from langchain_core.tools import tool 

# vectorrag (workspace root) path'ini Python path'e ekle, böylece backend module'ü bulunabilir
_current_file = Path(__file__).resolve()
_core_dir = _current_file.parent
_backend_dir = _core_dir.parent
_vectorrag_root = _backend_dir.parent

if str(_vectorrag_root) not in sys.path:
    sys.path.insert(0, str(_vectorrag_root))

from backend.shared.constants import SKILLS_DIR

def register_skill_intros():
    """
    Register all skill introductions by aggregating SKILL.md frontmatter.

    Returns:
        str: A concatenated string of all skill introductions (frontmatter blocks).
    """
    registry = ""
    file_list = iter_skill_md_files()

    for file_path in file_list:
        print("here")
        markdown = read_md_file(file_path)
        intro = parse_frontmatter(markdown)
        if intro:
            registry += f"\n{intro}\n"
    return registry

@tool(parse_docstring=True)
def skill_loader(skill_name: str) -> str:
    """
    Load the SKILL.md content for a given skill name.

    Args:
        skill_name: The name of the skill folder to load.

    Returns:
        The full SKILL.md content, or an error message if not found.
    """
    skill_md_path = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_md_path.is_file():
        return f"Error: No SKILL.md found for skill '{skill_name}'."
    
    markdown = read_md_file(skill_md_path)
    return markdown


def iter_skill_md_files() -> list[Path]:
    """
    Iterate skill folders and return existing SKILL.md files.

    Returns:
        list[Path]: List of Path objects pointing to each SKILL.md file found.
    """
    if not SKILLS_DIR.exists() or not SKILLS_DIR.is_dir():
        return []

    files: list[Path] = []
    for folder in sorted(SKILLS_DIR.iterdir(), key=lambda p: p.name.lower()):
        if folder.is_dir():
            skill_md = folder / "SKILL.md"
            if skill_md.is_file():
                files.append(skill_md)
    return files


def read_md_file(md_path: Path) -> str:
    """
    Read markdown file content.

    Args:
        md_path: Path object pointing to the markdown file.

    Returns:
        str: The full content of the markdown file.
    """
    return md_path.read_text(encoding="utf-8")


def parse_frontmatter(markdown_text: str) -> str | None:
    """
    Extract text between opening and closing --- lines (YAML frontmatter).

    Args:
        markdown_text: The full markdown text content.

    Returns:
        str | None: The frontmatter content, or empty string if not found.
    """
    # İlk --- bul
    first_sep = markdown_text.find("---")
    if first_sep == -1:
        return ""
    
    # İkinci --- bul
    second_sep = markdown_text.find("---", first_sep + 3)
    if second_sep == -1:
        return ""
    
    # Arasındaki kısmı döndür
    content = markdown_text[first_sep + 3:second_sep].strip()
    return content if content else ""



if __name__ == "__main__":
    print("Registering skills...")
    print(register_skill_intros())
