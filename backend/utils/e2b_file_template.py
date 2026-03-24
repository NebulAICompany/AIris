from e2b import Template, default_build_logger
from dotenv import load_dotenv

load_dotenv()

FILE_AGENT_TEMPLATE_ALIAS = "file-agent-template"

template = (
    Template()
    .from_template("code-interpreter-v1")
    .pip_install("python-pptx")
    .pip_install("openpyxl")
    .pip_install("python-docx")
    .pip_install("Pillow")
)


def build_file_agent_template(alias: str = FILE_AGENT_TEMPLATE_ALIAS):
    """Build and register the file-agent template in E2B."""
    return Template.build(
        template,
        alias=alias,
        cpu_count=1,
        memory_mb=1024,
        on_build_logs=default_build_logger(),
    )


def ensure_file_agent_template(alias: str = FILE_AGENT_TEMPLATE_ALIAS):
    """Ensure the file-agent template exists by building it for the alias."""
    return build_file_agent_template(alias=alias)

if __name__ == "__main__":
    build_file_agent_template()
