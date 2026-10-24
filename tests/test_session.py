import socket
import unittest
from unittest.mock import MagicMock, patch

from eara import bluez
from eara.models import model_from_name, model_from_serial
from eara.session import Device


class SessionTests(unittest.TestCase):
    def test_resolve_model_prefers_serial_when_name_unknown(self):
        named = model_from_name("Bluetooth Audio")
        serial_model = model_from_serial("63123456")
        picked = Device._resolve_model("63123456", named)
        self.assertEqual(picked.base, serial_model.base)

    def test_resolve_model_sh_serial_keeps_name_when_known(self):
        named = model_from_name("Nothing Ear (a)")
        picked = Device._resolve_model("SH63ABCDEF", named)
        self.assertEqual(picked.base, "B162")

    def test_set_custom_eq_requires_response(self):
        device = Device("AA:BB:CC:DD:EE:FF", "Nothing Ear (a)")
        with patch.object(device, "_session") as session_ctx:
            session_ctx.return_value.__enter__ = MagicMock(return_value=device)
            session_ctx.return_value.__exit__ = MagicMock(return_value=False)
            device._sock = MagicMock(spec=socket.socket)
            device._sock.recv.side_effect = socket.timeout()
            with patch.object(device, "_send", return_value=9):
                with self.assertRaises(RuntimeError):
                    device.set_custom_eq(0.0, 0.0, 0.0)

    def test_ring_both_uses_distinct_side_byte(self):
        device = Device("AA:BB:CC:DD:EE:FF", "Nothing Ear (a)")
        with patch.object(device, "_session") as session_ctx:
            session_ctx.return_value.__enter__ = MagicMock(return_value=device)
            session_ctx.return_value.__exit__ = MagicMock(return_value=False)
            with patch.object(device, "_request", return_value=b"\x00") as req:
                device.ring("both")
                req.assert_called_with(0x02, 0xF0, bytes([0x01, 0x01]))

    def test_request_tracks_sequence(self):
        device = Device("AA:BB:CC:DD:EE:FF", "Nothing Ear (a)")
        device._sock = MagicMock(spec=socket.socket)
        device._sock.recv.side_effect = socket.timeout()
        with patch.object(device, "_send", return_value=42) as send:
            with patch.object(device, "_recv_for", return_value=b"ok") as recv:
                out = device._request(0x07, require=False)
        send.assert_called_once()
        recv.assert_called_once()
        self.assertEqual(recv.call_args.kwargs.get("seq"), 42)
        self.assertEqual(out, b"ok")

    def test_shutdown_disconnects_and_powers_off(self):
        device = Device("AA:BB:CC:DD:EE:FF", "Nothing Ear (a)")
        with patch.object(device, "close_control") as close_ctl:
            with patch.object(bluez, "disconnect") as disconnect:
                with patch.object(bluez, "power_off") as power_off:
                    device.shutdown()
        close_ctl.assert_called_once()
        disconnect.assert_called_once_with("AA:BB:CC:DD:EE:FF")
        power_off.assert_called_once()

    def test_shutdown_leaves_audio_connected_when_power_off_disabled(self):
        device = Device("AA:BB:CC:DD:EE:FF", "Nothing Ear (a)")
        with patch.object(device, "close_control") as close_ctl:
            with patch.object(bluez, "disconnect") as disconnect:
                with patch.object(bluez, "power_off") as power_off:
                    device.shutdown(power_off=False)
        close_ctl.assert_called_once()
        disconnect.assert_not_called()
        power_off.assert_not_called()

    def test_shutdown_can_disconnect_without_power_off(self):
        device = Device("AA:BB:CC:DD:EE:FF", "Nothing Ear (a)")
        with patch.object(device, "close_control"):
            with patch.object(bluez, "disconnect") as disconnect:
                with patch.object(bluez, "power_off") as power_off:
                    device.shutdown(power_off=False, disconnect=True)
        disconnect.assert_called_once_with("AA:BB:CC:DD:EE:FF")
        power_off.assert_not_called()

    @staticmethod
    def _open_session(device: Device):
        ctx = patch.object(device, "_session")
        session_ctx = ctx.start()
        session_ctx.return_value.__enter__ = MagicMock(return_value=device)
        session_ctx.return_value.__exit__ = MagicMock(return_value=False)
        return ctx

    def test_headphone_eq_uses_listening_command(self):
        device = Device("AA:BB:CC:DD:EE:FF", "CMF Headphone Pro")
        ctx = self._open_session(device)
        try:
            with patch.object(device, "_request", return_value=b"\x00") as req:
                device.set_eq("rock")
            req.assert_called_once_with(0x1D, 0xF0, bytes([1, 0]), require=True)
        finally:
            ctx.stop()

    def test_earbud_eq_still_uses_legacy_command(self):
        device = Device("AA:BB:CC:DD:EE:FF", "Nothing Ear (a)")
        ctx = self._open_session(device)
        try:
            with patch.object(device, "_request", return_value=b"\x00") as req:
                device.set_eq("balanced")
            req.assert_called_once_with(0x10, 0xF0, bytes([0, 0]), require=True)
        finally:
            ctx.stop()

    def test_headphone_gesture_payload(self):
        device = Device("AA:BB:CC:DD:EE:FF", "CMF Headphone Pro")
        ctx = self._open_session(device)
        try:
            with patch.object(device, "_request", return_value=b"\x00") as req:
                device.set_gesture("controls", "button-single", "voice-assistant")
            req.assert_called_once_with(
                0x03, 0xF0, bytes([1, 6, 10, 1, 0x0B]), require=True
            )
        finally:
            ctx.stop()

    def test_headphone_ring_uses_headphone_form(self):
        device = Device("AA:BB:CC:DD:EE:FF", "CMF Headphone Pro")
        ctx = self._open_session(device)
        try:
            with patch.object(device, "_request", return_value=b"\x00") as req:
                device.ring("both")
            req.assert_called_once_with(0x02, 0xF0, bytes([6, 1]))
        finally:
            ctx.stop()

    def test_headphone_spatial_personal_dual(self):
        device = Device("AA:BB:CC:DD:EE:FF", "CMF Headphone Pro")
        ctx = self._open_session(device)
        try:
            with patch.object(device, "_request", return_value=b"\x00") as req:
                device.set_spatial_audio("theatre")
                req.assert_called_once_with(0x52, 0xF0, bytes([3, 0]), require=True)
            with patch.object(device, "_request", return_value=b"\x00") as req:
                device.set_personal_sound(True)
                req.assert_called_once_with(0x5C, 0xF0, bytes([1]), require=True)
            with patch.object(device, "_request", return_value=b"\x00") as req:
                device.set_dual_connection(False)
                req.assert_called_once_with(0x1A, 0xF0, bytes([0]), require=True)
        finally:
            ctx.stop()

    def test_headphone_codec_maps_aac_and_ldac(self):
        device = Device("AA:BB:CC:DD:EE:FF", "CMF Headphone Pro")
        ctx = self._open_session(device)
        try:
            with patch("eara.session.audio.set_host_codec", return_value={"ok": True}):
                with patch.object(device, "_request", return_value=b"\x00") as req:
                    device.set_codec("ldac")
            req.assert_called_once_with(0x29, 0xF0, bytes([2]), require=True)
        finally:
            ctx.stop()


if __name__ == "__main__":
    unittest.main()
