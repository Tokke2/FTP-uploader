# Copyright (c) 2026 Rickard Längkvist
"""Windows shell shortcuts with a custom icon, using ctypes COM only."""
import ctypes
from pathlib import Path
import sys
import uuid


APP_ID = 'Tokke2.FTPUploader'


def set_app_id():
    if sys.platform == 'win32':
        function = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
        function.argtypes = [ctypes.c_wchar_p]
        function.restype = ctypes.c_long
        if function(APP_ID) < 0:
            raise OSError('Appens Windows-identitet kunde inte sättas.')


def create_shortcut(destination, target, arguments, icon, working_directory):
    """IShellLinkW/IPersistFile; no PowerShell, VBScript or extra package."""
    if sys.platform != 'win32':
        raise OSError('Windows-genvägar kräver Windows.')
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [('Data1', wintypes.DWORD), ('Data2', wintypes.WORD),
                    ('Data3', wintypes.WORD), ('Data4', ctypes.c_ubyte * 8)]

    def guid(value):
        return GUID.from_buffer_copy(uuid.UUID(value).bytes_le)

    def call(pointer, index, argtypes, *args):
        table = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        function = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argtypes)(table[index])
        result = function(pointer, *args)
        if result < 0:
            raise OSError('Windows COM-fel: 0x%08X' % (result & 0xffffffff))
        return result

    ole = ctypes.OleDLL('ole32')
    ole.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    ole.CoInitializeEx.restype = ctypes.c_long
    status = ole.CoInitializeEx(None, 2)
    initialized = status >= 0
    if status < 0 and (status & 0xffffffff) != 0x80010106:
        raise OSError('COM kunde inte initieras.')
    link = ctypes.c_void_p()
    persist = ctypes.c_void_p()
    store = ctypes.c_void_p()
    destination = Path(destination)
    temporary = destination.with_name(destination.stem + '.tmp.lnk')
    try:
        clsid = guid('00021401-0000-0000-C000-000000000046')
        iid_link = guid('000214F9-0000-0000-C000-000000000046')
        ole.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), ctypes.c_void_p, wintypes.DWORD,
                                        ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
        ole.CoCreateInstance.restype = ctypes.c_long
        result = ole.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid_link), ctypes.byref(link))
        if result < 0:
            raise OSError('Windows-genvägen kunde inte skapas.')
        call(link, 20, [wintypes.LPCWSTR], str(target))  # SetPath
        call(link, 11, [wintypes.LPCWSTR], arguments)  # SetArguments
        call(link, 9, [wintypes.LPCWSTR], str(working_directory))
        call(link, 7, [wintypes.LPCWSTR], 'FTP-uploader – bildgalleri och uppladdning')
        call(link, 17, [wintypes.LPCWSTR, ctypes.c_int], str(icon), 0)
        call(link, 15, [ctypes.c_int], 7 if '--autostart' in arguments else 1)  # SW_SHOWMINNOACTIVE for login
        # Match the process AppUserModelID so pinned/taskbar shortcuts belong
        # to this app, not to the shared Python interpreter.
        class PropertyKey(ctypes.Structure):
            _fields_ = [('fmtid', GUID), ('pid', wintypes.DWORD)]

        class Value(ctypes.Union):
            _fields_ = [('text', wintypes.LPWSTR),
                        ('storage', ctypes.c_byte * (16 if ctypes.sizeof(ctypes.c_void_p) == 8 else 8))]

        class PropVariant(ctypes.Structure):
            _fields_ = [('vt', ctypes.c_ushort), ('reserved1', ctypes.c_ushort),
                        ('reserved2', ctypes.c_ushort), ('reserved3', ctypes.c_ushort), ('value', Value)]

        iid_store = guid('886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99')
        call(link, 0, [ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)],
             ctypes.byref(iid_store), ctypes.byref(store))
        key = PropertyKey(guid('9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3'), 5)
        text = ctypes.create_unicode_buffer(APP_ID)
        value = PropVariant()
        value.vt = 31  # VT_LPWSTR, caller-owned buffer; SetValue copies it.
        value.value.text = ctypes.cast(text, wintypes.LPWSTR)
        call(store, 6, [ctypes.POINTER(PropertyKey), ctypes.POINTER(PropVariant)],
             ctypes.byref(key), ctypes.byref(value))
        call(store, 7, [])  # Commit
        iid_persist = guid('0000010B-0000-0000-C000-000000000046')
        call(link, 0, [ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)],
             ctypes.byref(iid_persist), ctypes.byref(persist))
        destination.parent.mkdir(parents=True, exist_ok=True)
        call(persist, 6, [wintypes.LPCWSTR, wintypes.BOOL], str(temporary), True)
        temporary.replace(destination)
    finally:
        if store:
            call(store, 2, [])
        if persist:
            call(persist, 2, [])
        if link:
            call(link, 2, [])
        if initialized:
            ole.CoUninitialize()
        temporary.unlink(missing_ok=True)
