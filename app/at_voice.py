"""Africa's Talking Voice XML helpers.

Response must be application/xml with a <Response> root.
https://developers.africastalking.com/docs/voice/handle_calls
"""

from __future__ import annotations

import html
from typing import List, Optional
from xml.etree.ElementTree import Element, tostring


def _text(el: Element, value: str) -> None:
    el.text = value


def build_response(actions: List[Element]) -> str:
    root = Element("Response")
    for action in actions:
        root.append(action)
    xml = tostring(root, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>{xml}'


def say(text: str, *, voice: Optional[str] = None) -> Element:
    el = Element("Say")
    if voice:
        el.set("voice", voice)
    _text(el, html.unescape(text.strip()))
    return el


def play(url: str) -> Element:
    el = Element("Play")
    el.set("url", url)
    return el


def get_digits(
    *,
    num_digits: int = 1,
    timeout: int = 10,
    finish_on_key: str = "#",
    callback_url: Optional[str] = None,
    prompt: Optional[Element] = None,
) -> Element:
    el = Element("GetDigits")
    el.set("timeout", str(timeout))
    el.set("finishOnKey", finish_on_key)
    if num_digits:
        el.set("numDigits", str(num_digits))
    if callback_url:
        el.set("callbackUrl", callback_url)
    if prompt is not None:
        el.append(prompt)
    return el


def record(
    *,
    max_length: int = 45,
    timeout: int = 10,
    finish_on_key: str = "#",
    play_beep: bool = True,
    trim_silence: bool = True,
    callback_url: Optional[str] = None,
    prompt: Optional[Element] = None,
) -> Element:
    el = Element("Record")
    el.set("maxLength", str(max_length))
    el.set("timeout", str(timeout))
    el.set("finishOnKey", finish_on_key)
    el.set("playBeep", "true" if play_beep else "false")
    el.set("trimSilence", "true" if trim_silence else "false")
    if callback_url:
        el.set("callbackUrl", callback_url)
    if prompt is not None:
        el.append(prompt)
    return el


def reject() -> Element:
    return Element("Reject")
