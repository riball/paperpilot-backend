import subprocess
import os

def compile_pdf(tex_path):
    directory = os.path.dirname(tex_path)
    filename = os.path.basename(tex_path)

    command = [
        "pdflatex",
        "-interaction=nonstopmode",
        filename
    ]

    subprocess.run(
        command,
        cwd=directory,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    pdf_path = tex_path.replace(".tex", ".pdf")
    return pdf_path