import struct
import unittest

from eara.models import model_from_name, model_from_serial
from eara.protocol import (
    ANC_MODES,
    DIR_GET,
    DIR_RESPONSE,
    DIR_SET,
    FrameParser,
    build_custom_eq_payload,
    build_frame,
    crc16_arc,
    parse_anc,
    parse_battery,
    parse_custom_eq,
    parse_device_codec,
    parse_dual_devices,
    parse_dual_enabled,
    parse_ear_tip,
    parse_eq,
    parse_gestures,
    parse_headphone_gestures,
    parse_listening,
    parse_personal_sound,
    parse_serial,
    parse_spatial,
    parse_fast_pair_battery,
    merge_battery_cache,
    MAX_FRAME_BUFFER,
)


class ProtocolTests(unittest.TestCase):
    def test_crc_matches_captured_transparency(self):
        frame = build_frame(0x0F, DIR_SET, bytes([1, 7, 0]), seq=0xCB)
        self.assertEqual(frame.hex(), "5560010ff00300cb010700c5af")

    def test_crc_matches_captured_off(self):
        frame = build_frame(0x0F, DIR_SET, bytes([1, 5, 0]), seq=0xCD)
        self.assertEqual(frame.hex(), "5560010ff00300cd010500c447")

    def test_all_anc_modes_have_valid_crc(self):
        for mode, wire in ANC_MODES.items():
            frame = build_frame(0x0F, DIR_SET, bytes([1, wire, 0]), seq=1)
            body, crc = frame[:-2], struct.unpack("<H", frame[-2:])[0]
            self.assertEqual(crc16_arc(body), crc, mode)

    def test_parser_roundtrip(self):
        frame = build_frame(0x1E, 0xC0, b"\x03", seq=12)
        parser = FrameParser()
        parser.feed(frame)
        frames = list(parser.frames())
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].command, 0x1E)
        self.assertEqual(frames[0].payload, b"\x03")

    def test_parse_battery(self):
        payload = bytes([3, 2, 80, 3, 75, 4, 50 | 0x80])
        parsed = parse_battery(payload)
        self.assertEqual(parsed["left"]["level"], 80)
        self.assertEqual(parsed["right"]["level"], 75)
        self.assertEqual(parsed["case"]["level"], 50)
        self.assertTrue(parsed["case"]["charging"])

    def test_parse_anc(self):
        self.assertEqual(parse_anc(bytes([1, 7, 0])), "transparency")
        self.assertEqual(parse_anc(bytes([1, 5, 0])), "off")

    def test_serial_sku_ear_a(self):
        payload = b"2,4,SH63xxxxxxxx\n"
        serial = parse_serial(payload)
        self.assertTrue(serial.startswith("SH"))
        self.assertEqual(model_from_serial("63ABC").base, "B162")
        self.assertTrue(model_from_serial("63ABC").bass_enhance)

    def test_model_from_bt_name(self):
        self.assertEqual(model_from_name("Nothing Ear (a)").base, "B162")
        self.assertEqual(model_from_name("CMF Buds Pro 2").base, "B172")

    def test_i18n_english_default(self):
        from eara.i18n import STRINGS, t, set_lang

        set_lang("en")
        self.assertEqual(t("connect"), "Connect")
        set_lang("uk")
        self.assertEqual(t("connect"), "Підключити")
        set_lang("en")
        self.assertIn("connect", STRINGS["en"])
        self.assertEqual(set(STRINGS["en"]), set(STRINGS["uk"]))

    def test_custom_eq_payload_length(self):
        payload = build_custom_eq_payload(2.0, 0.0, -1.0)
        self.assertGreater(len(payload), 40)
        parsed = parse_custom_eq(payload)
        self.assertEqual(len(parsed), 3)

    def test_parse_ear_tip(self):
        self.assertEqual(parse_ear_tip(bytes([0, 0])), {"left": "good", "right": "good"})
        self.assertEqual(parse_ear_tip(bytes([0, 1])), {"left": "good", "right": "poor"})
        self.assertEqual(parse_ear_tip(bytes([1, 0])), {"left": "poor", "right": "good"})
        with self.assertRaises(ValueError):
            parse_ear_tip(b"\x00")

    def test_merge_battery_cache(self):
        battery = {"left": {"level": 80, "charging": False, "available": True}}
        cache: dict = {"case": {"level": 55, "charging": False, "available": True}}
        merged, new_cache = merge_battery_cache(battery, cache)
        self.assertEqual(merged["case"]["level"], 55)
        self.assertTrue(merged["case"]["stale"])
        self.assertEqual(new_cache["left"]["level"], 80)

    def test_parse_gestures_offsets(self):
        payload = bytearray(36)
        payload[4] = 0x09
        payload[12] = 0x08
        payload[20] = 0x0A
        payload[28] = 0x0B
        payload[8] = 0x09
        payload[16] = 0x08
        payload[24] = 0x0B
        payload[32] = 0x15
        parsed = parse_gestures(bytes(payload))
        self.assertEqual(parsed["left"]["double-pinch"], "skip-forward")
        self.assertEqual(parsed["left"]["triple-pinch"], "skip-back")
        self.assertEqual(parsed["left"]["pinch-hold"], "noise-control-cycle")
        self.assertEqual(parsed["left"]["double-pinch-hold"], "voice-assistant")
        self.assertEqual(parsed["right"]["pinch-hold"], "voice-assistant")
        self.assertEqual(parsed["right"]["double-pinch-hold"], "noise-control-trans-off")

    def test_ear_tip_result_frame(self):
        # Captured-style result frame: cmd 0x0d, payload L/R seal bytes.
        body = build_frame(0x0D, DIR_RESPONSE, bytes([0, 1]), seq=0)
        parser = FrameParser()
        parser.feed(body)
        frame = next(parser.frames())
        self.assertEqual(frame.command, 0x0D)
        self.assertEqual(parse_ear_tip(frame.payload), {"left": "good", "right": "poor"})

    def test_version_and_license_notice(self):
        from pathlib import Path

        from eara import __version__

        root = Path(__file__).resolve().parents[1]
        self.assertEqual(__version__, "0.4.0")
        readme = (root / "README.md").read_text(encoding="utf-8")
        self.assertIn("GPL-3.0-or-later", readme)
        self.assertTrue((root / "LICENSE").is_file())
        self.assertIn("GPL-3.0-or-later", (root / "NOTICE").read_text(encoding="utf-8"))

    def test_graphic_eq_maps_to_three_bands(self):
        from eara.protocol import graphic_to_three, three_to_graphic

        bass, mid, treble = graphic_to_three([2, 2, 2, 0, 0, 0, -1, -1])
        self.assertAlmostEqual(bass, 2.0)
        self.assertAlmostEqual(mid, 0.0)
        self.assertAlmostEqual(treble, -1.0)
        graphic = three_to_graphic(2, 0, -1)
        self.assertEqual(graphic[:3], [2.0, 2.0, 2.0])
        self.assertEqual(graphic[-2:], [-1.0, -1.0])

    def test_ear1_has_preset_eq_only(self):
        model = model_from_name("Nothing Ear (1)")
        self.assertFalse(model.custom_eq)
        self.assertTrue(model.eq_presets)

    def test_frame_parser_caps_buffer(self):
        parser = FrameParser()
        parser.feed(b"\x00" * (MAX_FRAME_BUFFER + 100))
        self.assertLessEqual(len(parser._buf), MAX_FRAME_BUFFER)

    def test_parse_fast_pair_battery(self):
        parsed = parse_fast_pair_battery(bytes([0x50, 0x60 | 0x80, 0x7F]))
        self.assertEqual(parsed["left"]["level"], 80)
        self.assertEqual(parsed["right"]["level"], 96)
        self.assertTrue(parsed["right"]["charging"])
        self.assertNotIn("case", parsed)

    def test_parse_listening(self):
        self.assertEqual(parse_listening(bytes([1])), "entertainment")

    def test_cmf_headphone_pro_model(self):
        model = model_from_name("CMF Headphone Pro")
        self.assertEqual(model.base, "B175")
        self.assertTrue(model.single_battery)
        self.assertTrue(model.over_ear)
        self.assertEqual(model.rfcomm_channels, (28, 15))
        self.assertEqual(model.eq_family, "listening")
        self.assertTrue(model.protocol_version)
        self.assertTrue(model.spatial_audio)
        self.assertTrue(model.personal_sound)
        self.assertTrue(model.dual_connection)
        self.assertEqual(model.gesture_profile, "headphone")
        self.assertEqual(model.gesture_device, 6)
        self.assertFalse(model.in_ear)
        self.assertFalse(model.ear_tip_fit)
        self.assertEqual(model_from_serial("B175ABC").base, "B175")

    def test_headphone_single_battery(self):
        parsed = parse_battery(bytes([1, 6, 0x32]))
        self.assertEqual(parsed["headset"]["level"], 50)
        self.assertFalse(parsed["headset"]["charging"])
        self.assertNotIn("case", parsed)

    def test_parse_eq_b175(self):
        self.assertEqual(parse_eq(bytes([3]), "listening"), "pop")
        self.assertEqual(parse_eq(bytes([0]), "listening"), "dirac")
        self.assertEqual(parse_eq(bytes([3]), "earbud"), "voice")

    def test_parse_headphone_gestures_live(self):
        payload = bytes.fromhex("04060a0701060a010b0605012306010716")
        parsed = parse_headphone_gestures(payload)["controls"]
        self.assertEqual(parsed["button-single"], "voice-assistant")
        self.assertEqual(parsed["button-hold"], "no-action")
        self.assertEqual(parsed["energy-slider"], "bass-tuning")
        self.assertEqual(parsed["roller-hold"], "noise-control-trans-anc")

    def test_parse_spatial_personal_dual(self):
        self.assertEqual(parse_spatial(bytes([2, 0])), "concert")
        self.assertEqual(parse_spatial(bytes([3, 0])), "theatre")
        self.assertEqual(parse_spatial(bytes([0, 0])), "off")
        self.assertIs(parse_personal_sound(b"\x00"), False)
        self.assertIs(parse_personal_sound(b"\x01"), True)
        self.assertIs(parse_dual_enabled(b"\x00"), False)
        self.assertIs(parse_dual_enabled(b"\x01"), True)

    def test_parse_dual_devices(self):
        name = b"Pixel 9"
        payload = (
            bytes([0, 0, 1, 0x11])
            + bytes.fromhex("AABBCCDDEEFF")
            + bytes([len(name)])
            + name
        )
        devices = parse_dual_devices(payload)
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["mac"], "AA:BB:CC:DD:EE:FF")
        self.assertEqual(devices[0]["name"], "Pixel 9")
        self.assertTrue(devices[0]["connected"])
        self.assertTrue(devices[0]["this_device"])

    def test_b175_codec_zero_is_aac(self):
        self.assertEqual(parse_device_codec(b"\x00", "aac"), "aac")
        self.assertEqual(parse_device_codec(b"\x02", "aac"), "ldac")
        self.assertEqual(parse_device_codec(b"\x00"), "sbc")

    def test_b175_golden_frames(self):
        self.assertEqual(
            build_frame(0x01, DIR_GET, b"", seq=1).hex(),
            "55600101c000000124df",
        )
        self.assertEqual(
            build_frame(0x07, DIR_GET, b"", seq=2).hex(),
            "55600107c0000002ecde",
        )
        self.assertEqual(
            build_frame(
                0x41,
                DIR_SET,
                build_custom_eq_payload(3, 0, -3, peak_q=0.7),
                seq=1,
            ).hex(),
            "55600141f035000103000040c00100000000000075443333333f02000040c0"
            "00c05a450000803f000000404000000c43cdcc4c3f0000000000000000003252",
        )


if __name__ == "__main__":
    unittest.main()
