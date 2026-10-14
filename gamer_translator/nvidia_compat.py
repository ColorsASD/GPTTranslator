"""Az aktuális EXE saját NVIDIA G-SYNC kompatibilitási profilja.

Csak a driver System32-ben telepített NVAPI könyvtárát használja. Nem módosít
globális profilt, meglévő felhasználói profilt vagy más alkalmazás bejegyzését.
A modul importja nem tölt be DLL-t és nem olvassa/írja a driver adatbázisát.

A tesztelhető session_factory contextmanager szerződése: find_application(path),
find_profile(name), create_profile(name, path), set_force_off(profile),
delete_profile(profile), save(). A keresések profilleírást vagy None-t adnak.
"""
from __future__ import annotations

import ctypes as C
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SETTING_ID = 0x10A879CF  # NVAPI VRR_APP_OVERRIDE_ID
SETTING_VALUE = 1  # NVAPI VRR_APP_OVERRIDE_FORCE_OFF
CREATOR = "gamer_translator.nvidia_compat/v1"
PROFILE_PREFIX = "ColorsASD Gamer Translator - auto "
_UNSUPPORTED = {-2, -3, -6, -104}
_U32, _U16, _HANDLE = C.c_uint32, C.c_uint16, C.c_void_p
_UNICODE = _U16 * 2048


class NvApiError(RuntimeError):
    def __init__(self, operation: str, status: int):
        self.operation, self.status = operation, int(status)
        super().__init__(f"{operation}: NVAPI {status}")


class _Binary(C.Structure):
    _fields_ = [("length", _U32), ("value", C.c_ubyte * 4096)]


class _Value(C.Union):
    _pack_ = 4
    _fields_ = [("dword", _U32), ("binary", _Binary), ("text", _UNICODE), ("qword", C.c_uint64)]


class _Setting(C.Structure):
    _pack_ = 4
    _fields_ = [("version", _U32), ("name", _UNICODE), ("id", _U32), ("type", _U32),
               ("location", _U32), ("current_predefined", _U32), ("predefined_valid", _U32),
               ("predefined", _Value), ("current", _Value)]


class _Application(C.Structure):
    _fields_ = [("version", _U32), ("predefined", _U32), ("app", _UNICODE),
               ("friendly", _UNICODE), ("launcher", _UNICODE), ("file_in_folder", _UNICODE),
               ("flags", _U32), ("command_line", _UNICODE)]


class _Profile(C.Structure):
    _fields_ = [("version", _U32), ("name", _UNICODE), ("gpu_support", _U32),
               ("predefined", _U32), ("num_apps", _U32), ("num_settings", _U32)]


def _structure(cls: type[C.Structure], version: int) -> Any:
    value = cls()
    value.version = C.sizeof(cls) | (version << 16)
    return value


def _unicode(text: str) -> Any:
    encoded = text.encode("utf-16-le")
    if "\0" in text or len(encoded) >= C.sizeof(_UNICODE):
        raise ValueError("Érvénytelen NVAPI szöveg.")
    value = _UNICODE()
    C.memmove(value, encoded, len(encoded))
    return value


def _decode(value: Any) -> str:
    raw = bytes(value)
    end = next((i for i in range(0, len(raw), 2) if raw[i:i + 2] == b"\0\0"), len(raw))
    return raw[:end].decode("utf-16-le")


def _path_key(path: str | Path) -> str:
    return os.path.normcase(os.path.normpath(str(path)))


def profile_name_for(executable: str | Path) -> str:
    absolute = Path(executable).resolve()
    return PROFILE_PREFIX + hashlib.sha256(_path_key(absolute).encode("utf-8")).hexdigest()[:16]


def _setting_dict(value: Any) -> dict[str, Any]:
    return {"id": int(value.id), "type": int(value.type), "value": int(value.current.dword),
            "location": int(value.location), "predefined": bool(value.current_predefined)}


class NvApiSession:
    """A publikus NVAPI SDK NVDRS V1/V4 ABI-jának szűk DRS leképezése.

    A függvényazonosítók az NVIDIA nvapi_interface.h fájljából származnak;
    az NVDRS_SETTING_V1 négybájtos illesztésű, az alkalmazás V4 verziójú.
    """

    def __init__(self):
        self.handle = _HANDLE()
        self.initialized = False
        self.functions: dict[str, Any] = {}

    def __enter__(self):
        try:
            directory = C.create_unicode_buffer(32768)
            kernel = C.WinDLL("kernel32", winmode=0x800)
            get_directory = kernel.GetSystemDirectoryW
            get_directory.argtypes = [C.c_wchar_p, _U32]
            get_directory.restype = _U32
            length = get_directory(directory, len(directory))
            if not 0 < length < len(directory):
                raise OSError("A Windows rendszermappája nem kérdezhető le.")
            library = Path(directory.value) / "nvapi64.dll"
            if not library.is_file():
                raise NvApiError("LoadLibrary", -2)
            self.dll = C.CDLL(str(library), winmode=0x800)
            query = self.dll.nvapi_QueryInterface
            query.argtypes, query.restype = [_U32], _HANDLE
            # Csak a szükséges publikus DRS API; globális profilhoz nincs író hívás.
            specs = {
                "Initialize": (0x0150E828, ()), "Unload": (0xD22BDD7E, ()),
                "EnumPhysicalGPUs": (0xE5AC921F, (C.POINTER(_HANDLE), C.POINTER(_U32))),
                "CreateSession": (0x0694D52E, (C.POINTER(_HANDLE),)),
                "DestroySession": (0xDAD9CFF8, (_HANDLE,)), "LoadSettings": (0x375DBD6B, (_HANDLE,)),
                "SaveSettings": (0xFCBC7E14, (_HANDLE,)),
                "FindProfileByName": (0x7E4A9A0B, (_HANDLE, C.POINTER(_U16), C.POINTER(_HANDLE))),
                "FindApplicationByName": (0xEEE566B2, (_HANDLE, C.POINTER(_U16), C.POINTER(_HANDLE), C.POINTER(_Application))),
                "GetProfileInfo": (0x61CD6FD6, (_HANDLE, _HANDLE, C.POINTER(_Profile))),
                "GetSetting": (0x73BF8338, (_HANDLE, _HANDLE, _U32, C.POINTER(_Setting))),
                "EnumApplications": (0x7FA2173A, (_HANDLE, _HANDLE, _U32, C.POINTER(_U32), C.POINTER(_Application))),
                "EnumSettings": (0xAE3039DA, (_HANDLE, _HANDLE, _U32, C.POINTER(_U32), C.POINTER(_Setting))),
                "CreateProfile": (0xCC176068, (_HANDLE, C.POINTER(_Profile), C.POINTER(_HANDLE))),
                "CreateApplication": (0x4347A9DE, (_HANDLE, _HANDLE, C.POINTER(_Application))),
                "SetSetting": (0x577DD202, (_HANDLE, _HANDLE, C.POINTER(_Setting))),
                "DeleteProfile": (0x17093206, (_HANDLE, _HANDLE)),
            }
            for name, (identifier, arguments) in specs.items():
                pointer = query(identifier)
                if not pointer:
                    raise NvApiError(name, -3)
                self.functions[name] = C.CFUNCTYPE(C.c_int, *arguments)(pointer)
            self._check("Initialize")
            self.initialized = True
            devices, count = (_HANDLE * 64)(), _U32()
            self._check("EnumPhysicalGPUs", devices, C.byref(count))
            if not count.value:
                raise NvApiError("EnumPhysicalGPUs", -6)
            self._check("CreateSession", C.byref(self.handle))
            self._check("LoadSettings", self.handle)
            return self
        except BaseException:
            self.close()
            raise

    def _call(self, operation: str, *arguments: Any) -> int:
        return int(self.functions[operation](*arguments))

    def _check(self, operation: str, *arguments: Any) -> None:
        status = self._call(operation, *arguments)
        if status:
            raise NvApiError(operation, status)

    def close(self) -> None:
        # A takarítás hibája nem fedheti el a tranzakció eredeti státuszát.
        try:
            if self.handle.value:
                self._call("DestroySession", self.handle)
        finally:
            self.handle = _HANDLE()
            if self.initialized:
                self._call("Unload")
                self.initialized = False

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _snapshot(self, handle: Any) -> dict[str, Any]:
        info = _structure(_Profile, 1)
        self._check("GetProfileInfo", self.handle, handle, C.byref(info))
        setting = _structure(_Setting, 1)
        status = self._call("GetSetting", self.handle, handle, SETTING_ID, C.byref(setting))
        if status not in (0, -160):
            raise NvApiError("GetSetting", status)
        result = {"handle": handle.value, "name": _decode(info.name), "predefined": bool(info.predefined),
                  "num_apps": int(info.num_apps), "num_settings": int(info.num_settings),
                  "applications": [], "settings": [], "override": _setting_dict(setting) if not status else None}
        # Idegen nagy profiloknál nincs szükség az összes elem felsorolására.
        if info.num_apps == 1:
            app, count = _structure(_Application, 4), _U32(1)
            self._check("EnumApplications", self.handle, handle, 0, C.byref(count), C.byref(app))
            if count.value == 1:
                result["applications"] = [{"path": _decode(app.app), "friendly": _decode(app.friendly),
                    "predefined": bool(app.predefined), "launcher": _decode(app.launcher),
                    "file_in_folder": _decode(app.file_in_folder), "flags": int(app.flags),
                    "command_line": _decode(app.command_line)}]
        if info.num_settings == 1:
            local, count = _structure(_Setting, 1), _U32(1)
            self._check("EnumSettings", self.handle, handle, 0, C.byref(count), C.byref(local))
            if count.value == 1:
                result["settings"] = [_setting_dict(local)]
        return result

    def find_profile(self, name: str) -> dict[str, Any] | None:
        handle = _HANDLE()
        status = self._call("FindProfileByName", self.handle, _unicode(name), C.byref(handle))
        if status == -163:
            return None
        if status:
            raise NvApiError("FindProfileByName", status)
        return self._snapshot(handle)

    def find_application(self, executable: str) -> dict[str, Any] | None:
        handle, app = _HANDLE(), _structure(_Application, 4)
        status = self._call("FindApplicationByName", self.handle, _unicode(executable), C.byref(handle), C.byref(app))
        if status == -166:
            return None
        if status:
            raise NvApiError("FindApplicationByName", status)
        return self._snapshot(handle)

    def create_profile(self, name: str, executable: str) -> dict[str, Any]:
        info, handle = _structure(_Profile, 1), _HANDLE()
        info.name = _unicode(name)
        self._check("CreateProfile", self.handle, C.byref(info), C.byref(handle))
        app = _structure(_Application, 4)
        app.app, app.friendly = _unicode(executable), _unicode("Gamer Translator")
        self._check("CreateApplication", self.handle, handle, C.byref(app))
        return {"handle": handle.value}

    def set_force_off(self, profile: dict[str, Any]) -> None:
        setting = _structure(_Setting, 1)
        setting.id, setting.type, setting.current.dword = SETTING_ID, 0, SETTING_VALUE
        self._check("SetSetting", self.handle, _HANDLE(profile["handle"]), C.byref(setting))

    def delete_profile(self, profile: dict[str, Any]) -> None:
        self._check("DeleteProfile", self.handle, _HANDLE(profile["handle"]))

    def save(self) -> None:
        self._check("SaveSettings", self.handle)


def _persist(path: Path, state: dict[str, Any], *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path if exclusive else path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(state, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        if not exclusive:
            os.replace(temporary, path)
    finally:
        if not exclusive and temporary.exists():
            temporary.unlink()


def _read_state(path: Path) -> dict[str, Any] | None:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        return state if isinstance(state, dict) else None
    except (OSError, ValueError):
        return None


def _state_owned(state: dict[str, Any] | None, executable: str, name: str) -> bool:
    if not state:
        return False
    try:
        uuid.UUID(state["transaction_uuid"])
        return (state.get("schema") == 1 and state.get("created_by") == CREATOR
                and _path_key(state["application"]) == _path_key(executable)
                and state.get("profile_name") == name
                and state.get("setting_id") == SETTING_ID and state.get("setting_value") == SETTING_VALUE
                and state.get("created_profile_owned") is True
                and state.get("baseline") == {"application_absent": True, "profile_absent": True})
    except (KeyError, ValueError, TypeError):
        return False


def _force_off(profile: dict[str, Any] | None) -> bool:
    value = profile.get("override") if profile else None
    return bool(value and value.get("id") == SETTING_ID and value.get("type") == 0
                and value.get("value") == SETTING_VALUE)


def _owned_profile(profile: dict[str, Any] | None, state: dict[str, Any] | None,
                   executable: str, name: str) -> bool:
    if not _state_owned(state, executable, name) or not profile:
        return False
    apps, settings = profile.get("applications", []), profile.get("settings", [])
    if (profile.get("name") != name or profile.get("predefined") is not False
            or profile.get("num_apps") != 1 or profile.get("num_settings") != 1
            or len(apps) != 1 or len(settings) != 1):
        return False
    app = apps[0]
    return (_path_key(app.get("path", "")) == _path_key(executable)
            and app.get("friendly") == "Gamer Translator" and app.get("predefined") is False
            and app.get("launcher") == "" and app.get("file_in_folder") == ""
            and app.get("flags") == 0 and app.get("command_line") == ""
            and settings[0] == {"id": SETTING_ID, "type": 0, "value": SETTING_VALUE,
                                "location": 0, "predefined": False}
            and _force_off(profile) and profile["override"].get("location") == 0
            and profile["override"].get("predefined") is False)


def configure_nvidia_compatibility(executable: Path, *, enabled: bool = True, state_dir: Path,
                                   session_factory: Callable[[], Any] | None = None) -> dict[str, Any]:
    """Nem végzetes, frissen visszaellenőrzött alkalmazásprofil-beállítás.

    Valódi NVAPI csak Windows x64-en, csomagolt EXE-ből hívható. A forrásból
    indított program nem ír a driverbe. A hívó az öntesztet és egyéb ellenőrzési
    módokat az indítási pontban kihagyja; teszthez fake session_factory adható.
    """
    result: dict[str, Any] = {"status": "failed", "changed": False, "verified": False}
    if session_factory is None:
        if not getattr(sys, "frozen", False):
            return {**result, "status": "skipped", "reason": "source_run"}
        if sys.platform != "win32" or C.sizeof(C.c_void_p) != 8:
            return {**result, "status": "unsupported", "reason": "platform"}
        session_factory = NvApiSession
    try:
        executable = Path(executable).resolve(strict=True)
        if not executable.is_file() or executable.suffix.lower() != ".exe":
            raise ValueError("Érvénytelen alkalmazásútvonal.")
        path, name = str(executable), profile_name_for(executable)
        state_path = Path(state_dir) / (name.removeprefix(PROFILE_PREFIX) + ".json")
        state = _read_state(state_path)
        with session_factory() as session:
            application = session.find_application(path)
            profile = session.find_profile(name)
            if not enabled:
                if profile is None:
                    return {**result, "status": "disabled", "verified": True}
                if (application is None or application.get("handle") != profile.get("handle")
                        or not _owned_profile(profile, state, path, name)):
                    return {**result, "status": "ownership_unproven"}
                assert state is not None
                state["stage"] = "restore_pending"
                _persist(state_path, state)
                session.delete_profile(profile)
            else:
                if application is not None:
                    if application.get("name") == name and not _owned_profile(application, state, path, name):
                        return {**result, "status": "ownership_unproven"}
                    if _force_off(application):
                        status = "already_applied" if _owned_profile(application, state, path, name) else "already_configured"
                        return {**result, "status": status, "verified": True}
                    return {**result, "status": "existing_profile", "verified": True}
                if profile is not None:
                    return {**result, "status": "ownership_unproven"}
                state = {"schema": 1, "created_by": CREATOR, "transaction_uuid": str(uuid.uuid4()),
                         "application": path, "profile_name": name, "setting_id": SETTING_ID,
                         "setting_value": SETTING_VALUE, "baseline": {"application_absent": True, "profile_absent": True},
                         "created_profile_owned": False, "stage": "prepared",
                         "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                backup = state_path.parent / "backups" / (state_path.stem + "-" + state["transaction_uuid"] + ".json")
                _persist(backup, state, exclusive=True)
                _persist(state_path, state)
                own = session.create_profile(name, path)
                session.set_force_off(own)
                state["created_profile_owned"], state["stage"] = True, "save_pending"
                _persist(state_path, state)
            result["state_file"] = str(state_path)
            save_error = None
            try:
                session.save()
            except Exception as error:
                # A mentés hibája után az eredmény bizonytalan; nincs vak újraírás.
                save_error = error
        # Új session újra betölti a driver adatbázisát, nem a saját író cache-t olvassa.
        with session_factory() as session:
            application, profile = session.find_application(path), session.find_profile(name)
        if enabled:
            verified = (application is not None and profile is not None
                        and application.get("handle") == profile.get("handle")
                        and _owned_profile(profile, state, path, name))
        else:
            verified = application is None and profile is None
        if not verified:
            if save_error:
                raise save_error
            raise NvApiError("VerifySettings", -1)
        assert state is not None
        state["stage"] = "applied" if enabled else "restored"
        if isinstance(save_error, NvApiError):
            state["recovered_save_error"] = save_error.status
        _persist(state_path, state)
        result.update(status=state["stage"], changed=True, verified=True)
        if save_error:
            result["recovered_save_error"] = True
            if isinstance(save_error, NvApiError):
                result["error_code"] = save_error.status
        return result
    except Exception as error:
        if isinstance(error, NvApiError):
            result.update(status="unsupported" if error.status in _UNSUPPORTED else "failed",
                          operation=error.operation, error_code=error.status)
        else:
            result.update(status="failed", operation=type(error).__name__)
        return result
