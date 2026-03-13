from e2b import Template, default_build_logger
from dotenv import load_dotenv

load_dotenv()

template = (
    Template()
    .from_template("code-interpreter-v1")
    .pip_install("python-pptx")
    .pip_install("openpyxl")
    .pip_install("python-docx")
    .pip_install("Pillow")
)

if __name__ == "__main__":
    Template.build(
        template,
        alias="file-agent-template",
        cpu_count=1,
        memory_mb=1024,
        on_build_logs=default_build_logger(),
    )
