import os
import subprocess
from latex_engine.injector import inject_content

TEMPLATE_DIR = "templates"

def get_available_formats():
    return [
        name for name in os.listdir(TEMPLATE_DIR)
        if os.path.isdir(os.path.join(TEMPLATE_DIR, name))
    ]

def compile_pdf(tex_path):
    directory = os.path.dirname(os.path.abspath(tex_path))
    filename  = os.path.basename(tex_path)

    result = subprocess.run(
        ["xelatex", "-interaction=nonstopmode", filename],
        cwd=directory,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0:
        # Surface the real error from the log file
        log_path = tex_path.replace(".tex", ".log")
        error_detail = ""
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                log_lines = f.readlines()
            # Grab lines starting with "!" (LaTeX errors) plus a few context lines
            error_lines = []
            for i, line in enumerate(log_lines):
                if line.startswith("!"):
                    error_lines.extend(log_lines[i : i + 4])
            error_detail = "".join(error_lines[:20]).strip()

        msg = f"PDF compilation failed"
        if error_detail:
            msg += f":\n{error_detail}"
        else:
            msg += ". Check that pdflatex is installed and templates are valid."
        raise Exception(msg)

    pdf_path = tex_path.replace(".tex", ".pdf")
    if not os.path.exists(pdf_path):
        raise Exception("PDF compilation appeared to succeed but no .pdf was produced.")
    return pdf_path

def generate_formats(content_dict, formats, output_type="pdf"):
    generated_paths = {}

    for format_name in formats:
        template_path = os.path.join(TEMPLATE_DIR, format_name, "main.tex")

        if not os.path.exists(template_path):
            continue

        filled_tex = inject_content(template_path, content_dict)

        output_dir = os.path.join("outputs", format_name)
        os.makedirs(output_dir, exist_ok=True)

        tex_path = os.path.join(output_dir, "output.tex")

        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(filled_tex)

        result_files = {"tex": tex_path}

        if output_type == "pdf":
            pdf_path = compile_pdf(tex_path)
            result_files["pdf"] = pdf_path

        generated_paths[format_name] = result_files

    return generated_paths
