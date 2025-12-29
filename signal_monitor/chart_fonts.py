import matplotlib.pyplot as plt
from matplotlib import font_manager

DEFAULT_FONT_CANDIDATES = [
    "Microsoft YaHei",
    "SimHei",
    "WenQuanYi Micro Hei",
    "Noto Sans CJK SC",
    "Noto Sans CJK",
    "Noto Sans",
    "DejaVu Sans",
]


def configure_matplotlib_fonts(preferred=None):
    candidates = preferred or DEFAULT_FONT_CANDIDATES
    available = {font.name for font in font_manager.fontManager.ttflist}
    selected = [name for name in candidates if name in available]
    if not selected:
        selected = ["DejaVu Sans"]
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = selected
    plt.rcParams["axes.unicode_minus"] = False
    return selected
