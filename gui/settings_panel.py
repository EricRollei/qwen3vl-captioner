"""
Settings Panel (Right Sidebar) — VL-CAPTIONER Studio Pro

Model configuration, target architecture presets, caption length,
extra captioning options, generation parameters, prompt formatting,
batch controls, and model status display. Matches the Figma design.
"""

from pathlib import Path
from typing import Optional, Dict, List

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QComboBox, QSlider, QTextEdit, QLineEdit, QFrame, QScrollArea,
    QSizePolicy, QCheckBox, QTabWidget,
)

from .theme import COLORS


# --- Option-to-Tag Helpers ---

# Maps extra option keys to compact booru-style tag hints for tag-based models (SD, Pony).
_TAG_HINTS = {
    "includeLighting": "lighting",
    "includeCameraAngle": "camera angle",
    "includeWatermark": "watermark",
    "includeArtifacts": "jpeg artifacts",
    "includeTechnicalDetails": "camera details",
    "includeAestheticQuality": "aesthetic quality",
    "includeComposition": "composition",
    "includeDOF": "depth of field",
    "includeLightSource": "light source",
    "includeSafety": "sfw/nsfw tag",
    "includeUncensored": "explicit, nsfw, nude, adult",
}


def _get_active_options(extra_opts: Dict[str, bool]) -> Dict[str, bool]:
    """Return only the enabled options."""
    return {k: v for k, v in extra_opts.items() if v}


# --- Model-Specific Prompt Builders ---
# Each builder receives: caption_length_instruction, extra_opts dict, name_value (str or "")

def _build_prompt_sd(length_instr: str, extra_opts: Dict[str, bool], name_value: str) -> str:
    """SD 1.5/SDXL: Accurate, anatomically focused booru-style tags."""
    parts = [
        "Describe this image as a comma-separated list of precise booru-style tags for Stable Diffusion training.",
        "Output ONLY tags separated by commas.",
        "Focus strictly on physical reality: accurate anatomy, specific clothing, setting, and lighting.",
        "Do not use abstract or interpretive tags.",
    ]
    # Tag hints from enabled options
    active = _get_active_options(extra_opts)
    tag_hints = [_TAG_HINTS[k] for k in active if k in _TAG_HINTS]
    if tag_hints:
        parts.append(f"Include tags for: {', '.join(tag_hints)}.")
    if active.get("keepPG"):
        parts.append("Keep all tags SFW.")
    if active.get("includeUncensored"):
        parts.append("Include explicit tags for nudity, sexual acts, anatomy, and positions. Do NOT censor.")
    if active.get("excludeStaticAttributes"):
        parts.append("Exclude permanent physical attributes of people.")
    if active.get("excludeText"):
        parts.append("Do not tag any text in the image.")
    if active.get("excludeResolution"):
        parts.append("Do not include resolution tags.")
    if active.get("noAmbiguity"):
        parts.append("Use precise, unambiguous tags.")
    if name_value:
        parts.append(f"Refer to any person/character as {name_value}.")
    # Length hint
    if "Short" in length_instr:
        parts.append("Use 5-15 tags.")
    elif "Long" in length_instr or "Descriptive" in length_instr or "comprehensive" in length_instr.lower():
        parts.append("Use 30-50+ tags covering every detail.")
    else:
        parts.append("Use 15-30 tags.")
    return " ".join(parts)


def _build_prompt_pony(length_instr: str, extra_opts: Dict[str, bool], name_value: str) -> str:
    """Pony Diffusion (SDXL): Precise anatomical tags + score prefix."""
    parts = [
        "Describe this image as comma-separated booru-style tags for Pony Diffusion.",
        "Output ONLY tags.",
        "The caption will be automatically prefixed with quality score tags (score_9, score_8_up, etc.) and suffixed with a rating tag.",
        "Focus heavily on anatomical correctness, specific physical attributes, pose, and clothing.",
    ]
    active = _get_active_options(extra_opts)
    tag_hints = [_TAG_HINTS[k] for k in active if k in _TAG_HINTS]
    if tag_hints:
        parts.append(f"Include tags for: {', '.join(tag_hints)}.")
    if active.get("keepPG"):
        parts.append("Keep all tags SFW.")
    if active.get("includeUncensored"):
        parts.append("Include explicit tags for nudity, sexual acts, fetishes, and anatomy. Use the 'rating_explicit' tag.")
    if active.get("excludeStaticAttributes"):
        parts.append("Exclude permanent physical attributes of people.")
    if active.get("excludeText"):
        parts.append("Do not tag any text in the image.")
    if active.get("noAmbiguity"):
        parts.append("Use precise, unambiguous tags.")
    if name_value:
        parts.append(f"Refer to any person/character as {name_value}.")
    if "Short" in length_instr:
        parts.append("Use 5-15 tags.")
    elif "Long" in length_instr or "Descriptive" in length_instr or "comprehensive" in length_instr.lower():
        parts.append("Use 30-50+ tags.")
    else:
        parts.append("Use 15-30 tags.")
    return " ".join(parts)


def _build_prompt_flux1(length_instr: str, extra_opts: Dict[str, bool], name_value: str) -> str:
    """Flux.1: Objective, anatomically detailed description (less poetic)."""
    parts = [
        "Write a highly accurate, objectively detailed description of this image for Flux.1 training.",
        "Use clear, descriptive prose — NOT tags.",
        "Focus on physical reality: anatomy, precise shapes, textures, and spatial relations.",
        "Avoid poetic language or storytelling. Be direct and descriptive.",
    ]
    active = _get_active_options(extra_opts)
    nl_extras = []
    if active.get("includeLighting"):
        nl_extras.append("precise lighting details")
    if active.get("includeCameraAngle"):
        nl_extras.append("exact camera angle")
    if active.get("includeTechnicalDetails"):
        nl_extras.append("technical camera parameters")
    if active.get("includeComposition"):
        nl_extras.append("composition style")
    if active.get("includeDOF"):
        nl_extras.append("focal depth")
    if active.get("includeLightSource"):
        nl_extras.append("light sources")
    if active.get("includeAestheticQuality"):
        nl_extras.append("image quality")
    if nl_extras:
        parts.append(f"Include objective details about: {', '.join(nl_extras)}.")
    if active.get("keepPG"):
        parts.append("Keep the description SFW.")
    if active.get("includeUncensored"):
        parts.append("Describe all anatomical details, including genitalia, sexual acts, and nudity, with explicit and anatomically correct terminology. Do not use euphemisms.")
    if active.get("excludeStaticAttributes"):
        parts.append("Do not describe unchangeable physical attributes.")
    if active.get("excludeText"):
        parts.append("Ignore text in the image.")
    if active.get("excludeResolution"):
        parts.append("Ignore resolution.")
    if active.get("includeWatermark"):
        parts.append("Note if a watermark is present.")
    if active.get("includeArtifacts"):
        parts.append("Note any image artifacts.")
    if active.get("includeSafety"):
        parts.append("State the NSFW/SFW rating.")
    if active.get("noAmbiguity"):
        parts.append("Use precise, clinical language.")
    if name_value:
        parts.append(f"Refer to the subject as {name_value}.")
    if length_instr:
        parts.append(length_instr)
    return " ".join(parts)


def _build_prompt_flux2(length_instr: str, extra_opts: Dict[str, bool], name_value: str) -> str:
    """Flux.2: Objective, anatomically detailed description (less poetic/cinematic)."""
    parts = [
        "Write a highly accurate, objectively detailed description of this image for Flux.2 training.",
        "Focus on physical reality: anatomy, skin texture, precise shapes, and spatial relations.",
        "Avoid poetic language, storytelling, or ambiguous metaphors. Be direct and descriptive.",
        "You MUST describe human anatomy, body proportions, and physical features in extreme detail.",
    ]
    active = _get_active_options(extra_opts)
    nl_extras = []
    if active.get("includeLighting"):
        nl_extras.append("precise lighting conditions")
    if active.get("includeCameraAngle"):
        nl_extras.append("exact camera angle")
    if active.get("includeComposition"):
        nl_extras.append("composition and framing")
    if active.get("includeDOF"):
        nl_extras.append("focal depth")
    if active.get("includeLightSource"):
        nl_extras.append("light sources")
    if active.get("includeAestheticQuality"):
        nl_extras.append("image quality")
    if active.get("includeTechnicalDetails"):
        nl_extras.append("technical camera parameters")
    if nl_extras:
        parts.append(f"Include objective details about: {', '.join(nl_extras)}.")
    if active.get("keepPG"):
        parts.append("Keep the description SFW.")
    if active.get("includeUncensored"):
        parts.append("Describe all anatomical details, including genitalia, sexual acts, and nudity, with explicit and anatomically correct terminology. Do not use euphemisms.")
    if active.get("excludeStaticAttributes"):
        parts.append("Do not describe unchangeable physical attributes.")
    if active.get("excludeText"):
        parts.append("Ignore text in the image.")
    if active.get("excludeResolution"):
        parts.append("Ignore resolution.")
    if active.get("includeWatermark"):
        parts.append("Note if a watermark is present.")
    if active.get("includeArtifacts"):
        parts.append("Note any image artifacts.")
    if active.get("includeSafety"):
        parts.append("State the NSFW/SFW rating.")
    if active.get("noAmbiguity"):
        parts.append("Use precise, clinical language.")
    if name_value:
        parts.append(f"Refer to the subject as {name_value}.")
    if length_instr:
        parts.append(length_instr)
    return " ".join(parts)


def _build_prompt_zimage(length_instr: str, extra_opts: Dict[str, bool], name_value: str) -> str:
    """Z-Image: Objective, clinical natural language description."""
    parts = [
        "Write a detailed, objective natural language description of this image for Z-Image fine-tuning.",
        "Focus on the physical subject, anatomy, environment, and specific lighting details.",
        "Be precise and descriptive. Avoid ambiguous or emotive language.",
    ]
    active = _get_active_options(extra_opts)
    nl_extras = []
    if active.get("includeLighting"):
        nl_extras.append("lighting details")
    if active.get("includeCameraAngle"):
        nl_extras.append("exact camera angle")
    if active.get("includeTechnicalDetails"):
        nl_extras.append("technical details")
    if active.get("includeComposition"):
        nl_extras.append("composition")
    if active.get("includeDOF"):
        nl_extras.append("depth of field")
    if active.get("includeLightSource"):
        nl_extras.append("light sources")
    if active.get("includeAestheticQuality"):
        nl_extras.append("image quality")
    if nl_extras:
        parts.append(f"Include objective details about: {', '.join(nl_extras)}.")
    if active.get("keepPG"):
        parts.append("Keep the description SFW.")
    if active.get("includeUncensored"):
        parts.append("Provide a fully explicit, anatomically correct description of nudity, genitalia, and sexual acts. Do not use euphemisms.")
    if active.get("excludeStaticAttributes"):
        parts.append("Do not describe unchangeable physical attributes.")
    if active.get("excludeText"):
        parts.append("Ignore text in the image.")
    if active.get("excludeResolution"):
        parts.append("Ignore resolution.")
    if active.get("includeWatermark"):
        parts.append("Note if a watermark is present.")
    if active.get("includeArtifacts"):
        parts.append("Note any image artifacts.")
    if active.get("includeSafety"):
        parts.append("State the NSFW/SFW rating.")
    if active.get("noAmbiguity"):
        parts.append("Use precise, clinical language.")
    if name_value:
        parts.append(f"Refer to the subject as {name_value}.")
    if length_instr:
        parts.append(length_instr)
    return " ".join(parts)


def _build_prompt_chroma(length_instr: str, extra_opts: Dict[str, bool], name_value: str) -> str:
    """Chroma: Detailed objective description focusing on color/form."""
    parts = [
        "Write a detailed, objective description of this image for Chroma model training.",
        "Focus on precise colors, lighting, physical forms, and anatomy.",
        "Use clear, descriptive prose. Avoid subjective artistic interpretation.",
    ]
    active = _get_active_options(extra_opts)
    nl_extras = []
    if active.get("includeLighting"):
        nl_extras.append("precise lighting and color temperature")
    if active.get("includeCameraAngle"):
        nl_extras.append("camera perspective")
    if active.get("includeComposition"):
        nl_extras.append("composition")
    if active.get("includeDOF"):
        nl_extras.append("focal depth")
    if active.get("includeLightSource"):
        nl_extras.append("light sources and their color")
    if active.get("includeAestheticQuality"):
        nl_extras.append("image quality")
    if active.get("includeTechnicalDetails"):
        nl_extras.append("technical details")
    if nl_extras:
        parts.append(f"Include objective details about: {', '.join(nl_extras)}.")
    if active.get("keepPG"):
        parts.append("Keep it PG.")
    if active.get("includeUncensored"):
        parts.append("Describe all anatomical details, including genitalia and sexual acts, with explicit and anatomically correct terminology.")
    if active.get("excludeStaticAttributes"):
        parts.append("Do not describe unchangeable physical attributes.")
    if active.get("excludeText"):
        parts.append("Ignore text in the image.")
    if active.get("excludeResolution"):
        parts.append("Ignore resolution.")
    if active.get("includeWatermark"):
        parts.append("Note if a watermark is present.")
    if active.get("includeArtifacts"):
        parts.append("Note any image artifacts.")
    if active.get("includeSafety"):
        parts.append("State the NSFW/SFW rating.")
    if active.get("noAmbiguity"):
        parts.append("Use precise language.")
    if name_value:
        parts.append(f"Refer to the subject as {name_value}.")
    if length_instr:
        parts.append(length_instr)
    return " ".join(parts)


def _build_prompt_qwen(length_instr: str, extra_opts: Dict[str, bool], name_value: str) -> str:
    """Qwen Image: Clinical, objective, comprehensive description."""
    parts = [
        "Provide a highly accurate, objective, and comprehensive description of this image for Qwen-based training.",
        "Use complete sentences. Focus on physical reality, anatomy, and precise visual details.",
        "Avoid storytelling, mood, or interpretation.",
    ]
    active = _get_active_options(extra_opts)
    # Append all applicable NL instructions (use full_text from 3-tuple)
    for key, _short, full_text in EXTRA_OPTIONS:
        if active.get(key):
            # referAsName handled separately
            if key == "referAsName":
                continue
            parts.append(full_text)
    if active.get("includeUncensored"):
         parts.append("Describe all anatomy, nudity, and sexual acts in clear, explicit, and anatomically correct terms.")
    if name_value:
        parts.append(f"Refer to the person/character as {name_value}.")
    if length_instr:
        parts.append(length_instr)
    return " ".join(parts)


def _build_prompt_generic(length_instr: str, extra_opts: Dict[str, bool], name_value: str, base_prompt: str) -> str:
    """Generic fallback: original concatenation behavior when no preset is selected."""
    parts = [base_prompt]
    if length_instr:
        parts.append(length_instr)
    active = _get_active_options(extra_opts)
    for key, _short, full_text in EXTRA_OPTIONS:
        if active.get(key):
            if key == "referAsName" and name_value:
                parts.append(f"If there is a person/character in the image you must refer to them as {name_value}.")
            elif key != "referAsName":
                parts.append(full_text)
    return " ".join(parts)


# --- Extra Captioning Options ---
# 3-tuples: (key, short_label, full_instruction)
# short_label → displayed on checkbox (fits narrow sidebar)
# full_instruction → shown as tooltip + used by prompt builders
EXTRA_OPTIONS = [
    ("referAsName", "Refer as {name}", "If there is a person/character in the image you must refer to them as {name}."),
    ("excludeStaticAttributes", "Exclude static attributes", "Do NOT include information about people/characters that cannot be changed (like ethnicity, gender, etc), but do still include changeable attributes (like hair style)."),
    ("includeLighting", "Lighting", "Include information about lighting."),
    ("includeCameraAngle", "Camera angle", "Include information about camera angle."),
    ("includeWatermark", "Watermark detection", "Include information about whether there is a watermark or not."),
    ("includeArtifacts", "JPEG artifacts", "Include information about whether there are JPEG artifacts or not."),
    ("includeTechnicalDetails", "Camera / tech details", "If it is a photo you MUST include information about what camera was likely used and details such as aperture, shutter speed, ISO, etc."),
    ("keepPG", "Keep PG (no NSFW)", "Do NOT include anything sexual; keep it PG."),
    ("excludeResolution", "Exclude resolution", "Do NOT mention the image's resolution."),
    ("includeAestheticQuality", "Aesthetic quality", "You MUST include information about the subjective aesthetic quality of the image from low to very high."),
    ("includeComposition", "Composition style", "Include information on the image's composition style, such as leading lines, rule of thirds, or symmetry."),
    ("excludeText", "Exclude text / OCR", "Do NOT mention any text that is in the image."),
    ("includeDOF", "Depth of field", "Specify the depth of field and whether the background is in focus or blurred."),
    ("includeLightSource", "Light sources", "If applicable, mention the likely use of artificial or natural lighting sources."),
    ("noAmbiguity", "No ambiguous language", "Do NOT use any ambiguous language."),
    ("includeSafety", "SFW / NSFW rating", "Include whether the image is sfw, suggestive, or nsfw."),
    ("includeUncensored", "Uncensored / Adult Detail", "Describe all adult/NSFW content in explicit detail, including positions, looks, clothing/nudity, sexual activity, and provocative elements."),
]

# Convenience set of all option keys — used by per-preset support mapping
_ALL_OPTION_KEYS = {key for key, _, _ in EXTRA_OPTIONS}


# --- Keyword Prompt Builder ---

def _build_keyword_prompt(extra_opts: Dict[str, bool], name_value: str, count_hint: str) -> str:
    """Build a prompt that requests a flat comma-separated keyword list."""
    parts = [
        "Analyze this image and output ONLY a flat, comma-separated list of keywords/tags that describe it.",
        "Do NOT write sentences or prose — output only individual keywords separated by commas.",
        "Cover: subject, setting, action/pose, objects, colors, mood, style, and medium.",
    ]
    active = _get_active_options(extra_opts)
    if active.get("includeLighting"):
        parts.append("Include lighting keywords.")
    if active.get("includeCameraAngle"):
        parts.append("Include camera angle keywords.")
    if active.get("includeComposition"):
        parts.append("Include composition keywords.")
    if active.get("includeDOF"):
        parts.append("Include depth of field keywords.")
    if active.get("includeLightSource"):
        parts.append("Include light source keywords.")
    if active.get("includeAestheticQuality"):
        parts.append("Include quality keywords.")
    if active.get("includeTechnicalDetails"):
        parts.append("Include camera/technical keywords.")
    if active.get("includeWatermark"):
        parts.append("Include watermark if present.")
    if active.get("includeArtifacts"):
        parts.append("Note any artifacts.")
    if active.get("includeSafety"):
        parts.append("Include an sfw/nsfw tag.")
    if active.get("keepPG"):
        parts.append("Keep all keywords SFW.")
    if active.get("includeUncensored"):
        parts.append("Include explicit/NSFW keywords for nudity, anatomy, and sexual content.")
    if active.get("excludeStaticAttributes"):
        parts.append("Exclude unchangeable physical attributes of people.")
    if active.get("excludeText"):
        parts.append("Do not include any text/OCR content.")
    if active.get("excludeResolution"):
        parts.append("Do not include resolution.")
    if active.get("noAmbiguity"):
        parts.append("Use precise, unambiguous keywords.")
    if name_value:
        parts.append(f"Use '{name_value}' as the name tag for any person/character.")
    if count_hint:
        parts.append(count_hint)
    return " ".join(parts)


# --- Keyword Count Options ---
KEYWORD_COUNTS = {
    "Few (5-10)": "Output 5-10 keywords.",
    "Moderate (10-20)": "Output 10-20 keywords.",
    "Many (20-40)": "Output 20-40 keywords.",
    "Exhaustive (40+)": "Output 40 or more keywords covering every detail.",
}


# --- Caption Length Options ---
CAPTION_LENGTHS = {
    "Short": "Keep the description brief, around 1-2 sentences.",
    "Medium": "Provide a moderately detailed description in 2-4 sentences.",
    "Long": "Provide a long, detailed description covering all visual elements.",
    "Descriptive (Longest)": "Provide an extremely detailed, comprehensive description covering every visual element, style, mood, lighting, composition, and technical details.",
}

_ALL_LENGTH_KEYS = list(CAPTION_LENGTHS.keys())


# --- Target Architecture Presets ---
TARGET_PRESETS = [
    {
        "id": "sd",
        "name": "Stable Diffusion",
        "icon": "📦",
        "template": "Describe this image as comma-separated booru-style tags for Stable Diffusion training:",
        "prefix": "",
        "suffix": ", high quality, masterwork",
        "prompt_builder": _build_prompt_sd,
        "supported_options": _ALL_OPTION_KEYS,
        "allowed_lengths": ["Short", "Medium", "Long"],
    },
    {
        "id": "flux1",
        "name": "Flux 1",
        "icon": "🔥",
        "template": "Provide a very long, highly detailed natural language description of this image for Flux.1:",
        "prefix": "",
        "suffix": "",
        "prompt_builder": _build_prompt_flux1,
        "supported_options": _ALL_OPTION_KEYS,
        "allowed_lengths": _ALL_LENGTH_KEYS,
    },
    {
        "id": "flux2",
        "name": "Flux 2",
        "icon": "⚡",
        "template": "Provide a comprehensive aesthetic description for Flux.2:",
        "prefix": "",
        "suffix": "",
        "prompt_builder": _build_prompt_flux2,
        "supported_options": _ALL_OPTION_KEYS,
        "allowed_lengths": _ALL_LENGTH_KEYS,
    },
    {
        "id": "zimage",
        "name": "Z-Image",
        "icon": "🎯",
        "template": "Detailed description for Z-Image fine-tuning:",
        "prefix": "",
        "suffix": "",
        "prompt_builder": _build_prompt_zimage,
        "supported_options": _ALL_OPTION_KEYS,
        "allowed_lengths": _ALL_LENGTH_KEYS,
    },
    {
        "id": "chroma",
        "name": "Chroma",
        "icon": "🎨",
        "template": "Color-focused descriptive caption for Chroma:",
        "prefix": "",
        "suffix": "",
        "prompt_builder": _build_prompt_chroma,
        "supported_options": _ALL_OPTION_KEYS,
        "allowed_lengths": _ALL_LENGTH_KEYS,
    },
    {
        "id": "pony",
        "name": "Pony (SDXL)",
        "icon": "✨",
        "template": "Describe this image as comma-separated booru tags for Pony Diffusion:",
        "prefix": "score_9, score_8_up, score_7_up, ",
        "suffix": ", rating_safe",
        "prompt_builder": _build_prompt_pony,
        "supported_options": _ALL_OPTION_KEYS,
        "allowed_lengths": ["Short", "Medium", "Long"],
    },
    {
        "id": "qwen",
        "name": "Qwen Image",
        "icon": "💻",
        "template": "Provide a comprehensive description of this image for Qwen-based generation:",
        "prefix": "",
        "suffix": "",
        "prompt_builder": _build_prompt_qwen,
        "supported_options": _ALL_OPTION_KEYS,
        "allowed_lengths": _ALL_LENGTH_KEYS,
    },
]


class SettingsPanel(QFrame):
    """
    Right sidebar: model settings, target presets, caption options,
    parameters, formatting, and batch controls.
    """

    batch_caption_requested = pyqtSignal()
    export_requested = pyqtSignal()
    load_model_requested = pyqtSignal()
    unload_model_requested = pyqtSignal()
    download_model_requested = pyqtSignal(str)   # combo display name
    cancel_requested = pyqtSignal()               # cancel generation / batch / download
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "settings-panel")
        self.setMinimumWidth(280)
        self.setMaximumWidth(420)

        self._active_preset_id: Optional[str] = None
        self._preset_buttons: Dict[str, QPushButton] = {}
        self._extra_checkboxes: Dict[str, QCheckBox] = {}
        self._show_extra_options = True
        self._custom_edit_mode = False

        # Outer layout with tab widget
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(
            f"QTabWidget::pane {{ border: none; background: {COLORS['bg_darkest']}; }}"
            f"QTabBar::tab {{ background: {COLORS['bg_dark']}; color: {COLORS['text_dim']}; "
            f"border: none; border-bottom: 2px solid transparent; "
            f"padding: 8px 12px; font-size: 11px; font-weight: 600; "
            f"min-width: 60px; }}"
            f"QTabBar::tab:selected {{ color: {COLORS['text_primary']}; "
            f"border-bottom: 2px solid {COLORS['accent']}; "
            f"background: {COLORS['bg_darkest']}; }}"
            f"QTabBar::tab:hover {{ color: {COLORS['text_secondary']}; "
            f"background: {COLORS['bg_hover']}; }}"
        )

        self._tabs.addTab(self._build_model_tab(), "🔧 Model")
        self._tabs.addTab(self._build_caption_tab(), "📝 Caption")
        self._tabs.addTab(self._build_generate_tab(), "⚡ Generate")

        outer_layout.addWidget(self._tabs)

        # Finalize training mode visibility after all widgets are created
        self._update_training_mode_ui()

    # ─── Tab Builder Methods ──────────────────────────────

    def _build_model_tab(self) -> QWidget:
        """Build the 🔧 Model tab: model selection, load/unload, status."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"background: {COLORS['bg_darkest']}; border: none;")

        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(6)

        # ─── CAPTIONING MODEL ─────────────────────────────
        layout.addWidget(self._section_header("CAPTIONING MODEL"))

        model_row = QHBoxLayout()
        model_row.setSpacing(6)

        self.model_combo = QComboBox()
        self.model_combo.setStyleSheet(
            f"QComboBox {{ background: {COLORS['bg_input']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border_light']}; border-radius: 4px; "
            f"padding: 4px 8px; font-size: 11px; min-height: 28px; }}"
            f"QComboBox:hover {{ border-color: {COLORS['accent']}; }}"
            f"QComboBox QAbstractItemView {{ background: {COLORS['bg_dark']}; "
            f"color: {COLORS['text_primary']}; selection-background-color: {COLORS['accent']}; "
            f"selection-color: #ffffff; border: 1px solid {COLORS['border']}; }}"
        )
        model_row.addWidget(self.model_combo, 1)

        self._download_btn = QPushButton()
        self._download_btn.setFixedSize(32, 32)
        self._download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._download_btn.setToolTip("Download this model from HuggingFace")
        self._download_btn.setIcon(self._create_download_icon(COLORS['accent_text']))
        self._download_btn.setIconSize(QSize(18, 18))
        self._download_btn.setStyleSheet(
            f"QPushButton {{ background: {COLORS['bg_hover']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {COLORS['accent']}; border-color: {COLORS['accent']}; }}"
        )
        self._download_btn.clicked.connect(self._on_download_clicked)
        model_row.addWidget(self._download_btn)

        layout.addLayout(model_row)

        # Model action buttons row (Load + Unload side by side)
        self._model_is_loaded = False
        model_btn_row = QHBoxLayout()
        model_btn_row.setSpacing(6)

        self.load_model_btn = QPushButton("▶  Load Model")
        self.load_model_btn.setFixedHeight(36)
        self.load_model_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.load_model_btn.setStyleSheet(
            f"QPushButton {{ background: {COLORS['accent']}; color: #ffffff; "
            f"border: none; border-radius: 6px; font-size: 12px; font-weight: 600; "
            f"padding: 0 12px; }}"
            f"QPushButton:hover {{ background: {COLORS['accent_hover']}; }}"
            f"QPushButton:disabled {{ background: {COLORS['bg_hover']}; color: {COLORS['text_dim']}; }}"
        )
        self.load_model_btn.clicked.connect(self.load_model_requested.emit)
        model_btn_row.addWidget(self.load_model_btn, 1)

        self.unload_model_btn = QPushButton("⏹  Unload")
        self.unload_model_btn.setFixedHeight(36)
        self.unload_model_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.unload_model_btn.setStyleSheet(
            f"QPushButton {{ background: {COLORS['bg_dark']}; color: {COLORS['text_secondary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; "
            f"font-size: 12px; font-weight: 600; padding: 0 12px; }}"
            f"QPushButton:hover {{ background: {COLORS['error']}; color: #ffffff; "
            f"border-color: {COLORS['error']}; }}"
            f"QPushButton:disabled {{ background: {COLORS['bg_hover']}; color: {COLORS['text_dim']}; "
            f"border-color: {COLORS['border']}; }}"
        )
        self.unload_model_btn.setEnabled(False)
        self.unload_model_btn.clicked.connect(self.unload_model_requested.emit)
        model_btn_row.addWidget(self.unload_model_btn)

        layout.addLayout(model_btn_row)

        # Loading status indicator
        self._model_loading_label = QLabel("")
        self._model_loading_label.setWordWrap(True)
        self._model_loading_label.setStyleSheet(
            f"color: {COLORS['accent_text']}; font-size: 10px; font-style: italic; "
            f"padding: 2px 0;"
        )
        self._model_loading_label.setVisible(False)
        layout.addWidget(self._model_loading_label)

        layout.addWidget(self._separator())

        # ─── GPU SELECTION ────────────────────────────────
        layout.addWidget(self._section_header("GPU DEVICE"))

        self.gpu_combo = QComboBox()
        self.gpu_combo.addItem("Auto (GPU 0)")
        self.gpu_combo.setStyleSheet(
            f"QComboBox {{ background: {COLORS['bg_input']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border_light']}; border-radius: 4px; "
            f"padding: 4px 8px; font-size: 11px; min-height: 28px; }}"
            f"QComboBox:hover {{ border-color: {COLORS['accent']}; }}"
            f"QComboBox QAbstractItemView {{ background: {COLORS['bg_dark']}; "
            f"color: {COLORS['text_primary']}; selection-background-color: {COLORS['accent']}; "
            f"selection-color: #ffffff; border: 1px solid {COLORS['border']}; }}"
        )
        self.gpu_combo.setToolTip("Select which GPU to use for model inference")
        layout.addWidget(self.gpu_combo)

        gpu_hint = QLabel("Choose the GPU for model offloading. Reload required after changing.")
        gpu_hint.setWordWrap(True)
        gpu_hint.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")
        layout.addWidget(gpu_hint)

        layout.addWidget(self._separator())

        # ─── MODEL STATUS INFO BOX ───────────────────────
        self.status_frame = QFrame()
        self.status_frame.setProperty("class", "model-status")
        status_layout = QVBoxLayout(self.status_frame)
        status_layout.setContentsMargins(12, 10, 12, 10)
        status_layout.setSpacing(4)

        status_header = QHBoxLayout()
        info_icon = QLabel("ℹ")
        info_icon.setStyleSheet(f"color: {COLORS['accent_text']}; font-size: 13px;")
        status_header.addWidget(info_icon)
        status_title = QLabel("Model Status")
        status_title.setProperty("class", "info-label")
        status_header.addWidget(status_title)
        status_header.addStretch()
        status_layout.addLayout(status_header)

        self.status_text = QLabel("Not loaded")
        self.status_text.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")
        self.status_text.setWordWrap(True)
        status_layout.addWidget(self.status_text)

        self.inference_time_label = QLabel("")
        self.inference_time_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        self.inference_time_label.setVisible(False)
        status_layout.addWidget(self.inference_time_label)

        layout.addWidget(self.status_frame)

        layout.addStretch()
        scroll.setWidget(scroll_widget)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        return tab

    def _build_caption_tab(self) -> QWidget:
        """Build the 📝 Caption tab: presets, training mode, output mode, extra options."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"background: {COLORS['bg_darkest']}; border: none;")

        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(6)

        # ─── TARGET ARCHITECTURE ──────────────────────────
        layout.addWidget(self._section_header("TARGET ARCHITECTURE"))

        preset_grid = QGridLayout()
        preset_grid.setSpacing(6)
        for i, preset in enumerate(TARGET_PRESETS):
            btn = QPushButton(f"{preset['icon']}\n{preset['name']}")
            btn.setProperty("class", "preset-button")
            btn.setFixedHeight(52)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, p=preset: self._apply_preset(p))
            row, col = divmod(i, 2)
            preset_grid.addWidget(btn, row, col)
            self._preset_buttons[preset["id"]] = btn
        layout.addLayout(preset_grid)

        layout.addWidget(self._separator())

        # ─── TRAINING MODE ────────────────────────────────
        layout.addWidget(self._section_header("TRAINING MODE"))

        training_desc = QLabel(
            "Select what you're training. General captions everything. "
            "Other modes let you exclude elements the model should learn implicitly."
        )
        training_desc.setWordWrap(True)
        training_desc.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: 10px; margin-bottom: 4px;"
        )
        layout.addWidget(training_desc)

        self._training_mode = "general"
        self._training_mode_buttons: Dict[str, QPushButton] = {}

        training_grid = QGridLayout()
        training_grid.setSpacing(4)
        _TRAINING_MODES = [
            ("general", "📝 General"),
            ("style", "🎨 Style"),
            ("character", "👤 Character"),
            ("concept", "💡 Concept"),
        ]
        for i, (mode_id, mode_label) in enumerate(_TRAINING_MODES):
            btn = QPushButton(mode_label)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if mode_id == "general":
                btn.setProperty("class", "preset-button-active")
            else:
                btn.setProperty("class", "preset-button")
            btn.clicked.connect(lambda checked, m=mode_id: self._set_training_mode(m))
            row, col = divmod(i, 2)
            training_grid.addWidget(btn, row, col)
            self._training_mode_buttons[mode_id] = btn
        layout.addLayout(training_grid)

        # Trigger word
        self._trigger_word_label = QLabel("Trigger Word")
        self._trigger_word_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; margin-top: 4px;")
        self._trigger_word_label.setToolTip("Prepended to every caption (e.g. ohwx_style, sks_person)")
        layout.addWidget(self._trigger_word_label)

        self.trigger_word_input = QLineEdit()
        self.trigger_word_input.setPlaceholderText("e.g. ohwx_style")
        self.trigger_word_input.setFixedHeight(30)
        self.trigger_word_input.setStyleSheet(
            f"background-color: {COLORS['bg_input']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border_light']}; border-radius: 4px; "
            f"padding: 4px 8px; font-size: 12px;"
        )
        self.trigger_word_input.textChanged.connect(lambda: self.settings_changed.emit())
        layout.addWidget(self.trigger_word_input)

        # Exclusion text area
        self._exclusion_label = QLabel("Elements to Exclude from Captions")
        self._exclusion_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; margin-top: 4px;")
        layout.addWidget(self._exclusion_label)

        self._exclusion_hint = QLabel("")
        self._exclusion_hint.setWordWrap(True)
        self._exclusion_hint.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: 10px;"
        )
        layout.addWidget(self._exclusion_hint)

        self.exclusion_text = QTextEdit()
        self.exclusion_text.setPlaceholderText(
            "Describe elements to leave out of captions...\n"
            "e.g. abstract symmetrical block shapes, eroded edges, rough geometric textures"
        )
        self.exclusion_text.setMaximumHeight(80)
        self.exclusion_text.setAcceptRichText(False)
        self.exclusion_text.setStyleSheet(
            f"background-color: {COLORS['bg_input']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border_light']}; border-radius: 4px; "
            f"padding: 4px 8px; font-size: 11px;"
        )
        self.exclusion_text.textChanged.connect(lambda: self._refresh_prompt_preview())
        layout.addWidget(self.exclusion_text)

        layout.addWidget(self._separator())

        # ─── OUTPUT MODE ──────────────────────────────────
        layout.addWidget(self._section_header("OUTPUT MODE"))

        mode_row = QHBoxLayout()
        mode_row.setSpacing(4)

        self._output_mode = "caption"
        self._output_mode_buttons: Dict[str, QPushButton] = {}

        for mode_id, label, icon in [("caption", "Caption", "📝"), ("keywords", "Keywords", "🏷")]:
            btn = QPushButton(f"{icon}  {label}")
            btn.setCheckable(True)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background: {COLORS['bg_hover']}; color: {COLORS['text_secondary']}; "
                f"border: 1px solid {COLORS['border']}; border-radius: 6px; "
                f"font-size: 11px; font-weight: 600; padding: 0 10px; }}"
                f"QPushButton:checked {{ background: {COLORS['accent']}; color: #ffffff; "
                f"border-color: {COLORS['accent']}; }}"
            )
            btn.clicked.connect(lambda checked, m=mode_id: self._set_output_mode(m))
            mode_row.addWidget(btn)
            self._output_mode_buttons[mode_id] = btn

        self._output_mode_buttons["caption"].setChecked(True)
        layout.addLayout(mode_row)

        # ─── CAPTION LENGTH ──────────────────────────────
        self._caption_length_label = self._section_header("CAPTION LENGTH")
        layout.addWidget(self._caption_length_label)

        self.caption_length_combo = QComboBox()
        self.caption_length_combo.addItems(CAPTION_LENGTHS.keys())
        self.caption_length_combo.setCurrentText("Medium")
        self.caption_length_combo.currentTextChanged.connect(self._on_caption_length_changed)
        layout.addWidget(self.caption_length_combo)

        # ─── KEYWORD COUNT ───────────────────────────────
        self._keyword_count_label = self._section_header("KEYWORD COUNT")
        layout.addWidget(self._keyword_count_label)

        self.keyword_count_combo = QComboBox()
        self.keyword_count_combo.addItems(KEYWORD_COUNTS.keys())
        self.keyword_count_combo.setCurrentText("Moderate (10-20)")
        self.keyword_count_combo.currentTextChanged.connect(lambda: self._refresh_prompt_preview())
        layout.addWidget(self.keyword_count_combo)

        self._keyword_count_label.setVisible(False)
        self.keyword_count_combo.setVisible(False)

        layout.addWidget(self._separator())

        # ─── EXTRA OPTIONS ────────────────────────────────
        extra_toggle_row = QHBoxLayout()
        self.extra_options_toggle = QCheckBox("Extra Options")
        self.extra_options_toggle.setChecked(True)
        self.extra_options_toggle.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {COLORS['text_secondary']};"
        )
        self.extra_options_toggle.toggled.connect(self._toggle_extra_options)
        extra_toggle_row.addWidget(self.extra_options_toggle)
        extra_toggle_row.addStretch()
        self.extra_chevron = QLabel("▼")
        self.extra_chevron.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")
        extra_toggle_row.addWidget(self.extra_chevron)
        layout.addLayout(extra_toggle_row)

        self.extra_container = QFrame()
        self.extra_container.setProperty("class", "extra-options-container")
        extra_inner_layout = QVBoxLayout(self.extra_container)
        extra_inner_layout.setContentsMargins(0, 0, 0, 0)
        extra_inner_layout.setSpacing(0)

        extra_scroll = QScrollArea()
        extra_scroll.setWidgetResizable(True)
        extra_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        extra_scroll.setFixedHeight(240)
        extra_scroll.setStyleSheet("border: none; background: transparent;")

        extra_scroll_widget = QWidget()
        extra_opts_layout = QVBoxLayout(extra_scroll_widget)
        extra_opts_layout.setContentsMargins(8, 8, 8, 8)
        extra_opts_layout.setSpacing(4)

        for key, short_label, full_text in EXTRA_OPTIONS:
            cb = QCheckBox(short_label)
            cb.setToolTip(full_text)
            cb.toggled.connect(self._on_extra_option_toggled)
            extra_opts_layout.addWidget(cb)
            self._extra_checkboxes[key] = cb

        extra_opts_layout.addStretch()
        extra_scroll.setWidget(extra_scroll_widget)
        extra_inner_layout.addWidget(extra_scroll)
        layout.addWidget(self.extra_container)

        layout.addStretch()
        scroll.setWidget(scroll_widget)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        return tab

    def _build_generate_tab(self) -> QWidget:
        """Build the ⚡ Generate tab: parameters, formatting, batch processing."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"background: {COLORS['bg_darkest']}; border: none;")

        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(6)

        # ─── PARAMETERS ──────────────────────────────────
        layout.addWidget(self._section_header("PARAMETERS"))

        # Max Tokens
        tok_row = QHBoxLayout()
        tok_lbl = QLabel("Max Tokens")
        tok_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        tok_row.addWidget(tok_lbl)
        tok_row.addStretch()
        self.max_tokens_value = QLabel("256")
        self.max_tokens_value.setMinimumWidth(30)
        self.max_tokens_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.max_tokens_value.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-weight: 600; font-size: 11px; "
            f"font-family: 'Consolas', monospace;"
        )
        tok_row.addWidget(self.max_tokens_value)
        layout.addLayout(tok_row)

        self.max_tokens_slider = QSlider(Qt.Orientation.Horizontal)
        self.max_tokens_slider.setRange(16, 1024)
        self.max_tokens_slider.setValue(256)
        self.max_tokens_slider.setSingleStep(16)
        self.max_tokens_slider.setPageStep(64)
        self.max_tokens_slider.valueChanged.connect(
            lambda v: self.max_tokens_value.setText(str(v))
        )
        self.max_tokens_slider.valueChanged.connect(lambda: self.settings_changed.emit())
        layout.addWidget(self.max_tokens_slider)

        layout.addSpacing(4)

        # Temperature
        temp_row = QHBoxLayout()
        temp_lbl = QLabel("Temperature")
        temp_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        temp_row.addWidget(temp_lbl)
        temp_row.addStretch()
        self.temp_value = QLabel("0.6")
        self.temp_value.setMinimumWidth(30)
        self.temp_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.temp_value.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-weight: 600; font-size: 11px; "
            f"font-family: 'Consolas', monospace;"
        )
        temp_row.addWidget(self.temp_value)
        layout.addLayout(temp_row)

        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(1, 20)
        self.temp_slider.setValue(6)
        self.temp_slider.setSingleStep(1)
        self.temp_slider.valueChanged.connect(
            lambda v: self.temp_value.setText(f"{v / 10:.1f}")
        )
        self.temp_slider.valueChanged.connect(lambda: self.settings_changed.emit())
        layout.addWidget(self.temp_slider)

        layout.addWidget(self._separator())

        # ─── FORMATTING ──────────────────────────────────
        layout.addWidget(self._section_header("FORMATTING"))

        prompt_header_row = QHBoxLayout()
        fmt_lbl = QLabel("Prompt Template")
        fmt_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        prompt_header_row.addWidget(fmt_lbl)
        prompt_header_row.addStretch()

        self.custom_edit_btn = QPushButton("✏ Edit")
        self.custom_edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.custom_edit_btn.setFixedHeight(20)
        self.custom_edit_btn.setStyleSheet(
            f"font-size: 10px; padding: 2px 8px; border: 1px solid {COLORS['border']}; "
            f"border-radius: 3px; background: transparent; color: {COLORS['text_secondary']};"
        )
        self.custom_edit_btn.setToolTip("Switch to custom edit mode — type your own prompt")
        self.custom_edit_btn.clicked.connect(self._toggle_custom_edit)
        prompt_header_row.addWidget(self.custom_edit_btn)
        layout.addLayout(prompt_header_row)

        self.prompt_text = QTextEdit()
        self.prompt_text.setProperty("class", "prompt-template")
        self.prompt_text.setPlaceholderText("Enter prompt template...")
        self.prompt_text.setMaximumHeight(140)
        self.prompt_text.setAcceptRichText(False)
        self.prompt_text.setPlainText(TARGET_PRESETS[0]["template"])
        layout.addWidget(self.prompt_text)

        pfx_lbl = QLabel("Fixed Prefix")
        pfx_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        layout.addWidget(pfx_lbl)
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("e.g. sks style,")
        self.prefix_input.setFixedHeight(32)
        self.prefix_input.setStyleSheet(
            f"background-color: {COLORS['bg_input']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border_light']}; border-radius: 4px; "
            f"padding: 4px 8px; font-size: 12px;"
        )
        layout.addWidget(self.prefix_input)

        sfx_lbl = QLabel("Fixed Suffix")
        sfx_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        layout.addWidget(sfx_lbl)
        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText("e.g. , masterpiece, high quality")
        self.suffix_input.setFixedHeight(32)
        self.suffix_input.setStyleSheet(
            f"background-color: {COLORS['bg_input']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border_light']}; border-radius: 4px; "
            f"padding: 4px 8px; font-size: 12px;"
        )
        layout.addWidget(self.suffix_input)

        layout.addWidget(self._separator())

        # ─── BATCH PROCESSING ─────────────────────────────
        batch_header = QLabel("BATCH PROCESSING")
        batch_header.setProperty("class", "section-header")
        layout.addWidget(batch_header)

        batch_desc = QLabel("Caption all imported images at once using current settings.")
        batch_desc.setWordWrap(True)
        batch_desc.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: 10px; margin-bottom: 4px;"
        )
        layout.addWidget(batch_desc)

        self.auto_save_cb = QCheckBox("Auto-save .txt sidecar for each image")
        self.auto_save_cb.setChecked(True)
        self.auto_save_cb.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 11px; padding: 2px 0;"
        )
        self.auto_save_cb.setToolTip("Automatically write a .txt caption file next to each image during batch")
        layout.addWidget(self.auto_save_cb)

        self.skip_existing_cb = QCheckBox("Skip images with existing .txt")
        self.skip_existing_cb.setChecked(True)
        self.skip_existing_cb.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 11px; padding: 2px 0;"
        )
        self.skip_existing_cb.setToolTip("Skip images that already have a .txt caption sidecar file")
        layout.addWidget(self.skip_existing_cb)

        layout.addSpacing(4)

        self.batch_btn = QPushButton("Batch Caption All")
        self.batch_btn.setProperty("class", "accent-button")
        self.batch_btn.setFixedHeight(40)
        self.batch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.batch_btn.setToolTip("Generate captions for every imported image using current settings")
        self.batch_btn.clicked.connect(self.batch_caption_requested.emit)
        layout.addWidget(self.batch_btn)

        # Cancel button
        self.cancel_btn = QPushButton("✕  Cancel")
        self.cancel_btn.setFixedHeight(36)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setToolTip("Cancel current generation, batch, or download")
        self.cancel_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {COLORS['error']}; "
            f"border: 1px solid {COLORS['error']}; border-radius: 6px; "
            f"font-size: 12px; font-weight: 600; }} "
            f"QPushButton:hover {{ background: {COLORS['error']}; color: #ffffff; }}"
        )
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)
        self.cancel_btn.setVisible(False)
        layout.addWidget(self.cancel_btn)

        self.export_btn = QPushButton("#  Export to .txt Files")
        self.export_btn.setProperty("class", "secondary-button")
        self.export_btn.setFixedHeight(40)
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self.export_requested.emit)
        layout.addWidget(self.export_btn)

        layout.addStretch()
        scroll.setWidget(scroll_widget)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        return tab

    # ─── Internal Helpers ─────────────────────────────────

    @staticmethod
    def _create_download_icon(color_hex: str, size: int = 18) -> QIcon:
        """Paint a download arrow icon (↓ with tray) that renders on all platforms."""
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

        p = QPainter(pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(QColor(color_hex))
        pen.setWidthF(1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)

        cx = size / 2  # center x
        # Arrow shaft: vertical line from top to ~65% down
        shaft_top = size * 0.15
        shaft_bot = size * 0.62
        p.drawLine(int(cx), int(shaft_top), int(cx), int(shaft_bot))

        # Arrowhead: two lines from shaft bottom forming a V
        head_w = size * 0.25  # half-width of arrowhead
        p.drawLine(int(cx), int(shaft_bot), int(cx - head_w), int(shaft_bot - head_w))
        p.drawLine(int(cx), int(shaft_bot), int(cx + head_w), int(shaft_bot - head_w))

        # Tray: horizontal line with small vertical edges at bottom
        tray_y = size * 0.82
        tray_left = size * 0.2
        tray_right = size * 0.8
        tray_edge_h = size * 0.12
        # Left edge
        p.drawLine(int(tray_left), int(tray_y - tray_edge_h), int(tray_left), int(tray_y))
        # Bottom line
        p.drawLine(int(tray_left), int(tray_y), int(tray_right), int(tray_y))
        # Right edge
        p.drawLine(int(tray_right), int(tray_y - tray_edge_h), int(tray_right), int(tray_y))

        p.end()
        return QIcon(pixmap)

    def _section_header(self, text: str) -> QLabel:
        """Create a styled section header label."""
        label = QLabel(text)
        label.setProperty("class", "section-header")
        return label

    def _separator(self) -> QFrame:
        """Create a horizontal separator line."""
        line = QFrame()
        line.setProperty("class", "h-separator")
        line.setFixedHeight(1)
        return line

    def _apply_preset(self, preset: dict):
        """Apply a target architecture preset (toggle off if already active)."""
        # Toggle off if clicking the already-active preset
        if self._active_preset_id == preset["id"]:
            self._deselect_preset()
            return

        old_id = self._active_preset_id
        self._active_preset_id = preset["id"]

        # Update button styles
        if old_id and old_id in self._preset_buttons:
            self._preset_buttons[old_id].setProperty("class", "preset-button")
            self._preset_buttons[old_id].style().unpolish(self._preset_buttons[old_id])
            self._preset_buttons[old_id].style().polish(self._preset_buttons[old_id])

        btn = self._preset_buttons[preset["id"]]
        btn.setProperty("class", "preset-button-active")
        btn.style().unpolish(btn)
        btn.style().polish(btn)

        # Apply prefix, suffix
        self.prefix_input.setText(preset["prefix"])
        self.suffix_input.setText(preset["suffix"])

        # Reset custom edit mode when switching presets
        self._custom_edit_mode = False
        self.custom_edit_btn.setText("✏ Edit")
        self.custom_edit_btn.setToolTip("Switch to custom edit mode — type your own prompt")
        self.custom_edit_btn.setStyleSheet(
            f"font-size: 10px; padding: 2px 8px; border: 1px solid {COLORS['border']}; "
            f"border-radius: 3px; background: transparent; color: {COLORS['text_secondary']};"
        )

        # Enable/disable checkboxes based on preset's supported options
        supported = preset.get("supported_options", _ALL_OPTION_KEYS)

        for key, cb in self._extra_checkboxes.items():
            is_supported = key in supported
            cb.setEnabled(is_supported)
            if not is_supported:
                cb.setChecked(False)  # Uncheck unsupported options

        # Filter caption length dropdown to only meaningful options for this preset
        allowed = preset.get("allowed_lengths", _ALL_LENGTH_KEYS)
        prev_selection = self.caption_length_combo.currentText()
        self.caption_length_combo.blockSignals(True)
        self.caption_length_combo.clear()
        self.caption_length_combo.addItems(allowed)
        if prev_selection in allowed:
            self.caption_length_combo.setCurrentText(prev_selection)
        self.caption_length_combo.blockSignals(False)

        # Lock prompt box (auto-generated while preset is active)
        self.prompt_text.setReadOnly(True)
        self.prompt_text.setStyleSheet(
            f"background: {COLORS['bg_dark']}; color: {COLORS['text_secondary']};"
        )

        # Show live-built prompt in the template box
        self._refresh_prompt_preview()
        self.settings_changed.emit()

    def _set_training_mode(self, mode: str):
        """Switch training mode and update UI."""
        self._training_mode = mode

        # Update button styles
        for mid, btn in self._training_mode_buttons.items():
            if mid == mode:
                btn.setProperty("class", "preset-button-active")
            else:
                btn.setProperty("class", "preset-button")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self._update_training_mode_ui()
        self._refresh_prompt_preview()
        self.settings_changed.emit()

    def _update_training_mode_ui(self):
        """Show/hide training-mode-specific widgets based on current mode."""
        is_training = self._training_mode != "general"
        self._exclusion_label.setVisible(is_training)
        self._exclusion_hint.setVisible(is_training)
        self.exclusion_text.setVisible(is_training)

        hints = {
            "style": "Describe the visual style elements the model should learn "
                     "(e.g. texture, artistic treatment, medium). These will NOT appear in captions.",
            "character": "Describe the character's fixed physical traits "
                         "(e.g. face shape, eye color, body type). These will NOT appear in captions.",
            "concept": "Describe the concept or visual motif being trained "
                        "(e.g. a composition technique, effect). These will NOT appear in captions.",
        }
        self._exclusion_hint.setText(hints.get(self._training_mode, ""))

    def _build_exclusion_block(self) -> str:
        """Build the exclusion instruction string for the current training mode."""
        if self._training_mode == "general":
            return ""

        exclusion_text = self.exclusion_text.toPlainText().strip()
        if not exclusion_text:
            return ""

        mode_context = {
            "style": (
                "The user is training a STYLE LoRA. The following visual style elements "
                "are what the model should learn implicitly — do NOT describe or mention "
                "them in your caption. Focus on describing everything ELSE in the image "
                "(subject, scene, composition, colors, lighting setup, mood)."
            ),
            "character": (
                "The user is training a CHARACTER LoRA. The following physical traits "
                "belong to the character being trained — do NOT describe or mention "
                "them in your caption. Focus on describing everything ELSE "
                "(pose, action, clothing, expression, setting, background, lighting)."
            ),
            "concept": (
                "The user is training a CONCEPT LoRA. The following concept-specific "
                "elements are what the model should learn implicitly — do NOT describe "
                "or mention them in your caption. Focus on describing everything ELSE "
                "in the image."
            ),
        }

        context = mode_context.get(self._training_mode, "")
        return f" {context} Elements to EXCLUDE: {exclusion_text}."

    def _toggle_extra_options(self, visible: bool):
        """Toggle extra options visibility."""
        self._show_extra_options = visible
        self.extra_container.setVisible(visible)
        self.extra_chevron.setText("▼" if visible else "▶")

    def _deselect_preset(self):
        """Deselect the current preset, re-enabling all options and restoring editable prompt."""
        if self._active_preset_id and self._active_preset_id in self._preset_buttons:
            btn = self._preset_buttons[self._active_preset_id]
            btn.setProperty("class", "preset-button")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._active_preset_id = None

        # Re-enable all checkboxes and restore full caption length dropdown
        for cb in self._extra_checkboxes.values():
            cb.setEnabled(True)
        prev_selection = self.caption_length_combo.currentText()
        self.caption_length_combo.blockSignals(True)
        self.caption_length_combo.clear()
        self.caption_length_combo.addItems(_ALL_LENGTH_KEYS)
        if prev_selection in _ALL_LENGTH_KEYS:
            self.caption_length_combo.setCurrentText(prev_selection)
        self.caption_length_combo.blockSignals(False)

        # Restore editable prompt
        self.prompt_text.setReadOnly(False)
        self.prompt_text.setStyleSheet("")

        # Reset custom edit mode
        self._custom_edit_mode = False
        self.custom_edit_btn.setText("✏ Edit")
        self.custom_edit_btn.setToolTip("Switch to custom edit mode — type your own prompt")
        self.custom_edit_btn.setStyleSheet(
            f"font-size: 10px; padding: 2px 8px; border: 1px solid {COLORS['border']}; "
            f"border-radius: 3px; background: transparent; color: {COLORS['text_secondary']};"
        )

        self.settings_changed.emit()

    def _on_download_clicked(self):
        """Emit download request for the currently selected model."""
        self.download_model_requested.emit(self.model_combo.currentText())

    def _on_extra_option_toggled(self, _checked: bool):
        """Slot for any extra-option checkbox toggle."""
        self._refresh_prompt_preview()
        self.settings_changed.emit()

    def _on_caption_length_changed(self, _text: str):
        """Slot for caption-length combo change."""
        self._refresh_prompt_preview()
        self.settings_changed.emit()

    def _toggle_custom_edit(self):
        """Toggle between auto-generated preview and user-editable custom prompt mode."""
        self._custom_edit_mode = not self._custom_edit_mode

        if self._custom_edit_mode:
            # Switch to editable mode — user can type their own prompt
            self.custom_edit_btn.setText("↻ Reset")
            self.custom_edit_btn.setToolTip("Return to auto-generated prompt from preset")
            self.custom_edit_btn.setStyleSheet(
                f"font-size: 10px; padding: 2px 8px; border: 1px solid {COLORS['accent']}; "
                f"border-radius: 3px; background: {COLORS['accent']}; color: {COLORS['bg_darkest']};"
            )
            self.prompt_text.setReadOnly(False)
            self.prompt_text.setStyleSheet("")  # Reset to default editable style
            self.prompt_text.setFocus()
        else:
            # Switch back to auto-generated mode — restore preset preview
            self.custom_edit_btn.setText("✏ Edit")
            self.custom_edit_btn.setToolTip("Switch to custom edit mode — type your own prompt")
            self.custom_edit_btn.setStyleSheet(
                f"font-size: 10px; padding: 2px 8px; border: 1px solid {COLORS['border']}; "
                f"border-radius: 3px; background: transparent; color: {COLORS['text_secondary']};"
            )
            if self._active_preset_id:
                self.prompt_text.setReadOnly(True)
                self.prompt_text.setStyleSheet(
                    f"background: {COLORS['bg_dark']}; color: {COLORS['text_secondary']};"
                )
            self._refresh_prompt_preview()

    def _set_output_mode(self, mode: str):
        """Switch between caption and keywords output mode."""
        self._output_mode = mode
        for m, btn in self._output_mode_buttons.items():
            btn.setChecked(m == mode)

        is_caption = (mode == "caption")
        # Toggle caption-length vs keyword-count visibility
        self._caption_length_label.setVisible(is_caption)
        self.caption_length_combo.setVisible(is_caption)
        self._keyword_count_label.setVisible(not is_caption)
        self.keyword_count_combo.setVisible(not is_caption)

        self._refresh_prompt_preview()
        self.settings_changed.emit()

    def get_output_mode(self) -> str:
        """Return the current output mode: 'caption' or 'keywords'."""
        return self._output_mode

    def _refresh_prompt_preview(self):
        """Update the prompt template box to show the actual prompt that will be sent.

        Only auto-updates when a preset is active and the user hasn't
        switched to custom-edit mode.  When no preset is selected (or
        custom-edit is on) the user's manual text IS the prompt input
        and should not be overwritten.
        """
        if (self._active_preset_id or self._output_mode == "keywords") and not self._custom_edit_mode:
            built = self.get_prompt()
            self.prompt_text.blockSignals(True)
            self.prompt_text.setPlainText(built)
            self.prompt_text.blockSignals(False)

    # ─── Public Getters ───────────────────────────────────

    def get_prompt(self) -> str:
        """Build the full prompt using the active preset's model-specific builder.

        In keyword mode, uses the keyword prompt builder instead.
        When *custom edit mode* is on, the user's text in the prompt box
        is returned directly (no builder override).
        """
        # Custom edit mode — user typed their own prompt, return it as-is
        if self._custom_edit_mode:
            prompt = self.prompt_text.toPlainText().strip()
            prompt += self._build_exclusion_block()
            return prompt

        # Always gather extra options — even when the panel is collapsed
        extra_opts = self.get_extra_options()

        # Get the {name} value if referAsName is enabled
        name_value = ""
        if extra_opts.get("referAsName"):
            name_value = getattr(self, "_name_input_value", "") or "the subject"

        # ── Keyword mode — bypass preset builders entirely ──
        if self._output_mode == "keywords":
            count_key = self.keyword_count_combo.currentText()
            count_hint = KEYWORD_COUNTS.get(count_key, "")
            prompt = _build_keyword_prompt(extra_opts, name_value, count_hint)
            prompt += self._build_exclusion_block()
            return prompt

        # ── Caption mode — use preset builder ──
        length_key = self.caption_length_combo.currentText()
        length_instruction = CAPTION_LENGTHS.get(length_key, "")

        # Build the base prompt from the active preset's builder
        prompt = ""
        if self._active_preset_id:
            for preset in TARGET_PRESETS:
                if preset["id"] == self._active_preset_id:
                    builder = preset.get("prompt_builder")
                    if builder:
                        prompt = builder(length_instruction, extra_opts, name_value)
                    break

        # No preset selected or no builder — use generic fallback
        if not prompt:
            base_prompt = self.prompt_text.toPlainText().strip()
            prompt = _build_prompt_generic(length_instruction, extra_opts, name_value, base_prompt)

        # Append training-mode exclusion instructions
        prompt += self._build_exclusion_block()
        return prompt

    def get_prefix(self) -> str:
        """Return the effective prefix, including trigger word if set."""
        trigger = self.trigger_word_input.text().strip()
        prefix = self.prefix_input.text().strip()
        if trigger and prefix:
            return f"{trigger}, {prefix}"
        elif trigger:
            return f"{trigger},"
        return prefix

    def get_suffix(self) -> str:
        return self.suffix_input.text().strip()

    def get_training_mode(self) -> str:
        """Return the active training mode: general, style, character, or concept."""
        return self._training_mode

    def get_exclusion_text(self) -> str:
        """Return the raw exclusion text entered by the user."""
        return self.exclusion_text.toPlainText().strip()

    def get_temperature(self) -> float:
        return self.temp_slider.value() / 10.0

    def get_top_p(self) -> float:
        """Kept for backward compatibility; returns a sensible default."""
        return 0.9

    def get_max_tokens(self) -> int:
        return self.max_tokens_slider.value()

    def get_active_preset(self) -> Optional[str]:
        return self._active_preset_id

    def get_caption_length(self) -> str:
        return self.caption_length_combo.currentText()

    def get_extra_options(self) -> Dict[str, bool]:
        """Get the state of all extra option checkboxes."""
        return {key: cb.isChecked() for key, cb in self._extra_checkboxes.items()}

    def get_selected_gpu(self) -> int:
        """Return the 0-based GPU device index selected by the user."""
        return max(0, self.gpu_combo.currentIndex())

    # ─── Status Updates ───────────────────────────────────

    def set_model_status(self, status: str, detail: str = "", is_loaded: bool = False):
        """Update the model status display and button states."""
        self._model_is_loaded = is_loaded

        # Toggle button states
        self.load_model_btn.setEnabled(not is_loaded)
        self.unload_model_btn.setEnabled(is_loaded)
        self.model_combo.setEnabled(not is_loaded)
        self.gpu_combo.setEnabled(not is_loaded)

        # Update load button appearance based on state
        if is_loaded:
            self.load_model_btn.setText("✓  Loaded")
            self.load_model_btn.setStyleSheet(
                f"QPushButton {{ background: {COLORS['accent_dim']}; color: {COLORS['accent_text']}; "
                f"border: 1px solid {COLORS['accent']}; border-radius: 6px; "
                f"font-size: 12px; font-weight: 600; padding: 0 12px; }}"
            )
            self.status_text.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        else:
            self.load_model_btn.setText("▶  Load Model")
            self.load_model_btn.setStyleSheet(
                f"QPushButton {{ background: {COLORS['accent']}; color: #ffffff; "
                f"border: none; border-radius: 6px; font-size: 12px; font-weight: 600; "
                f"padding: 0 12px; }}"
                f"QPushButton:hover {{ background: {COLORS['accent_hover']}; }}"
                f"QPushButton:disabled {{ background: {COLORS['bg_hover']}; color: {COLORS['text_dim']}; }}"
            )
            self.status_text.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")

        # Hide loading indicator when reaching a final state
        self._model_loading_label.setVisible(False)

        self.status_text.setText(status)
        if detail:
            self.inference_time_label.setText(detail)
            self.inference_time_label.setVisible(True)
        else:
            self.inference_time_label.setVisible(False)

    def set_model_loading(self, message: str):
        """Show a loading indicator during model load/unload."""
        self._model_loading_label.setText(f"⏳ {message}")
        self._model_loading_label.setVisible(True)
        self.load_model_btn.setEnabled(False)
        self.unload_model_btn.setEnabled(False)
        self.model_combo.setEnabled(False)
        self._download_btn.setEnabled(False)

    def set_inference_time(self, seconds: float):
        """Update the inference time display."""
        self.inference_time_label.setText(f"Average inference time: ~{seconds:.1f}s per image")
        self.inference_time_label.setVisible(True)

    def set_batch_progress(self, current: int, total: int):
        """Update batch button text with progress."""
        if current < total:
            self.batch_btn.setText(f"  Processing {current}/{total}...")
            self.batch_btn.setEnabled(False)
        else:
            self.batch_btn.setText("⚡  Batch Caption All")
            self.batch_btn.setEnabled(True)

    def set_generating(self, is_generating: bool):
        """Toggle UI state during generation."""
        self.batch_btn.setEnabled(not is_generating)
        self.load_model_btn.setEnabled(not is_generating and not self._model_is_loaded)
        self.unload_model_btn.setEnabled(not is_generating and self._model_is_loaded)
        self._download_btn.setEnabled(not is_generating)
        # Show cancel button while generating
        self.cancel_btn.setVisible(is_generating)

    def set_download_in_progress(self, in_progress: bool):
        """Toggle cancel button visibility during model download."""
        self.cancel_btn.setVisible(in_progress)
        self._download_btn.setEnabled(not in_progress)
        self.load_model_btn.setEnabled(not in_progress and not self._model_is_loaded)
        self.unload_model_btn.setEnabled(not in_progress and self._model_is_loaded)
