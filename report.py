import os
import pandas as pd
from pylatex import Document, Section, Tabular, Figure, NoEscape, Package


# ------------------ READ EXCEL ------------------
def read_excel_data(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Common name fixes
    rename_map = {
        "x": "start",
        "position": "start",
        "distance": "start",
        "shear": "shear force",
        "shearforce": "shear force",
        "moment": "bending moment",
        "bendingmoment": "bending moment",
        "to": "end",
    }
    df = df.rename(columns=lambda c: rename_map.get(c, c))

    required = {"start", "shear force", "bending moment"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Excel columns found: {df.columns.tolist()}\n"
            f"Missing required columns: {missing}\n"
            "Required: Start, Shear Force, Bending Moment"
        )

    if "end" not in df.columns:
        df["end"] = pd.NA

    df["start"] = pd.to_numeric(df["start"])
    df["shear force"] = pd.to_numeric(df["shear force"])
    df["bending moment"] = pd.to_numeric(df["bending moment"])
    df["end"] = pd.to_numeric(df["end"], errors="coerce")

    df = df.sort_values("start").reset_index(drop=True)
    return df


def coords_to_str(xs, ys):
    return " ".join([f"({x:.4f},{y:.4f})" for x, y in zip(xs, ys)])


# ------------------ BUILD PDF ------------------
def build_report(excel_path: str, beam_image: str, out_name="beam_report"):
    df = read_excel_data(excel_path)

    xs = df["start"].tolist()
    V = df["shear force"].tolist()
    M = df["bending moment"].tolist()

    L = max(xs) if xs else 0

    sfd_str = coords_to_str(xs, V)
    bmd_str = coords_to_str(xs, M)

    doc = Document()
    doc.packages.append(Package("graphicx"))
    doc.packages.append(Package("float"))
    doc.packages.append(Package("tikz"))
    doc.packages.append(Package("pgfplots"))
    doc.append(NoEscape(r"\pgfplotsset{compat=1.18}"))

    # Title
    doc.preamble.append(NoEscape(r"\title{Beam Engineering Report}"))
    doc.preamble.append(NoEscape(r"\author{Auto Generated}"))
    doc.preamble.append(NoEscape(r"\date{\today}"))
    doc.append(NoEscape(r"\maketitle"))

    # ---------- INTRO ----------
    with doc.create(Section("Introduction")):
        doc.append("This report is generated from Excel beam result data.")
        doc.append(NoEscape(rf"\newline Beam Span: {L:.2f} m"))

        if os.path.exists(beam_image):
            with doc.create(Figure(position="H")) as fig:
                fig.add_image(beam_image, width=NoEscape(r"0.8\textwidth"))
                fig.add_caption("Simply Supported Beam")

    # ---------- TABLE ----------
    with doc.create(Section("Excel Table")):
        with doc.create(Tabular("|c|c|c|c|")) as table:
            table.add_hline()
            table.add_row(["Start", "End", "Shear Force", "Bending Moment"])
            table.add_hline()

            for _, r in df.iterrows():
                table.add_row([
                    f"{r['start']:.2f}",
                    "" if pd.isna(r["end"]) else f"{r['end']:.2f}",
                    f"{r['shear force']:.2f}",
                    f"{r['bending moment']:.2f}"
                ])
                table.add_hline()

    # ---------- DIAGRAMS ----------
    with doc.create(Section("Diagrams")):
        doc.append(NoEscape(rf"""
\begin{{center}}
\begin{{tikzpicture}}
\begin{{axis}}[
title=Shear Force Diagram,
xlabel=x,
ylabel=V,
grid=both]
\addplot coordinates {{{sfd_str}}};
\end{{axis}}
\end{{tikzpicture}}
\end{{center}}
"""))

        doc.append(NoEscape(rf"""
\begin{{center}}
\begin{{tikzpicture}}
\begin{{axis}}[
title=Bending Moment Diagram,
xlabel=x,
ylabel=M,
grid=both]
\addplot coordinates {{{bmd_str}}};
\end{{axis}}
\end{{tikzpicture}}
\end{{center}}
"""))

    # ---------- GENERATE PDF (IMPORTANT FIX) ----------
    doc.generate_pdf(out_name, clean_tex=False, compiler="pdflatex")

    print(f"\nPDF Generated: {out_name}.pdf")


# ------------------ RUN ------------------
if __name__ == "__main__":
    build_report("loads.xlsx", "beam.png", "beam_report")
