"""Nothing / CMF model catalogue (SKU → capabilities).

SKU prefixes come from community reverse-engineering of Nothing X
(ear-web / Nothing serial strings). Unknown SKUs still speak the same
RFCOMM family; capabilities fall back to a conservative feature set.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Model:
    name: str
    base: str
    family: str
    colors: tuple[str, ...] = ()
    anc: bool = True
    adaptive_anc: bool = True
    eq_presets: bool = True
    custom_eq: bool = True
    advanced_eq: bool = True
    bass_enhance: bool = False
    in_ear: bool = True
    low_latency: bool = True
    gestures: bool = True
    ear_tip_fit: bool = False
    find_my: bool = True
    personalized_anc: bool = False
    listening_mode: bool = False  # CMF Buds / Buds Pro 2 style
    single_battery: bool = False  # one headset battery instead of L/R/case
    over_ear: bool = False
    protocol_version: bool = False  # send 0xC001 activation handshake
    rfcomm_channels: tuple[int, ...] = (15,)
    eq_family: str = "earbud"  # "earbud" (0xC01F) or "listening" (0xC050)
    spatial_audio: bool = False
    spatial_modes: tuple[str, ...] = ()
    personal_sound: bool = False  # Audiodo / Mimi toggle
    dual_connection: bool = False
    dual_reboot: bool = False
    gesture_profile: str = "earbud"  # "earbud" or "headphone"
    gesture_device: int = 2
    device_codecs: tuple[str, ...] = ()
    codec_zero: str = "sbc"
    custom_eq_peak_q: float = 0.66
    ring_form: str = "earbud"  # "earbud", "headphone" or "ear1"

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "base": self.base,
            "family": self.family,
            "features": {
                "anc": self.anc,
                "adaptive_anc": self.adaptive_anc,
                "eq_presets": self.eq_presets,
                "custom_eq": self.custom_eq,
                "advanced_eq": self.advanced_eq,
                "bass_enhance": self.bass_enhance,
                "in_ear": self.in_ear,
                "low_latency": self.low_latency,
                "gestures": self.gestures,
                "ear_tip_fit": self.ear_tip_fit,
                "find_my": self.find_my,
                "personalized_anc": self.personalized_anc,
                "listening_mode": self.listening_mode,
                "single_battery": self.single_battery,
                "over_ear": self.over_ear,
                "spatial_audio": self.spatial_audio,
                "spatial_modes": list(self.spatial_modes),
                "personal_sound": self.personal_sound,
                "dual_connection": self.dual_connection,
                "gesture_profile": self.gesture_profile,
                "eq_family": self.eq_family,
                "device_codecs": list(self.device_codecs),
            },
        }


# Conservative default: Ear (2) family protocol.
DEFAULT = Model(
    name="Nothing / CMF audio device",
    base="unknown",
    family="generic",
    ear_tip_fit=True,
)

MODELS_BY_BASE: dict[str, Model] = {
    "B181": Model(
        name="Nothing Ear (1)",
        base="B181",
        family="ear1",
        adaptive_anc=False,
        custom_eq=False,
        advanced_eq=False,
    ),
    "B157": Model(
        name="Nothing Ear (stick)",
        base="B157",
        family="stick",
        anc=True,
        adaptive_anc=False,
        ear_tip_fit=False,
    ),
    "B155": Model(
        name="Nothing Ear (2)",
        base="B155",
        family="ear2",
        personalized_anc=True,
        ear_tip_fit=True,
    ),
    "B171": Model(
        name="Nothing Ear",
        base="B171",
        family="ear",
        bass_enhance=True,
        ear_tip_fit=True,
    ),
    "B162": Model(
        name="Nothing Ear (a)",
        base="B162",
        family="ear-a",
        bass_enhance=True,
        ear_tip_fit=True,
    ),
    "B163": Model(
        name="CMF Buds Pro",
        base="B163",
        family="cmf-pro",
        ear_tip_fit=True,
    ),
    "B168": Model(
        name="CMF Buds",
        base="B168",
        family="cmf-buds",
        listening_mode=True,
        bass_enhance=True,
    ),
    "B172": Model(
        name="CMF Buds Pro 2",
        base="B172",
        family="cmf-pro2",
        listening_mode=True,
        bass_enhance=True,
        ear_tip_fit=True,
    ),
    "B164": Model(
        name="CMF Neckband Pro",
        base="B164",
        family="neckband",
        in_ear=False,
        ear_tip_fit=False,
        find_my=False,
    ),
    "B174": Model(
        name="Nothing Ear (open)",
        base="B174",
        family="open",
        anc=False,
        adaptive_anc=False,
        in_ear=False,
        ear_tip_fit=False,
    ),
    "B175": Model(
        name="CMF Headphone Pro",
        base="B175",
        family="forretress",
        adaptive_anc=True,
        advanced_eq=False,
        bass_enhance=False,
        in_ear=False,
        ear_tip_fit=False,
        single_battery=True,
        over_ear=True,
        protocol_version=True,
        rfcomm_channels=(28, 15),
        eq_family="listening",
        spatial_audio=True,
        spatial_modes=("off", "concert", "theatre"),
        personal_sound=True,
        dual_connection=True,
        gesture_profile="headphone",
        gesture_device=6,
        device_codecs=("aac", "ldac"),
        codec_zero="aac",
        custom_eq_peak_q=0.7,
        ring_form="headphone",
    ),
}

# Serial SKU fragment → model base. First two digits of many serials.
SKU_PREFIX_TO_BASE: dict[str, str] = {}
_SKU_TABLE = {
    "B181": ["01", "02", "03", "04", "06", "07", "08", "10"],
    "B157": ["14", "15", "16"],
    "B155": ["17", "18", "19", "27", "28", "29"],
    "B163": ["30", "31", "32", "33", "34", "35"],
    "B164": ["48", "49", "50", "51", "52", "53"],
    "B168": ["54", "55", "56", "57", "58", "59"],
    "B171": ["61", "62", "69", "70", "71", "74", "75"],
    "B162": ["63", "64", "65", "66", "67", "68", "72", "73"],
    "B172": ["76", "77", "78", "79", "80", "81", "82", "83"],
}
for _base, prefixes in _SKU_TABLE.items():
    for _p in prefixes:
        SKU_PREFIX_TO_BASE[_p] = _base


def model_from_serial(serial: str | None) -> Model:
    if not serial:
        return DEFAULT
    serial = serial.strip()
    if serial.startswith("B") and serial[:4] in MODELS_BY_BASE:
        return MODELS_BY_BASE[serial[:4]]
    prefix = ""
    for ch in serial:
        if ch.isdigit():
            prefix += ch
            if len(prefix) >= 2:
                break
        elif prefix:
            break
    base = SKU_PREFIX_TO_BASE.get(prefix[:2], "")
    if base in MODELS_BY_BASE:
        return MODELS_BY_BASE[base]
    # Ear (open) uses a long SKU.
    if serial.startswith("11200005"):
        return MODELS_BY_BASE["B174"]
    return DEFAULT


def model_from_name(name: str) -> Model:
    value = (name or "").lower()
    mapping = [
        ("cmf headphone pro", "B175"),
        ("cmf by nothing headphone", "B175"),
        ("cmf headphone", "B175"),
        ("ear (a)", "B162"),
        ("ear(a)", "B162"),
        ("ear (open)", "B174"),
        ("ear (stick)", "B157"),
        ("ear (1)", "B181"),
        ("ear (2)", "B155"),
        ("buds pro 2", "B172"),
        ("buds pro", "B163"),
        ("cmf buds", "B168"),
        ("neckband", "B164"),
        ("nothing ear", "B171"),
    ]
    for needle, base in mapping:
        if needle in value:
            return MODELS_BY_BASE[base]
    return DEFAULT
