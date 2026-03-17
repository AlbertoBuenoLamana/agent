"""Error types matching Steer Swift Errors.swift."""


class SteerError(Exception):
    pass


class CaptureFailure(SteerError):
    pass


class AppNotFound(SteerError):
    pass


class ElementNotFound(SteerError):
    pass


class NoSnapshot(SteerError):
    pass


class PermissionDenied(SteerError):
    pass


class ScreenNotFound(SteerError):
    pass


class WindowNotFound(SteerError):
    pass


class WindowActionFailed(SteerError):
    pass


class ClipboardEmpty(SteerError):
    pass


class WaitTimeout(SteerError):
    pass


class OcrFailed(SteerError):
    pass
