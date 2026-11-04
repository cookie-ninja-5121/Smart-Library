
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageTk
import math
import os
import tkinter as tk
from tkinter import messagebox, TclError
from database import get_connection
from datetime import datetime, timedelta
import bcrypt
import serial
import threading
import queue
import time
import re
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from mysql.connector import Error as MySQLError

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

GLASS_TEXT = "#172B4D"
GLASS_MUTED = "#52647A"
GLASS_PANEL = "#EAF2FC"
GLASS_BORDER = "#CBD7E5"
GLASS_BLUE = "#3182CE"
GLASS_BLUE_HOVER = "#2563A6"
GLASS_OVERLAY = (245, 250, 255, 150)

BACKGROUND_IMAGE_PATH = r"D:\VsCODES_PROJECTS FOLDER\SmartLibraryApp\wallpapers\wallhaven-o3r9p7.png"

TXT = "#172B4D"
TXT_MUTED = "#52647A"
TXT_DIM = "#7B8CA3"
GREEN = "#1E8E5A"
SOLID = "#EAF2FC"
SOLID_RGB = (234, 242, 252)
ROW_LINE = "#CBD7E5"

BTN_BLUE = "#3182CE"
BTN_TEAL = "#16877D"
BTN_NAVY = "#2F5DA8"
BTN_PURPLE = "#6B50D6"
BTN_INDIGO = "#4A55C8"
BTN_RED = "#D9444A"
BTN_GHOST = "#5B7396"

STATUS_PILLS = {
    "Borrowed": ("#9FC4F8", "#1D4F91"),
    "Returned": ("#95F3C4", "#17734E"),
    "Available": ("#95F3C4", "#17734E"),
    "Overdue": ("#FAD6DB", "#A32035"),
}

PANEL_STYLES = {
    "card": {"fill": (255, 255, 255, 12), "border": (255, 255, 255, 150)},
    "inner": {"fill": (255, 255, 255, 70), "border": (203, 215, 229, 170)},
    "solid": {"fill": SOLID_RGB + (255,), "border": (203, 215, 229, 255)},
    "flat": None,
}


def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def shade(rgb, amount):
    """amount > 0 lightens, amount < 0 darkens."""
    if amount >= 0:
        return tuple(int(c + (255 - c) * amount) for c in rgb)
    return tuple(int(c * (1 + amount)) for c in rgb)


_FONT_CACHE = {}


def pil_font(size, bold=False):
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    candidates = []
    windir = os.environ.get("WINDIR")
    if windir:
        candidates.append(os.path.join(
            windir, "Fonts", "segoeuib.ttf" if bold else "segoeui.ttf"
        ))
    assets = os.path.join(
        os.path.dirname(ctk.__file__), "assets", "fonts", "Roboto"
    )
    candidates.append(os.path.join(
        assets, "Roboto-Medium.ttf" if bold else "Roboto-Regular.ttf"
    ))
    candidates.append("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")

    font = None
    for path in candidates:
        try:
            font = ImageFont.truetype(path, size)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    _FONT_CACHE[key] = font
    return font


def wrap_lines(text, font, max_width):
    lines = []
    for paragraph in str(text).split("\n"):
        current = ""
        for word in paragraph.split(" "):
            trial = word if not current else f"{current} {word}"
            if not current or font.getlength(trial) <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def render_text_image(text, size, bold, color, wrap=0, justify="left"):
    font = pil_font(size, bold)
    text = str(text)
    lines = wrap_lines(text, font, wrap) if wrap else text.split("\n")
    ascent, descent = font.getmetrics()
    line_height = ascent + descent
    gap = max(2, size // 5)
    widths = [math.ceil(font.getlength(line)) for line in lines]
    width = max(max(widths), 1) + 2
    height = line_height * len(lines) + gap * (len(lines) - 1) + 2

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    fill = hex_to_rgb(color) + (255,)
    for index, line in enumerate(lines):
        if justify == "center":
            x = (width - widths[index]) // 2
        elif justify == "right":
            x = width - widths[index] - 1
        else:
            x = 1
        draw.text((x, 1 + index * (line_height + gap)), line, font=font, fill=fill)
    return image


def rounded_mask(size, radius, supersample=3):
    width, height = size
    mask = Image.new("L", (width * supersample, height * supersample), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, width * supersample - 1, height * supersample - 1),
        radius=radius * supersample,
        fill=255
    )
    return mask.resize(size, Image.Resampling.LANCZOS)


def rounded_outline(size, radius, color, supersample=3):
    width, height = size
    layer = Image.new(
        "RGBA", (width * supersample, height * supersample), (0, 0, 0, 0)
    )
    ImageDraw.Draw(layer).rounded_rectangle(
        (0, 0, width * supersample - 1, height * supersample - 1),
        radius=radius * supersample,
        outline=color,
        width=supersample
    )
    return layer.resize(size, Image.Resampling.LANCZOS)


def draw_icon(name, px, color="#FFFFFF"):
    """Small vector icons drawn with PIL (supersampled for smooth edges)."""
    ss = 4
    size = px * ss
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    rgb = hex_to_rgb(color) + (255,)
    sw = max(int(size * 0.085), 2)

    def p(x, y):
        return (x * size, y * size)

    def line(points, width=sw):
        d.line([p(*pt) for pt in points], fill=rgb, width=width, joint="curve")
        for pt in (points[0], points[-1]):
            x, y = p(*pt)
            d.ellipse((x - width / 2, y - width / 2, x + width / 2, y + width / 2), fill=rgb)

    def ring(box):
        d.ellipse([*p(box[0], box[1]), *p(box[2], box[3])], outline=rgb, width=sw)

    def disc(box):
        d.ellipse([*p(box[0], box[1]), *p(box[2], box[3])], fill=rgb)

    if name == "plus":
        line([(0.2, 0.5), (0.8, 0.5)])
        line([(0.5, 0.2), (0.5, 0.8)])
    elif name == "plus_circle":
        ring((0.08, 0.08, 0.92, 0.92))
        line([(0.3, 0.5), (0.7, 0.5)])
        line([(0.5, 0.3), (0.5, 0.7)])
    elif name == "back":
        line([(0.82, 0.5), (0.2, 0.5)])
        line([(0.45, 0.24), (0.2, 0.5), (0.45, 0.76)])
    elif name == "chevron":
        line([(0.36, 0.2), (0.66, 0.5), (0.36, 0.8)])
    elif name == "search":
        ring((0.1, 0.1, 0.64, 0.64))
        line([(0.57, 0.57), (0.88, 0.88)])
    elif name == "clock":
        ring((0.08, 0.08, 0.92, 0.92))
        line([(0.5, 0.26), (0.5, 0.5), (0.68, 0.6)])
    elif name == "book":
        d.polygon([p(0.08, 0.24), p(0.47, 0.32), p(0.47, 0.86), p(0.08, 0.78)], fill=rgb)
        d.polygon([p(0.92, 0.24), p(0.53, 0.32), p(0.53, 0.86), p(0.92, 0.78)], fill=rgb)
    elif name == "user":
        disc((0.33, 0.12, 0.67, 0.46))
        d.pieslice([*p(0.16, 0.54), *p(0.84, 1.3)], 180, 360, fill=rgb)
    elif name == "user_plus":
        disc((0.14, 0.14, 0.44, 0.44))
        d.pieslice([*p(0.0, 0.52), *p(0.58, 1.2)], 180, 360, fill=rgb)
        line([(0.76, 0.34), (0.76, 0.7)], width=int(sw * 0.9))
        line([(0.58, 0.52), (0.94, 0.52)], width=int(sw * 0.9))
    elif name == "logout":
        line([(0.46, 0.14), (0.16, 0.14), (0.16, 0.86), (0.46, 0.86)])
        line([(0.36, 0.5), (0.86, 0.5)])
        line([(0.66, 0.28), (0.86, 0.5), (0.66, 0.72)])
    elif name == "swap":
        line([(0.86, 0.3), (0.16, 0.3)])
        line([(0.36, 0.12), (0.16, 0.3), (0.36, 0.48)])
        line([(0.14, 0.72), (0.84, 0.72)])
        line([(0.64, 0.54), (0.84, 0.72), (0.64, 0.9)])
    elif name == "alert":
        d.polygon([p(0.5, 0.1), p(0.94, 0.86), p(0.06, 0.86)], outline=rgb, width=sw)
        line([(0.5, 0.4), (0.5, 0.62)])
        disc((0.46, 0.7, 0.54, 0.78))

    return image.resize((px, px), Image.Resampling.LANCZOS)


def find_owner(widget):
    """Nearest ancestor that can hand out a background crop."""
    master = widget.master
    while master is not None:
        if hasattr(master, "crop_rect"):
            return master
        master = master.master
    return None


def has_surface_ancestor(widget):
    master = widget.master
    while master is not None:
        if isinstance(master, GlassPanel) and master.style != "flat":
            return True
        master = master.master
    return False


class GlassPanel(tk.Canvas):
    """Rounded translucent card painted over the window background."""

    def __init__(self, parent, app, style="card", radius=16, width=1, height=1):
        super().__init__(
            parent,
            width=app.px(width),
            height=app.px(height),
            bg="#0F1A30",
            bd=0,
            highlightthickness=0
        )
        self.app = app
        if style in ("card", "inner") and has_surface_ancestor(parent):
            style = "inner"
        self.style = style
        self.radius = app.px(radius)
        self.rendered = None
        self.bd_ver = 0
        self._sig = None
        self._photo = None
        app.baked.append(self)
        self.bind("<Configure>", lambda e: app.request_bake(), add="+")
        self.bind("<Map>", lambda e: app.request_bake(), add="+")

    def crop_rect(self, x, y, width, height):
        if self.rendered is None:
            return None
        return self.rendered.crop((x, y, x + width, y + height))

    def bake(self):
        if not self.winfo_ismapped():
            return
        width, height = self.winfo_width(), self.winfo_height()
        if width < 3 or height < 3:
            return
        owner = find_owner(self)
        if owner is None:
            return

        x = self.winfo_rootx() - owner.winfo_rootx()
        y = self.winfo_rooty() - owner.winfo_rooty()
        signature = (owner.bd_ver, x, y, width, height)
        if signature == self._sig:
            return

        behind = owner.crop_rect(x, y, width, height)
        if behind is None:
            return
        behind = behind.convert("RGB")

        spec = PANEL_STYLES[self.style]
        if spec is None:
            rendered = behind
        else:
            if self.style == "solid" or has_surface_ancestor(self):
                base = behind
            else:
                base = self.app.crop_glass(
                    self.winfo_rootx() - self.app.winfo_rootx(),
                    self.winfo_rooty() - self.app.winfo_rooty(),
                    width, height
                ).convert("RGB")

            surface = Image.alpha_composite(
                base.convert("RGBA"),
                Image.new("RGBA", (width, height), spec["fill"])
            )
            surface = Image.alpha_composite(
                surface,
                rounded_outline((width, height), self.radius, spec["border"])
            )
            mask = rounded_mask((width, height), self.radius)
            rendered = Image.composite(surface.convert("RGB"), behind, mask)

        self.rendered = rendered
        self.bd_ver += 1
        self._sig = signature
        self._photo = ImageTk.PhotoImage(rendered, master=self)
        self.delete("bg")
        self.create_image(0, 0, image=self._photo, anchor="nw", tags="bg")
        self.tag_lower("bg")


class BakedLabel(tk.Label):
    """Base for widgets that are one image composited over the backdrop."""

    def __init__(self, parent, app, **kwargs):
        kwargs.setdefault("cursor", "")
        super().__init__(
            parent, bd=0, highlightthickness=0, padx=0, pady=0,
            bg="#0F1A30", **kwargs
        )
        self.app = app
        self._content = None
        self._content_id = 0
        self._placeholder = None
        self._photo = None
        self._sig = None
        app.baked.append(self)
        self.bind("<Map>", lambda e: app.request_bake(), add="+")

    def build_content(self):
        raise NotImplementedError

    def set_content(self):
        content = self.build_content()
        resized = self._content is None or content.size != self._content.size
        self._content = content
        self._content_id += 1
        if resized:
            self._placeholder = tk.PhotoImage(
                master=self, width=content.width, height=content.height
            )
            tk.Label.configure(self, image=self._placeholder)
            self._photo = None
        self._sig = None
        self.bake()
        self.app.request_bake()

    def bake(self):
        if self._content is None or not self.winfo_ismapped():
            return
        owner = find_owner(self)
        if owner is None:
            return
        x = self.winfo_rootx() - owner.winfo_rootx()
        y = self.winfo_rooty() - owner.winfo_rooty()
        signature = (owner.bd_ver, x, y, self._content_id)
        if signature == self._sig:
            return
        backdrop = owner.crop_rect(x, y, *self._content.size)
        if backdrop is None:
            return
        image = Image.alpha_composite(
            backdrop.convert("RGBA"), self._content
        ).convert("RGB")
        self._photo = ImageTk.PhotoImage(image, master=self)
        tk.Label.configure(self, image=self._photo)
        self._sig = signature


class GlassLabel(BakedLabel):
    def __init__(
        self, parent, app, text="", size=13, bold=False,
        color=TXT, wrap=0, justify="left"
    ):
        super().__init__(parent, app)
        self.text = text
        self.size = size
        self.bold = bold
        self.color = color
        self.wrap = wrap
        self.justify = justify
        self.set_content()

    def build_content(self):
        return render_text_image(
            self.text,
            self.app.px(self.size),
            self.bold,
            self.color,
            wrap=self.app.px(self.wrap) if self.wrap else 0,
            justify=self.justify
        )

    def configure(self, cnf=None, **kwargs):
        changed = False
        if "text" in kwargs:
            self.text = kwargs.pop("text")
            changed = True
        if "text_color" in kwargs:
            self.color = kwargs.pop("text_color")
            changed = True
        if cnf or kwargs:
            tk.Label.configure(self, cnf, **kwargs)
        if changed:
            self.set_content()

    config = configure


class GlassIcon(BakedLabel):
    def __init__(
        self, parent, app, name, size=44, fill=BTN_BLUE, color="#FFFFFF",
        circle=True
    ):
        super().__init__(parent, app)
        self.name = name
        self.size = size
        self.fill = fill
        self.color = color
        self.circle = circle
        self.set_content()

    def build_content(self):
        px = self.app.px(self.size)
        image = Image.new("RGBA", (px, px), (0, 0, 0, 0))
        if self.circle and self.fill:
            ss = 4
            disc = Image.new("RGBA", (px * ss, px * ss), (0, 0, 0, 0))
            ImageDraw.Draw(disc).ellipse(
                (0, 0, px * ss - 1, px * ss - 1),
                fill=hex_to_rgb(self.fill) + (255,)
            )
            image = disc.resize((px, px), Image.Resampling.LANCZOS)
        inner = int(px * (0.5 if self.circle else 0.9))
        glyph = draw_icon(self.name, inner, self.color)
        offset = (px - inner) // 2
        image.alpha_composite(glyph, (offset, offset))
        return image


class GlassButton(BakedLabel):
    def __init__(
        self, parent, app, text="", command=None, color=BTN_BLUE,
        icon=None, width=140, height=38, radius=10, text_color="#FFFFFF",
        size=13, icon_right=False
    ):
        super().__init__(parent, app, cursor="hand2")
        self.text = text
        self.command = command
        self.color = color
        self.icon = icon
        self.icon_right = icon_right
        self.width = width
        self.height = height
        self.radius = radius
        self.text_color = text_color
        self.size = size
        self.state = "normal"
        self._hover = False
        self._pressed = False
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.set_content()

    def _on_enter(self, _event):
        self._hover = True
        self.set_content()

    def _on_leave(self, _event):
        self._hover = False
        self._pressed = False
        self.set_content()

    def _on_press(self, _event):
        if self.state == "normal":
            self._pressed = True
            self.set_content()

    def _on_release(self, event):
        was_pressed = self._pressed
        self._pressed = False
        inside = 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height()
        if was_pressed and inside and self.command is not None:
            self.set_content()
            self.command()
        elif was_pressed:
            self.set_content()

    def build_content(self):
        px = self.app.px
        w, h, r = px(self.width), px(self.height), px(self.radius)
        base = hex_to_rgb(self.color)
        if self.state == "disabled":
            base = shade(base, -0.45)
        elif self._pressed:
            base = shade(base, -0.18)
        elif self._hover:
            base = shade(base, 0.14)

        gradient = Image.linear_gradient("L").resize((w, h))
        body = Image.composite(
            Image.new("RGB", (w, h), shade(base, -0.10)),
            Image.new("RGB", (w, h), shade(base, 0.10)),
            gradient
        ).convert("RGBA")
        body = Image.alpha_composite(
            body, rounded_outline((w, h), r, (255, 255, 255, 55))
        )
        body.putalpha(rounded_mask((w, h), r))

        text_img = (
            render_text_image(self.text, px(self.size), True, self.text_color)
            if self.text else None
        )
        icon_px = int(h * 0.5)
        icon_img = draw_icon(self.icon, icon_px, self.text_color) if self.icon else None

        gap = px(10)
        total = 0
        if icon_img:
            total += icon_px
        if icon_img and text_img:
            total += gap
        if text_img:
            total += text_img.width
        x = (w - total) // 2
        parts = []
        if icon_img:
            parts.append(icon_img)
        if text_img:
            parts.append(text_img)
        if self.icon_right:
            parts.reverse()
        for part in parts:
            body.alpha_composite(part, (x, (h - part.height) // 2))
            x += part.width + gap
        return body

    def configure(self, cnf=None, **kwargs):
        changed = False
        for key, attr in (
            ("text", "text"), ("fg_color", "color"), ("state", "state"),
            ("command", "command")
        ):
            if key in kwargs:
                setattr(self, attr, kwargs.pop(key))
                changed = True
        if cnf or kwargs:
            tk.Label.configure(self, cnf, **kwargs)
        if changed:
            self.set_content()

    config = configure


class TintMixin:
    """Gives rounded CTk widgets a corner colour that matches the glass."""

    def tint_init(self, app):
        self.app = app
        self._tint = None
        app.baked.append(self)

    def bake(self):
        if not self.winfo_ismapped():
            return
        owner = find_owner(self)
        if owner is None:
            return
        width, height = self.winfo_width(), self.winfo_height()
        if width < 3 or height < 3:
            return
        crop = owner.crop_rect(
            self.winfo_rootx() - owner.winfo_rootx(),
            self.winfo_rooty() - owner.winfo_rooty(),
            width, height
        )
        if crop is None:
            return
        r, g, b = crop.convert("RGB").resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
        color = f"#{r:02x}{g:02x}{b:02x}"
        if color != self._tint:
            self._tint = color
            self.configure(bg_color=color)


class GlassEntry(TintMixin, ctk.CTkEntry):
    def __init__(self, parent, app, placeholder="", width=360, height=38, show=None):
        options = {"show": show} if show else {}
        super().__init__(
            parent,
            width=width,
            height=height,
            corner_radius=10,
            border_width=1,
            border_color="#CBD7E5",
            fg_color="#F5F8FC",
            text_color=TXT,
            placeholder_text_color=TXT_DIM,
            placeholder_text=placeholder,
            font=("Segoe UI", 13),
            **options
        )
        self.tint_init(app)


class GlassCombo(TintMixin, ctk.CTkComboBox):
    def __init__(self, parent, app, values, width=150, height=38, command=None):
        super().__init__(
            parent,
            values=values,
            width=width,
            height=height,
            corner_radius=10,
            border_width=1,
            border_color="#CBD7E5",
            fg_color="#F5F8FC",
            button_color="#3182CE",
            button_hover_color="#2563A6",
            text_color=TXT,
            dropdown_fg_color="#F5F8FC",
            dropdown_text_color=TXT,
            dropdown_hover_color="#D2E3FA",
            state="readonly",
            font=("Segoe UI", 13),
            dropdown_font=("Segoe UI", 13),
            command=command
        )
        self.tint_init(app)



class SmartLibraryApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Smart Library System")
        self.geometry("1000x650")
        self.minsize(850, 580)
        self.configure(fg_color="#E8F0FA")

        self.background_source_image = None
        self.background_image = None
        self.background_label = None
        self.content_background_image = None
        self.content_background_label = None
        self.content_background_photo = None
        self.card_refresh = None
        self.card_refresh_job = None
        self.theme_mode = "login"
        self.baked = []
        self.bake_job = None
        self.backdrop_job = None
        self.bg_plain = None
        self.bg_glass = None
        self.bd_ver = 0

        if BACKGROUND_IMAGE_PATH:
            try:
                with Image.open(BACKGROUND_IMAGE_PATH) as image:
                    self.background_source_image = image.convert("RGB")
            except OSError as error:
                messagebox.showerror(
                    "Background Image Error",
                    f"Could not open the configured background image:\n{error}"
                )
                raise

            self.background_image = ctk.CTkImage(
                light_image=self.background_source_image,
                dark_image=self.background_source_image,
                size=(1000, 650)
            )
            self.background_label = ctk.CTkLabel(
                self,
                text="",
                image=self.background_image
            )
            self.background_label.place(
                x=0, y=0, relwidth=1, relheight=1
            )
            self.background_label.lower()

        self.dark_source = self.build_dark_source()
        self.bind("<Configure>", self.resize_background_image, add="+")

        self.rfid_queue = queue.Queue()
        self.rfid_serial = None
        self.rfid_running = True
        self.rfid_scanning_enabled = False
        self.rfid_serial_lock = threading.Lock()
        self.overdue_reminder_lock = threading.Lock()
        self.overdue_reminder_running = False

        self.rfid_thread = threading.Thread(
            target=self.read_rfid_serial,
            daemon=True
        )
        self.rfid_thread.start()

        self.after(100, self.process_rfid_queue)
        self.after(5000, self.check_overdue_reminders)

        self.show_login()

    @staticmethod
    def send_email(recipient, subject, body):
        host = os.environ.get("SMART_LIBRARY_SMTP_HOST", "").strip()
        user = os.environ.get("SMART_LIBRARY_SMTP_USER", "").strip()
        password = os.environ.get("SMART_LIBRARY_SMTP_PASSWORD", "")
        sender = os.environ.get("SMART_LIBRARY_SMTP_FROM", user).strip()
        sender_name = os.environ.get(
            "SMART_LIBRARY_SMTP_FROM_NAME", "Smart Library System"
        ).strip()

        if not host or not user or not password or not sender:
            raise ValueError(
                "Email is not configured. Set "
                "SMART_LIBRARY_SMTP_HOST, SMART_LIBRARY_SMTP_USER, "
                "SMART_LIBRARY_SMTP_PASSWORD, and optionally "
                "SMART_LIBRARY_SMTP_FROM."
            )

        try:
            port = int(os.environ.get("SMART_LIBRARY_SMTP_PORT", "465"))
        except ValueError as error:
            raise ValueError("SMART_LIBRARY_SMTP_PORT must be a number.") from error

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr((sender_name, sender))
        message["To"] = recipient
        message.set_content(body)

        if port == 465:
            with smtplib.SMTP_SSL(
                host, port, timeout=20, context=ssl.create_default_context()
            ) as smtp:
                smtp.login(user, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
                smtp.login(user, password)
                smtp.send_message(message)

    def send_receipt(self, recipient, subject, body):
        if not recipient or not recipient.strip():
            return "No email address is registered for this student."

        try:
            self.send_email(recipient.strip(), subject, body)
        except (OSError, smtplib.SMTPException, ValueError) as error:
            logging.exception("Could not send receipt to %s", recipient)
            return f"The transaction succeeded, but the email could not be sent: {error}"

        return f"Receipt emailed to {recipient.strip()}."

    def check_overdue_reminders(self):
        if not all((
            os.environ.get("SMART_LIBRARY_SMTP_HOST"),
            os.environ.get("SMART_LIBRARY_SMTP_USER"),
            os.environ.get("SMART_LIBRARY_SMTP_PASSWORD")
        )):
            logging.warning(
                "Overdue email reminders are disabled until SMTP environment "
                "variables are configured."
            )
        else:
            with self.overdue_reminder_lock:
                if not self.overdue_reminder_running:
                    self.overdue_reminder_running = True
                    threading.Thread(
                        target=self.send_overdue_reminders,
                        daemon=True
                    ).start()

        if self.winfo_exists():
            self.after(24 * 60 * 60 * 1000, self.check_overdue_reminders)

    def send_overdue_reminders(self):
        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor()
            cursor.execute(
                "SHOW COLUMNS FROM loans LIKE 'overdue_reminder_sent_at'"
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    "ALTER TABLE loans "
                    "ADD COLUMN overdue_reminder_sent_at DATETIME NULL"
                )

            cursor.execute("""
                SELECT
                    l.id,
                    s.full_name,
                    s.email,
                    b.title,
                    l.due_date
                FROM loans l
                JOIN students s ON s.id = l.student_id
                JOIN books b ON b.id = l.book_id
                WHERE l.return_date IS NULL
                  AND l.due_date < NOW()
                  AND l.overdue_reminder_sent_at IS NULL
                  AND s.email IS NOT NULL
                  AND TRIM(s.email) <> ''
                ORDER BY l.due_date ASC, l.id ASC
                FOR UPDATE
            """)

            for loan_id, student_name, recipient, book_title, due_date in cursor.fetchall():
                body = (
                    f"Hello {student_name},\n\n"
                    f"This is a reminder that '{book_title}' is overdue. "
                    f"It was due on {due_date}.\n\n"
                    "Please return the book to the library as soon as possible.\n\n"
                    "Smart Library System"
                )
                try:
                    self.send_email(
                        recipient.strip(),
                        "Overdue book reminder",
                        body
                    )
                except (OSError, smtplib.SMTPException, ValueError):
                    logging.exception(
                        "Could not send overdue reminder for loan %s to %s",
                        loan_id,
                        recipient
                    )
                    continue

                cursor.execute(
                    """
                    UPDATE loans
                    SET overdue_reminder_sent_at = NOW()
                    WHERE id = %s AND overdue_reminder_sent_at IS NULL
                    """,
                    (loan_id,)
                )

            connection.commit()
        except (MySQLError, OSError, smtplib.SMTPException, ValueError):
            if connection and connection.is_connected():
                connection.rollback()
            logging.exception("Overdue reminder check failed")
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
            with self.overdue_reminder_lock:
                self.overdue_reminder_running = False

    def clear_window(self):
        self.card_refresh = None
        for widget in self.winfo_children():
            if widget is not self.background_label:
                widget.destroy()
        if self.background_label:
            self.background_label.lower()

    def px(self, value):
        try:
            scale = self._get_window_scaling()
        except Exception:
            scale = 1.0
        return max(int(round(value * scale)), 1)

    def build_dark_source(self):
        """Background picture with a navy tint, used by the app screens."""
        if self.background_source_image is not None:
            source = self.background_source_image.convert("RGBA")
        else:
            source = Image.linear_gradient("L").resize((1000, 650)).convert("RGB")
            source = Image.merge(
                "RGB",
                (
                    source.point(lambda v: 40 + v // 6),
                    source.point(lambda v: 30 + v // 5),
                    source.point(lambda v: 70 + v // 4),
                )
            ).convert("RGBA")
        tint = Image.new("RGBA", source.size, (12, 24, 52, 0))
        return Image.alpha_composite(source, tint).convert("RGB")

    def ensure_background_label(self):
        if self.background_label is not None:
            return
        self.background_image = ctk.CTkImage(
            light_image=self.dark_source,
            dark_image=self.dark_source,
            size=(max(self.winfo_width(), 1000), max(self.winfo_height(), 650))
        )
        self.background_label = ctk.CTkLabel(
            self, text="", image=self.background_image
        )
        self.background_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.background_label.lower()

    def set_theme_mode(self, mode):
        """'login' keeps the original light look, 'app' is the dark glass."""
        self.theme_mode = mode
        if mode == "app":
            self.configure(fg_color="#E8F0FA")
            self.ensure_background_label()
            self.background_image.configure(
                light_image=self.dark_source, dark_image=self.dark_source
            )
            self.rebuild_backdrops()
        else:
            self.configure(fg_color="#E8F0FA")
            if self.background_label is not None and self.background_source_image:
                self.background_image.configure(
                    light_image=self.background_source_image,
                    dark_image=self.background_source_image
                )

    def rebuild_backdrops(self):
        width = max(self.winfo_width(), 2)
        height = max(self.winfo_height(), 2)
        self.bg_plain = self.dark_source.resize(
            (width, height), Image.Resampling.LANCZOS
        )
        frosted = self.bg_plain.filter(ImageFilter.GaussianBlur(14)).convert("RGBA")
        frosted = Image.alpha_composite(
            frosted, Image.new("RGBA", frosted.size, (245, 250, 255, 150))
        )
        self.bg_glass = frosted.convert("RGB")
        self.bd_ver += 1

    def crop_rect(self, x, y, width, height):
        if self.bg_plain is None:
            return None
        return self.bg_plain.crop((x, y, x + width, y + height))

    def crop_glass(self, x, y, width, height):
        if self.bg_glass is None:
            return self.crop_rect(x, y, width, height)
        return self.bg_glass.crop((x, y, x + width, y + height))

    def request_bake(self):
        if self.bake_job is None:
            self.bake_job = self.after(12, self.run_bake)

    def run_bake(self):
        self.bake_job = None
        if self.theme_mode != "app":
            return
        width, height = self.winfo_width(), self.winfo_height()
        if width > 1 and (
            self.bg_plain is None or self.bg_plain.size != (width, height)
        ):
            self.rebuild_backdrops()

        alive = []
        for widget in self.baked:
            try:
                if widget.winfo_exists():
                    alive.append(widget)
            except TclError:
                pass
        self.baked = alive
        alive.sort(key=lambda widget: str(widget).count("."))
        for widget in alive:
            try:
                widget.bake()
            except TclError:
                pass

    # widget factories
    def flat(self, parent):
        return GlassPanel(parent, self, style="flat", radius=0)

    def card(self, parent, radius=16, width=1, height=1):
        return GlassPanel(
            parent, self, style="card", radius=radius, width=width, height=height
        )

    def label(self, parent, text, size=13, bold=False, color=TXT, wrap=0,
              justify="left"):
        return GlassLabel(
            parent, self, text=text, size=size, bold=bold, color=color,
            wrap=wrap, justify=justify
        )

    def button(self, parent, text, command, color=BTN_BLUE, icon=None,
               width=140, height=38, icon_right=False):
        return GlassButton(
            parent, self, text=text, command=command, color=color,
            icon=icon, width=width, height=height, icon_right=icon_right
        )

    def entry(self, parent, placeholder, width=360, height=38, show=None):
        return GlassEntry(
            parent, self, placeholder=placeholder, width=width,
            height=height, show=show
        )

    def table_card(self, parent, **pack_options):
        """Dark rounded panel holding a scrollable table."""
        panel = GlassPanel(parent, self, style="solid", radius=14)
        panel.pack(fill="both", expand=True, **pack_options)
        table = ctk.CTkScrollableFrame(
            panel,
            fg_color=SOLID,
            corner_radius=0,
            border_width=0,
            scrollbar_button_color="#AFC0D6",
            scrollbar_button_hover_color="#8FA6C4"
        )
        table.pack(fill="both", expand=True, padx=8, pady=8)
        return table

    def fill_table(self, frame, headers, rows, weights=None, status_col=None,
                   empty_text="Nothing to show.", wrap=0):
        for widget in frame.winfo_children():
            widget.destroy()

        count = len(headers)
        weights = weights or [1] * count
        for column, weight in enumerate(weights):
            frame.grid_columnconfigure(column, weight=weight)

        for column, heading in enumerate(headers):
            ctk.CTkLabel(
                frame,
                text=heading,
                font=("Segoe UI", 12, "bold"),
                text_color=TXT,
                anchor="w"
            ).grid(row=0, column=column, padx=12, pady=(8, 10), sticky="w")

        def add_line(row_index):
            ctk.CTkFrame(
                frame, height=1, fg_color=ROW_LINE, corner_radius=0
            ).grid(row=row_index, column=0, columnspan=count, sticky="ew")

        add_line(1)

        if not rows:
            ctk.CTkLabel(
                frame,
                text=empty_text,
                font=("Segoe UI", 13),
                text_color=TXT_MUTED
            ).grid(row=2, column=0, columnspan=count, padx=12, pady=18, sticky="w")
            return

        grid_row = 2
        for row in rows:
            for column, value in enumerate(row):
                text = "-" if value in (None, "") else str(value)
                if column == status_col and text in STATUS_PILLS:
                    pill_bg, pill_fg = STATUS_PILLS[text]
                    ctk.CTkLabel(
                        frame,
                        text=text,
                        font=("Segoe UI", 11, "bold"),
                        fg_color=pill_bg,
                        text_color=pill_fg,
                        corner_radius=11,
                        width=88,
                        height=24
                    ).grid(row=grid_row, column=column, padx=12, pady=9, sticky="w")
                else:
                    ctk.CTkLabel(
                        frame,
                        text=text,
                        font=("Segoe UI", 12),
                        text_color="#334155",
                        anchor="w",
                        justify="left",
                        wraplength=wrap
                    ).grid(row=grid_row, column=column, padx=12, pady=10, sticky="w")
            add_line(grid_row + 1)
            grid_row += 2

    def crop_background_for_widget(self, widget):
        window_width = max(self.winfo_width(), 1)
        window_height = max(self.winfo_height(), 1)
        image = self.background_source_image.resize(
            (window_width, window_height),
            Image.Resampling.LANCZOS
        )
        left = widget.winfo_rootx() - self.winfo_rootx()
        top = widget.winfo_rooty() - self.winfo_rooty()
        right = left + max(widget.winfo_width(), 1)
        bottom = top + max(widget.winfo_height(), 1)
        return image.crop((left, top, right, bottom))

    def make_frosted_image(self, widget, corner_radius):
        background = self.crop_background_for_widget(widget).convert("RGB")
        frosted = background.filter(
            ImageFilter.GaussianBlur(10)
        ).convert("RGBA")
        overlay = Image.new("RGBA", frosted.size, (245, 250, 255, 150))
        frosted = Image.alpha_composite(frosted, overlay).convert("RGB")

        mask = Image.new("L", frosted.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, frosted.width - 1, frosted.height - 1),
            radius=corner_radius,
            fill=255
        )
        image = Image.composite(frosted, background, mask)

        return image

    def resize_background_image(self, event):
        if event.widget is self and self.background_image:
            self.background_image.configure(
                size=(max(event.width, 1), max(event.height, 1))
            )
            if self.card_refresh:
                if self.card_refresh_job:
                    self.after_cancel(self.card_refresh_job)
                self.card_refresh_job = self.after(60, self.card_refresh)
        if event.widget is self and self.theme_mode == "app":
            if self.backdrop_job:
                self.after_cancel(self.backdrop_job)
            self.backdrop_job = self.after(70, self.request_bake)

    def make_card(self, width=420, height=400):
        """Frosted-glass card drawn on a Canvas so text can sit directly
        on the glass with no solid-colour box behind it."""
        card = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=GLASS_PANEL,
            bd=0,
            highlightthickness=0
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.tint_targets = []

        if self.background_source_image:
            def refresh(event=None):
                if event is not None and event.widget is not card:
                    return
                if not card.winfo_exists():
                    return
                if card.winfo_width() <= 1 or card.winfo_height() <= 1:
                    return
                frosted = self.make_frosted_image(card, 22)
                photo = ImageTk.PhotoImage(frosted, master=card)
                card.delete("glass_bg")
                card.create_image(
                    0, 0, image=photo, anchor="nw", tags="glass_bg"
                )
                card.tag_lower("glass_bg")
                card.glass_photo = photo
                for target, bx, by, bw, bh in card.tint_targets:
                    r, g, b = frosted.crop(
                        (bx, by, bx + bw, by + bh)
                    ).resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
                    target.configure(bg_color=f"#{r:02x}{g:02x}{b:02x}")

            card.bind("<Configure>", refresh, add="+")
            card.after_idle(refresh)
            self.card_refresh = refresh

        return card

    def add_card_text(self, card, x, y, text, font):
        return card.create_text(
            x, y,
            text=text,
            font=font,
            fill=GLASS_TEXT,
            anchor="center"
        )

    def add_card_entry(self, card, x, y, placeholder, height=42, show=None):
        options = {}
        if show:
            options["show"] = show
        entry = ctk.CTkEntry(
            card,
            width=320,
            height=height,
            corner_radius=8,
            border_width=1,
            border_color=GLASS_BORDER,
            fg_color="#F5F8FC",
            text_color=GLASS_TEXT,
            placeholder_text_color=GLASS_MUTED,
            placeholder_text=placeholder,
            **options
        )
        card.create_window(x, y, window=entry)
        card.tint_targets.append((
            entry,
            x - self.px(320) // 2, y - self.px(height) // 2,
            self.px(320), self.px(height)
        ))
        return entry

    def add_card_button(self, card, x, y, text, command, height=42):
        button = ctk.CTkButton(
            card,
            text=text,
            width=320,
            height=height,
            corner_radius=8,
            command=command
        )
        card.create_window(x, y, window=button)
        card.tint_targets.append((
            button,
            x - self.px(320) // 2, y - self.px(height) // 2,
            self.px(320), self.px(height)
        ))
        return button

    def add_card_link(self, card, x, y, text, command):
        normal_color = "#082661"
        hover_color = "#2779F5"
        item = card.create_text(
            x, y,
            text=text,
            font=("Segoe UI", 11),
            fill=normal_color,
            anchor="center"
        )

        def on_enter(event):
            card.itemconfigure(
                item,
                fill=hover_color,
                font=("Segoe UI", 11, "underline")
            )
            card.configure(cursor="hand2")

        def on_leave(event):
            card.itemconfigure(
                item,
                fill=normal_color,
                font=("Segoe UI", 11)
            )
            card.configure(cursor="")

        card.tag_bind(item, "<Enter>", on_enter)
        card.tag_bind(item, "<Leave>", on_leave)
        card.tag_bind(
            item, "<Button-1>", lambda event: self.after(10, command)
        )
        return item

    def show_login(self):
        self.set_rfid_scan_mode(False)
        self.clear_window()
        self.set_theme_mode("login")
        card = self.make_card(width=420, height=400)
        cx = 210

        self.add_card_text(
            card, cx, 62, "SMART LIBRARY", ("Segoe UI", 28, "bold")
        )
        self.add_card_text(
            card, cx, 102, "Librarian Login", ("Segoe UI", 16)
        )

        self.username_entry = self.add_card_entry(
            card, cx, 168, "Username"
        )
        self.password_entry = self.add_card_entry(
            card, cx, 226, "Password", show="*"
        )

        self.add_card_button(card, cx, 294, "Log In", self.login)
        self.add_card_link(
            card, cx, 352, "Dont have account? Create Account", self.show_register
        )

    def show_register(self):
        self.set_rfid_scan_mode(False)
        self.clear_window()
        self.set_theme_mode("login")
        card = self.make_card(width=420, height=520)
        cx = 210

        self.add_card_text(
            card, cx, 52, "Create Account", ("Segoe UI", 26, "bold")
        )

        self.reg_name = self.add_card_entry(
            card, cx, 118, "Full Name", height=38
        )
        self.reg_id = self.add_card_entry(
            card, cx, 168, "Librarian ID", height=38
        )
        self.reg_username = self.add_card_entry(
            card, cx, 218, "Username", height=38
        )
        self.reg_email = self.add_card_entry(
            card, cx, 268, "Email", height=38
        )
        self.reg_password = self.add_card_entry(
            card, cx, 318, "Password", height=38, show="*"
        )
        self.reg_confirm = self.add_card_entry(
            card, cx, 368, "Confirm Password", height=38, show="*"
        )

        self.add_card_button(
            card, cx, 430, "Create Account", self.register, height=40
        )
        self.add_card_link(
            card, cx, 480, "Already have an account? Login", self.show_login
        )

    def register(self):
        name = self.reg_name.get().strip()
        librarian_id = self.reg_id.get().strip()
        username = self.reg_username.get().strip()
        email = self.reg_email.get().strip()
        password = self.reg_password.get()
        confirm = self.reg_confirm.get()

        if not all([name, librarian_id, username, email, password, confirm]):
            messagebox.showwarning(
                "Missing Information",
                "Please complete all fields."
            )
            return

        if password != confirm:
            messagebox.showerror(
                "Password Error",
                "The passwords do not match."
            )
            return

        if len(password) < 8:
            messagebox.showwarning(
                "Weak Password",
                "Use a password with at least 8 characters."
            )
            return

        connection = None
        cursor = None

        try:
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8")

            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO librarians
                    (librarian_id, name, username, email, password_hash)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (librarian_id, name, username, email, password_hash)
            )

            connection.commit()

            messagebox.showinfo(
                "Success",
                "Librarian account created successfully!"
            )
            self.show_login()

        except Exception as error:
            if connection and connection.is_connected():
                connection.rollback()

            messagebox.showerror(
                "Registration Failed",
                "Could not create the account.\n"
                "The librarian ID, username, or email may already exist.\n\n"
                f"Details: {error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showwarning(
                "Missing Information",
                "Enter your username and password."
            )
            return

        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT id, librarian_id, name, username, password_hash
                FROM librarians
                WHERE username = %s
                """,
                (username,)
            )
            librarian = cursor.fetchone()

            if librarian and bcrypt.checkpw(
                password.encode("utf-8"),
                librarian["password_hash"].encode("utf-8")
            ):
                messagebox.showinfo(
                    "Login Successful",
                    f"Welcome, {librarian['name']}!"
                )
                self.show_dashboard(librarian)
            else:
                messagebox.showerror(
                    "Login Failed",
                    "Incorrect username or password."
                )

        except Exception as error:
            messagebox.showerror(
                "Database Error",
                f"Could not log in:\n{error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def read_rfid_serial(self):
        try:
            with serial.Serial("COM3", 9600, timeout=1) as arduino:
                time.sleep(2)
                with self.rfid_serial_lock:
                    self.rfid_serial = arduino
                    mode = (
                        "MODE:SCAN\n"
                        if self.rfid_scanning_enabled
                        else "MODE:IDLE\n"
                    )
                    arduino.write(mode.encode("ascii"))

                while self.rfid_running:
                    line = arduino.readline().decode(
                        "utf-8", errors="ignore"
                    ).strip()

                    if line.startswith("Tag UID:"):
                        uid = line.split(":", 1)[1].strip().upper()
                        self.rfid_queue.put(uid)

        except serial.SerialException as error:
            self.rfid_queue.put(f"ERROR:{error}")
        finally:
            with self.rfid_serial_lock:
                self.rfid_serial = None

    def set_rfid_scan_mode(self, enabled):
        self.rfid_scanning_enabled = enabled

        while True:
            try:
                self.rfid_queue.get_nowait()
            except queue.Empty:
                break

        with self.rfid_serial_lock:
            arduino = self.rfid_serial
            if arduino is None or not arduino.is_open:
                return

            command = "MODE:SCAN\n" if enabled else "MODE:IDLE\n"
            try:
                arduino.write(command.encode("ascii"))
            except serial.SerialException as error:
                print(f"RFID mode update failed: {error}")

    def send_lcd_message(self, heading, detail):
        heading = " ".join(str(heading).split()).replace("|", "/")[:16]
        detail = " ".join(str(detail).split()).replace("|", "/")[:16]

        with self.rfid_serial_lock:
            arduino = self.rfid_serial
            if arduino is None or not arduino.is_open:
                return

            try:
                arduino.write(
                    f"LCD:{heading}|{detail}\n".encode("ascii", errors="replace")
                )
            except serial.SerialException as error:
                print(f"LCD update failed: {error}")

    def display_registered_rfid_name(self, uid):
        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT full_name
                FROM students
                WHERE UPPER(TRIM(rfid_uid)) = %s
                LIMIT 1
                """,
                (uid,)
            )
            student = cursor.fetchone()
            if student:
                self.send_lcd_message("STUDENT", student[0])
                return

            cursor.execute(
                """
                SELECT title
                FROM books
                WHERE UPPER(TRIM(rfid_uid)) = %s
                LIMIT 1
                """,
                (uid,)
            )
            book = cursor.fetchone()
            if book:
                self.send_lcd_message("BOOK", book[0])
                return

            if getattr(self, "current_page", None) == "Add Book":
                title = self.book_title_entry.get().strip()
                if title:
                    self.send_lcd_message("NEW BOOK", title)
                    return
            elif getattr(self, "current_page", None) == "Register Student":
                name = self.student_name_entry.get().strip()
                if name:
                    self.send_lcd_message("NEW STUDENT", name)
                    return

            self.send_lcd_message("RFID SCANNED", uid)

        except Exception as error:
            print(f"Could not resolve RFID name for LCD: {error}")
            self.send_lcd_message("RFID SCANNED", uid)

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def reject_duplicate_registration_scan(
        self,
        uid,
        entry,
        update_indicator
    ):
        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor()
            registered_type = self.find_registered_rfid(cursor, uid)

        except Exception as error:
            entry.delete(0, "end")
            update_indicator()
            messagebox.showerror(
                "RFID Validation Error",
                f"Could not verify whether this RFID is available:\n{error}"
            )
            return True

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

        if not registered_type:
            return False

        entry.delete(0, "end")
        update_indicator()
        self.send_lcd_message("RFID ALREADY USED", registered_type)
        messagebox.showwarning(
            "RFID Already Registered",
            "This RFID UID is already registered to a "
            f"{registered_type}. Registration cancelled. "
            "Scan a different RFID tag."
        )
        return True

    def process_rfid_queue(self):
        try:
            while True:
                item = self.rfid_queue.get_nowait()

                if item.startswith("ERROR:"):
                    print("RFID connection:", item[6:])
                    continue

                if not self.rfid_scanning_enabled:
                    continue

                print("RFID scanned:", item)
                self.handle_rfid_scan(item)

        except queue.Empty:
            pass

        if self.winfo_exists():
            self.after(100, self.process_rfid_queue)

    
    def handle_rfid_scan(self, uid):
        if not self.rfid_scanning_enabled:
            return

        uid = uid.strip().upper()

        for entry_name, update_name, page_name in (
            ("book_rfid_entry", "book_rfid_indicator_update", "Add Book"),
            ("student_rfid_entry", "student_rfid_indicator_update", "Register Student")
        ):
            entry = getattr(self, entry_name, None)
            try:
                active = entry is not None and entry.winfo_exists()
            except TclError:
                active = False

            if active:
                update_indicator = getattr(self, update_name)
                if self.reject_duplicate_registration_scan(
                    uid,
                    entry,
                    update_indicator
                ):
                    return

                entry.delete(0, "end")
                entry.insert(0, uid)
                update_indicator()
                self.display_registered_rfid_name(uid)
                print(f"RFID scanned into {page_name}: {uid}")
                return

        self.display_registered_rfid_name(uid)

        entry = getattr(self, "return_book_rfid_entry", None)
        try:
            active = entry is not None and entry.winfo_exists()
        except TclError:
            active = False

        if active:
            entry.delete(0, "end")
            entry.insert(0, uid)
            self.return_rfid_indicator_update()
            self.lookup_active_return_book()
            return

        student_entry = getattr(self, "borrow_student_entry", None)
        book_combo = getattr(self, "borrow_book_combo", None)

        try:
            active = (
                student_entry is not None
                and student_entry.winfo_exists()
                and book_combo is not None
                and book_combo.winfo_exists()
            )
        except TclError:
            active = False

        if not active:
            print("RFID scanned, but no matching form is open.")
            return

        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT student_no, full_name
                FROM students
                WHERE UPPER(rfid_uid) = %s
                LIMIT 1
                """,
                (uid,)
            )
            student = cursor.fetchone()

            if student:
                student_no, full_name = student
                self.borrow_student_no = student_no
                student_entry.delete(0, "end")
                student_entry.insert(0, full_name)
                self.borrow_rfid_indicator_update()
                print(f"Recognized student: {full_name} ({student_no})")
                return

            cursor.execute(
                """
                SELECT b.id, b.title
                FROM books b
                WHERE UPPER(b.rfid_uid) = %s
                  AND NOT EXISTS (
                      SELECT 1
                      FROM loans l
                      WHERE l.book_id = b.id
                        AND l.return_date IS NULL
                  )
                LIMIT 1
                """,
                (uid,)
            )
            book = cursor.fetchone()

            if book:
                book_id, title = book
                for display, mapped_id in self.available_book_map.items():
                    if mapped_id == book_id:
                        self.set_borrow_book_selection(display)
                        print(f"Selected available book: {title}")
                        return

                messagebox.showwarning(
                    "Refresh Required",
                    f"{title} is available in the database but not in the current list. "
                    "Please reopen Borrow Book and scan again."
                )
                return

            cursor.execute(
                """
                SELECT title
                FROM books
                WHERE UPPER(rfid_uid) = %s
                LIMIT 1
                """,
                (uid,)
            )
            registered_book = cursor.fetchone()

            if registered_book:
                self.send_lcd_message("BOOK BORROWED", registered_book[0])
                messagebox.showwarning(
                    "Book Unavailable",
                    f"{registered_book[0]} is already borrowed."
                )
            else:
                messagebox.showwarning(
                    "Unknown RFID",
                    f"This tag is not registered:\n{uid}"
                )

        except Exception as error:
            messagebox.showerror(
                "RFID Error",
                f"Could not process RFID scan:\n{error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()


    def show_dashboard(self, librarian):
        self.clear_window()
        self.set_theme_mode("app")

        self.content = GlassPanel(self, self, style="flat", radius=0)
        self.content.pack(fill="both", expand=True, padx=22, pady=(16, 16))

        self.show_page("Dashboard", librarian)

    def show_page(self, page, librarian):
        self.current_page = page
        self.set_rfid_scan_mode(
            page in {
                "Add Book",
                "Register Student",
                "Borrow Book",
                "Return Book"
            }
        )

        for widget in self.content.winfo_children():
            widget.destroy()
        self.request_bake()

        if page == "Dashboard":
            self.build_dashboard(librarian)
            return

        header = self.flat(self.content)
        header.pack(fill="x", pady=(0, 14))
        self.button(
            header, "", lambda: self.show_page("Dashboard", librarian),
            color=BTN_GHOST, icon="back", width=46, height=40
        ).pack(side="left", padx=(0, 14))
        self.label(header, page, size=28, bold=True).pack(side="left")

        if page == "Add Book":
            self.show_add_book()
        elif page == "Register Student":
            self.show_student_accounts()
        elif page == "Book Catalog":
            self.show_book_catalog()
        elif page == "Borrowed":
            self.show_loan_catalog("Borrowed")
        elif page == "Overdue":
            self.show_loan_catalog("Overdue")
        elif page == "Borrow Book":
            self.show_borrow_book()
        elif page == "Return Book":
            self.show_return_book()
        elif page == "Borrowing History":
            self.show_borrowing_history()
        else:
            self.label(
                self.content,
                f"{page} screen will be implemented next.",
                size=15, color=TXT_MUTED
            ).pack(anchor="w")

    def build_dashboard(self, librarian):
        # Retrieve dashboard statistics from MySQL
        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute("SELECT COUNT(*) FROM books")
            total_books = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM loans WHERE return_date IS NULL"
            )
            borrowed = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM loans
                WHERE return_date IS NULL AND due_date < NOW()
                """
            )
            overdue = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT
                    s.full_name,
                    b.title,
                    l.borrow_date,
                    l.due_date,
                    l.return_date
                FROM loans l
                JOIN students s ON s.id = l.student_id
                JOIN books b ON b.id = l.book_id
                ORDER BY l.borrow_date DESC
                LIMIT 8
                """
            )
            activities = cursor.fetchall()

        except Exception as error:
            messagebox.showerror(
                "Dashboard Error",
                f"Could not load dashboard data:\n{error}"
            )
            return

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

        self.button(
            self.content, "Log Out", self.show_login,
            color=BTN_RED, icon="logout", width=130, height=40
        ).pack(side="bottom", anchor="w", pady=(14, 0))

        # title + search
        top = self.flat(self.content)
        top.pack(fill="x", pady=(0, 14))

        titles = self.flat(top)
        titles.pack(side="left")
        self.label(titles, "Smart Library", size=28, bold=True).pack(anchor="w")
        self.label(
            titles, f"Welcome, {librarian['name']}", size=14, color=TXT_MUTED
        ).pack(anchor="w")

        search_box = self.flat(top)
        search_box.pack(side="right", anchor="n")
        catalog_search = self.entry(
            search_box, "Search catalog by title or RFID UID",
            width=330, height=40
        )

        def open_catalog_search(_event=None):
            self.pending_catalog_search = catalog_search.get().strip()
            self.show_page("Book Catalog", librarian)

        catalog_search.bind("<Return>", open_catalog_search)
        self.button(
            search_box, "", open_catalog_search, color=BTN_NAVY,
            icon="search", width=44, height=40
        ).pack(side="right", padx=(10, 0))
        catalog_search.pack(side="right")

        # statistic cards 
        stats_row = self.flat(self.content)
        stats_row.pack(fill="x", pady=(0, 14))

        statistics = [
            ("TOTAL BOOKS", total_books, TXT, None, "book", BTN_BLUE),
            ("BORROWED", borrowed, "#2F7DE1", "Borrowed", "user", BTN_BLUE),
            ("OVERDUE", overdue, "#D93636", "Overdue", "alert", BTN_RED)
        ]

        for index, (title, value, value_color, target, icon, icon_fill) in enumerate(statistics):
            stat = self.card(stats_row, radius=16)
            stat.pack(
                side="left", fill="both", expand=True,
                padx=(0 if index == 0 else 7, 0 if index == 2 else 7)
            )
            inner = self.flat(stat)
            inner.pack(anchor="w", padx=22, pady=18)

            icon_widget = GlassIcon(inner, self, icon, size=46, fill=icon_fill)
            icon_widget.pack(side="left", padx=(0, 18))

            text_box = self.flat(inner)
            text_box.pack(side="left")
            title_label = self.label(
                text_box, title, size=12, bold=True, color=TXT_MUTED
            )
            title_label.pack(anchor="w")
            value_label = self.label(
                text_box, str(value), size=28, bold=True, color=value_color
            )
            value_label.pack(anchor="w")

            if target:
                for widget in (stat, inner, icon_widget, text_box,
                               title_label, value_label):
                    widget.configure(cursor="hand2")
                    widget.bind(
                        "<Button-1>",
                        lambda _event, page=target:
                        self.show_page(page, librarian)
                    )

        # quick actions
        actions = self.flat(self.content)
        actions.pack(fill="x", pady=(0, 14))

        for label, page, color, icon in (
            ("Borrow Book", "Borrow Book", BTN_BLUE, "plus_circle"),
            ("Return Book", "Return Book", BTN_TEAL, "swap"),
            ("Book Catalog", "Book Catalog", BTN_NAVY, "book")
        ):
            self.button(
                actions, label,
                lambda target=page: self.show_page(target, librarian),
                color=color, icon=icon, width=150, height=42
            ).pack(side="left", padx=(0, 12))

        for label, page, color, icon in (
            ("Add Book", "Add Book", BTN_INDIGO, "plus"),
            ("Register Student", "Register Student", BTN_PURPLE, "user_plus")
        ):
            self.button(
                actions, label,
                lambda target=page: self.show_page(target, librarian),
                color=color, icon=icon, width=165, height=42
            ).pack(side="right", padx=(12, 0))

        # recent activity
        activity_card = self.card(self.content, radius=16)
        activity_card.pack(fill="both", expand=True)

        heading = self.flat(activity_card)
        heading.pack(fill="x", padx=18, pady=(14, 10))
        GlassIcon(
            heading, self, "clock", size=24, color=TXT, circle=False
        ).pack(side="left", padx=(0, 10))
        self.label(
            heading, "Recent Activity", size=18, bold=True
        ).pack(side="left")
        self.button(
            heading, "View History",
            lambda: self.show_page("Borrowing History", librarian),
            color=BTN_NAVY, icon="chevron", icon_right=True, width=130, height=34
        ).pack(side="right")

        activity_frame = self.table_card(
            activity_card, padx=14, pady=(0, 14)
        )

        rows = []
        for student, book, borrow_date, due_date, return_date in activities:
            if return_date is not None:
                status = "Returned"
            elif due_date < datetime.now():
                status = "Overdue"
            else:
                status = "Borrowed"
            rows.append(
                (student, book, str(borrow_date), str(due_date), status)
            )

        self.fill_table(
            activity_frame,
            ["Student", "Book", "Borrow Date", "Due Date", "Status"],
            rows,
            status_col=4,
            empty_text="No borrowing activity yet.",
            wrap=200
        )

    def create_rfid_indicator(
        self,
        parent,
        entry,
        instruction,
        title="RFID SCAN",
        detected_text="RFID UID detected",
        waiting_text="Waiting for RFID scan",
        is_detected=None
    ):
        indicator = self.card(parent, radius=16, width=230, height=10)
        indicator.pack_propagate(False)

        self.label(
            indicator, title, size=14, bold=True, color=TXT
        ).pack(pady=(30, 10))

        status = self.label(
            indicator, waiting_text, size=16, bold=True, color=TXT_MUTED,
            wrap=190, justify="center"
        )
        status.pack(expand=True, padx=15)

        self.label(
            indicator, instruction, size=12, color=TXT_MUTED,
            wrap=190, justify="center"
        ).pack(padx=15, pady=(0, 26))

        validation_job = None

        def update_status(_=None):
            nonlocal validation_job

            if validation_job is not None:
                try:
                    indicator.after_cancel(validation_job)
                except TclError:
                    pass
                validation_job = None

            if is_detected is not None:
                status.configure(text=waiting_text, text_color=TXT_MUTED)
                validation_job = indicator.after(300, validate_status)
                return

            detected = (
                bool(entry.get().strip())
            )
            if detected:
                status.configure(text=detected_text, text_color=GREEN)
            else:
                status.configure(text=waiting_text, text_color=TXT_MUTED)

        def validate_status():
            nonlocal validation_job
            validation_job = None

            try:
                detected = is_detected()
            except MySQLError as error:
                print(f"RFID validation failed: {error}")
                status.configure(
                    text="Unable to verify", text_color=BTN_RED
                )
                return

            if detected:
                status.configure(text=detected_text, text_color=GREEN)
            else:
                status.configure(text=waiting_text, text_color=TXT_MUTED)

        entry.bind("<KeyRelease>", update_status)
        return update_status, indicator

    @staticmethod
    def is_valid_rfid_uid(uid):
        hexadecimal_uid = re.sub(r"[\s:-]", "", uid.strip())
        return (
            len(hexadecimal_uid) in {8, 14, 20}
            and all(character in "0123456789ABCDEFabcdef"
                    for character in hexadecimal_uid)
        )

    def registration_rfid_is_available(self, uid):
        if not self.is_valid_rfid_uid(uid):
            return False

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor()
            return self.find_registered_rfid(cursor, uid) is None
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def registered_rfid_exists(self, uid):
        if not self.is_valid_rfid_uid(uid):
            return False

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor()
            return self.find_registered_rfid(cursor, uid) is not None
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def student_identifier_exists(self, identifier):
        identifier = identifier.strip()
        if not identifier:
            return False

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id
                FROM students
                WHERE UPPER(TRIM(student_no)) = UPPER(%s)
                   OR LOWER(TRIM(full_name)) = LOWER(%s)
                   OR UPPER(TRIM(rfid_uid)) = UPPER(%s)
                LIMIT 1
                """,
                (identifier, identifier, identifier)
            )
            return cursor.fetchone() is not None
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def show_add_book(self):
        layout = self.flat(self.content)
        layout.pack(fill="x", pady=(0, 8))

        form = self.card(layout, radius=16)

        self.label(
            form, "Book Information", size=20, bold=True
        ).pack(anchor="w", padx=26, pady=(22, 14))

        self.book_title_entry = self.entry(form, "Book Title", width=440, height=42)
        self.book_title_entry.pack(anchor="w", padx=26, pady=7)

        self.book_genre_entry = self.entry(
            form, "Genre (e.g. Programming)", width=440, height=42
        )
        self.book_genre_entry.pack(anchor="w", padx=26, pady=7)

        self.book_shelf_entry = self.entry(
            form, "Shelf Location (e.g. A-01)", width=440, height=42
        )
        self.book_shelf_entry.pack(anchor="w", padx=26, pady=7)

        self.book_rfid_entry = self.entry(form, "RFID UID", width=440, height=42)
        self.book_rfid_entry.pack(anchor="w", padx=26, pady=7)

        self.book_rfid_indicator_update, indicator = (
            self.create_rfid_indicator(
                layout,
                self.book_rfid_entry,
                "Scan a book tag into the RFID UID field.",
                is_detected=lambda: self.registration_rfid_is_available(
                    self.book_rfid_entry.get()
                )
            )
        )

        button_row = self.flat(form)
        button_row.pack(anchor="w", padx=26, pady=(20, 26))
        self.button(
            button_row, "Save Book", self.save_book,
            color=BTN_BLUE, icon="plus", width=170, height=44
        ).pack(side="left", padx=(0, 12))
        self.button(
            button_row, "Cancel", self.cancel_add_book,
            color=BTN_RED, width=130, height=44
        ).pack(side="left")

        indicator.pack(side="left", fill="y", padx=(0, 14))
        form.pack(side="left", fill="both", expand=True)

    def cancel_add_book(self):
        self.book_title_entry.delete(0, "end")
        self.book_genre_entry.delete(0, "end")
        self.book_shelf_entry.delete(0, "end")
        self.book_rfid_entry.delete(0, "end")
        self.book_rfid_indicator_update()
        self.send_lcd_message("BOOK CANCELLED", "")

    def find_registered_rfid(self, cursor, rfid_uid):
        cursor.execute(
            """
            SELECT 'student' AS record_type
            FROM students
            WHERE UPPER(TRIM(rfid_uid)) = %s
            UNION ALL
            SELECT 'book' AS record_type
            FROM books
            WHERE UPPER(TRIM(rfid_uid)) = %s
            LIMIT 1
            """,
            (rfid_uid.upper(), rfid_uid.upper())
        )
        record = cursor.fetchone()
        return record[0] if record else None

    def save_book(self):
        title = self.book_title_entry.get().strip()
        genre = self.book_genre_entry.get().strip()
        shelf = self.book_shelf_entry.get().strip()
        rfid_uid = self.book_rfid_entry.get().strip()

        if not title or not rfid_uid:
            messagebox.showwarning(
                "Missing Information",
                "Book title and RFID UID are required."
            )
            return

        if not self.is_valid_rfid_uid(rfid_uid):
            messagebox.showwarning(
                "Invalid RFID UID",
                "Enter or scan a valid RFID UID before saving the book."
            )
            return

        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor()

            registered_type = self.find_registered_rfid(cursor, rfid_uid)
            if registered_type:
                messagebox.showwarning(
                    "RFID Already Registered",
                    "This RFID UID is already registered to a "
                    f"{registered_type}. Use a unique RFID tag."
                )
                return

            cursor.execute(
                """
                INSERT INTO books (title, genre, shelf, rfid_uid)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    title,
                    genre or None,
                    shelf or None,
                    rfid_uid.upper()
                )
            )

            connection.commit()
            self.send_lcd_message("BOOK ADDED", title)

            messagebox.showinfo(
                "Success",
                "Book added successfully!"
            )

            self.book_title_entry.delete(0, "end")
            self.book_genre_entry.delete(0, "end")
            self.book_shelf_entry.delete(0, "end")
            self.book_rfid_entry.delete(0, "end")
            self.book_rfid_indicator_update()

        except Exception as error:
            if connection and connection.is_connected():
                connection.rollback()

            messagebox.showerror(
                "Unable to Add Book",
                "Could not save the book.\n"
                "Check whether the RFID UID is already registered.\n\n"
                f"Details: {error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

                
    def show_student_accounts(self):
        layout = self.flat(self.content)
        layout.pack(fill="x", pady=(0, 8))

        form = self.card(layout, radius=16)

        self.label(
            form, "Student Information", size=20, bold=True
        ).pack(anchor="w", padx=26, pady=(18, 10))

        self.student_no_entry = self.entry(
            form, "Student Number", width=440, height=38
        )
        self.student_no_entry.pack(anchor="w", padx=26, pady=4)

        self.student_name_entry = self.entry(
            form, "Full Name", width=440, height=38
        )
        self.student_name_entry.pack(anchor="w", padx=26, pady=4)

        self.student_phone_entry = self.entry(
            form, "Phone Number (optional)", width=440, height=38
        )
        self.student_phone_entry.pack(anchor="w", padx=26, pady=4)

        self.student_email_entry = self.entry(
            form, "Email (required)", width=440, height=38
        )
        self.student_email_entry.pack(anchor="w", padx=26, pady=4)

        self.student_rfid_entry = self.entry(
            form, "RFID UID", width=440, height=38
        )
        self.student_rfid_entry.pack(anchor="w", padx=26, pady=4)

        self.student_rfid_indicator_update, indicator = (
            self.create_rfid_indicator(
                layout,
                self.student_rfid_entry,
                "Scan a student card into the RFID UID field.",
                is_detected=lambda: self.registration_rfid_is_available(
                    self.student_rfid_entry.get()
                )
            )
        )

        button_row = self.flat(form)
        button_row.pack(anchor="w", padx=26, pady=(14, 18))
        self.button(
            button_row, "Register Student", self.save_student,
            color=BTN_PURPLE, icon="user_plus", width=190, height=44
        ).pack(side="left", padx=(0, 12))
        self.button(
            button_row, "Cancel", self.cancel_student_registration,
            color=BTN_RED, width=130, height=44
        ).pack(side="left")

        indicator.pack(side="left", fill="y", padx=(0, 14))
        form.pack(side="left", fill="both", expand=True)

        section = self.card(self.content, radius=16)
        section.pack(fill="both", expand=True, pady=(12, 0))
        self.label(
            section, "Registered Students", size=18, bold=True
        ).pack(anchor="w", padx=18, pady=(12, 8))

        self.student_list = self.table_card(section, padx=14, pady=(0, 14))

        self.load_students()

    def cancel_student_registration(self):
        self.student_no_entry.delete(0, "end")
        self.student_name_entry.delete(0, "end")
        self.student_phone_entry.delete(0, "end")
        self.student_email_entry.delete(0, "end")
        self.student_rfid_entry.delete(0, "end")
        self.student_rfid_indicator_update()
        self.send_lcd_message("STUDENT CANCEL", "")

    def ensure_student_phone_column(self, cursor):
        cursor.execute("SHOW COLUMNS FROM students LIKE 'phone'")
        if cursor.fetchone() is None:
            cursor.execute(
                "ALTER TABLE students ADD COLUMN phone VARCHAR(20) NOT NULL DEFAULT ''"
            )

    def save_student(self):
        student_no = self.student_no_entry.get().strip()
        full_name = self.student_name_entry.get().strip()
        phone = self.student_phone_entry.get().strip()
        email = self.student_email_entry.get().strip()
        rfid_uid = self.student_rfid_entry.get().strip()

        if not student_no or not full_name or not email or not rfid_uid:
            messagebox.showwarning(
                "Missing Information",
                "Student number, full name, email, and RFID UID are required."
            )
            return

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            messagebox.showwarning(
                "Invalid Email",
                "Enter a valid email address."
            )
            return

        if not self.is_valid_rfid_uid(rfid_uid):
            messagebox.showwarning(
                "Invalid RFID UID",
                "Enter or scan a valid RFID UID before registering the student."
            )
            return

        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor()

            registered_type = self.find_registered_rfid(cursor, rfid_uid)
            if registered_type:
                messagebox.showwarning(
                    "RFID Already Registered",
                    "This RFID UID is already registered to a "
                    f"{registered_type}. Use a unique RFID tag."
                )
                return

            self.ensure_student_phone_column(cursor)

            cursor.execute(
                """
                INSERT INTO students
                    (student_no, full_name, phone, email, rfid_uid)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (student_no, full_name, phone or "", email, rfid_uid.upper())
            )
            connection.commit()
            self.send_lcd_message("STUDENT ADDED", full_name)

            messagebox.showinfo(
                "Success",
                "Student registered successfully!"
            )

            self.student_no_entry.delete(0, "end")
            self.student_name_entry.delete(0, "end")
            self.student_phone_entry.delete(0, "end")
            self.student_email_entry.delete(0, "end")
            self.student_rfid_entry.delete(0, "end")
            self.student_rfid_indicator_update()

            self.load_students()

        except Exception as error:
            if connection and connection.is_connected():
                connection.rollback()

            messagebox.showerror(
                "Registration Failed",
                "Could not register student. The student number "
                "or RFID UID may already exist.\n\n"
                f"Details: {error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def load_students(self):
        for widget in self.student_list.winfo_children():
            widget.destroy()

        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor()
            self.ensure_student_phone_column(cursor)

            cursor.execute(
                """
                SELECT student_no, full_name, phone, email, rfid_uid
                FROM students
                ORDER BY full_name
                """
            )
            students = cursor.fetchall()

            self.fill_table(
                self.student_list,
                [
                    "Student Number", "Full Name", "Phone Number",
                    "Email", "RFID UID"
                ],
                students,
                empty_text="No students registered yet.",
                wrap=170
            )

        except Exception as error:
            messagebox.showerror(
                "Database Error",
                f"Could not load students:\n{error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

                
    def show_book_catalog(self):
        toolbar = self.flat(self.content)
        toolbar.pack(fill="x", pady=(0, 12))

        self.book_search_entry = self.entry(
            toolbar, "Search by title or RFID UID", width=360, height=40
        )
        self.book_search_entry.pack(
            side="left", fill="x", expand=True, padx=(0, 10)
        )
        self.book_search_entry.bind(
            "<Return>", lambda event: self.load_book_catalog()
        )

        self.button(
            toolbar, "Search", self.load_book_catalog,
            color=BTN_BLUE, icon="search", width=110, height=40
        ).pack(side="left", padx=(0, 10))

        self.book_status_filter = GlassCombo(
            toolbar, self,
            values=["All statuses", "Available", "Borrowed"],
            width=150, height=40,
            command=lambda selected: self.load_book_catalog()
        )
        self.book_status_filter.set("All statuses")
        self.book_status_filter.pack(side="left", padx=(0, 10))

        self.button(
            toolbar, "Show All", self.clear_book_search,
            color=BTN_GHOST, width=110, height=40
        ).pack(side="left")

        self.book_catalog_frame = self.table_card(self.content)

        pending_search = getattr(self, "pending_catalog_search", "")
        if pending_search:
            self.book_search_entry.insert(0, pending_search)
        self.pending_catalog_search = ""

        self.load_book_catalog()

    def clear_book_search(self):
        self.book_search_entry.delete(0, "end")
        self.book_status_filter.set("All statuses")
        self.load_book_catalog()

    def load_book_catalog(self):
        for widget in self.book_catalog_frame.winfo_children():
            widget.destroy()

        search_text = self.book_search_entry.get().strip()
        status_filter = self.book_status_filter.get()

        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor()

            query = """
                SELECT
                    b.title,
                    b.rfid_uid,
                    b.shelf,
                    CASE
                        WHEN EXISTS (
                            SELECT 1
                            FROM loans l
                            WHERE l.book_id = b.id
                              AND l.return_date IS NULL
                        )
                        THEN 'Borrowed'
                        ELSE 'Available'
                    END AS book_status
                FROM books b
                WHERE (
                    b.title LIKE %s
                    OR b.rfid_uid LIKE %s
                )
            """

            search_pattern = f"%{search_text}%"
            parameters = [search_pattern, search_pattern]

            if status_filter == "Available":
                query += """
                    AND NOT EXISTS (
                        SELECT 1
                        FROM loans l
                        WHERE l.book_id = b.id
                          AND l.return_date IS NULL
                    )
                """
            elif status_filter == "Borrowed":
                query += """
                    AND EXISTS (
                        SELECT 1
                        FROM loans l
                        WHERE l.book_id = b.id
                          AND l.return_date IS NULL
                    )
                """

            cursor.execute(query + " ORDER BY b.title", tuple(parameters))

            books = cursor.fetchall()

            self.fill_table(
                self.book_catalog_frame,
                ["Title", "RFID UID", "Shelf", "Status"],
                books,
                weights=[3, 2, 1, 1],
                status_col=3,
                empty_text="No matching books found.",
                wrap=240
            )

        except Exception as error:
            messagebox.showerror(
                "Book Catalog Error",
                f"Could not load books:\n{error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

                
    
    def show_borrow_book(self):
        self.borrow_student_entry = None
        self.borrow_book_combo = None
        self.borrow_student_no = None
        self.available_book_map = {}

        layout = self.flat(self.content)
        layout.pack(fill="x", pady=(0, 6))

        form = self.card(layout, radius=16)

        self.label(
            form, "Student Name or Student Number", size=13, bold=True
        ).pack(anchor="w", padx=22, pady=(18, 6))
        student_entry = self.entry(
            form, "Scan student RFID card", width=400, height=40
        )
        student_entry.pack(anchor="w", padx=22, pady=(0, 10))
        self.borrow_student_entry = student_entry

        self.borrow_rfid_indicator_update, indicator = (
            self.create_rfid_indicator(
                layout,
                student_entry,
                "Scan the student's RFID card.",
                title="RFID / STUDENT ID",
                detected_text="Student recognized",
                is_detected=lambda: self.student_identifier_exists(
                    student_entry.get()
                )
            )
        )

        self.label(
            form, "Book (scan RFID tag)", size=13, bold=True
        ).pack(anchor="w", padx=22, pady=(0, 6))
        book_entry = self.entry(
            form, "Scan book RFID tag", width=400, height=40
        )
        book_entry.pack(anchor="w", padx=22, pady=(0, 10))
        self.borrow_book_combo = book_entry

        self.label(
            form, "Loan Duration (1–7 days)", size=13, bold=True
        ).pack(anchor="w", padx=22, pady=(0, 6))
        duration_entry = self.entry(
            form, "Enter number of days (1–7)", width=400, height=40
        )
        duration_entry.pack(anchor="w", padx=22, pady=(0, 14))
        self.borrow_duration_entry = duration_entry

        button_row = self.flat(form)
        button_row.pack(anchor="w", padx=22, pady=(0, 20))
        self.button(
            button_row, "Confirm Borrow",
            lambda: self.borrow_book(student_entry, book_entry, duration_entry),
            color=BTN_BLUE, icon="plus_circle", width=180, height=42
        ).pack(side="left", padx=(0, 12))
        self.button(
            button_row, "Cancel Borrow", self.cancel_borrow,
            color=BTN_RED, width=150, height=42
        ).pack(side="left")

        indicator.pack(side="left", fill="y", padx=(0, 14))
        form.pack(side="left", fill="both", expand=True)

        section = self.card(self.content, radius=16)
        section.pack(fill="both", expand=True, pady=(12, 0))
        self.label(
            section, "Available Books", size=18, bold=True
        ).pack(anchor="w", padx=18, pady=(12, 8))

        self.available_books_frame = self.table_card(
            section, padx=14, pady=(0, 14)
        )

        self.load_available_books()

    def cancel_borrow(self):
        """Clear the current borrow form without saving a loan."""
        if self.borrow_student_entry and self.borrow_student_entry.winfo_exists():
            self.borrow_student_entry.delete(0, "end")

        if self.borrow_book_combo and self.borrow_book_combo.winfo_exists():
            self.set_borrow_book_selection("")

        if hasattr(self, "borrow_duration_entry"):
            if self.borrow_duration_entry and self.borrow_duration_entry.winfo_exists():
                self.borrow_duration_entry.delete(0, "end")

        self.borrow_student_no = None

        if hasattr(self, "borrow_rfid_indicator_update"):
            self.borrow_rfid_indicator_update()

        self.send_lcd_message("BORROW CANCELLED", "")
        print("Borrow form cleared. No loan was saved.")

    def set_borrow_book_selection(self, display):
        book_entry = getattr(self, "borrow_book_combo", None)
        if book_entry is None or not book_entry.winfo_exists():
            return

        book_entry.delete(0, "end")
        if display:
            book_entry.insert(0, display)

    def load_available_books(self):
        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute("""
                SELECT b.id, b.title, b.shelf
                FROM books b
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM loans l
                    WHERE l.book_id = b.id
                      AND l.return_date IS NULL
                )
                ORDER BY b.title
            """)

            books = cursor.fetchall()
            self.available_book_map = {}
            rows = []

            for book_id, title, shelf in books:
                display = f"{book_id} | {title} | Shelf: {shelf or 'N/A'}"
                self.available_book_map[display] = book_id
                rows.append((title, shelf or "N/A"))

            frame = getattr(self, "available_books_frame", None)
            if frame is not None and frame.winfo_exists():
                self.fill_table(
                    frame, ["Title", "Shelf"], rows, [3, 1],
                    empty_text="No available books."
                )

            self.set_borrow_book_selection("")

        except Exception as error:
            messagebox.showerror(
                "Database Error",
                f"Could not load available books:\n{error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def borrow_book(self, student_entry, book_entry, duration_entry):
        student_identifier = student_entry.get().strip()
        selected_book = book_entry.get().strip()
        duration_text = duration_entry.get().strip()

        if not student_identifier:
            messagebox.showwarning(
                "Missing Student",
                "Enter the student's number or RFID UID."
            )
            return

        if selected_book not in self.available_book_map:
            messagebox.showwarning(
                "No Book Selected",
                "Scan an available book's RFID tag."
            )
            return

        try:
            days = int(duration_text)
        except ValueError:
            messagebox.showwarning(
                "Invalid Duration",
                "Enter a whole number from 1 to 7."
            )
            return

        if not 1 <= days <= 7:
            messagebox.showwarning(
                "Invalid Duration",
                "Loan duration must be between 1 and 7 days."
            )
            return

        book_id = self.available_book_map[selected_book]
        connection = None
        cursor = None

        try:
            connection = get_connection()
            connection.start_transaction()
            cursor = connection.cursor()

            cursor.execute("""
                SELECT id, full_name, email
                FROM students
                WHERE UPPER(TRIM(student_no)) = UPPER(%s)
                   OR LOWER(TRIM(full_name)) = LOWER(%s)
                   OR UPPER(TRIM(rfid_uid)) = UPPER(%s)
                LIMIT 1
            """, (student_identifier, student_identifier, student_identifier))

            student = cursor.fetchone()

            if not student:
                connection.rollback()
                self.send_lcd_message("STUDENT NOT FOUND", "")
                messagebox.showerror(
                    "Student Not Found",
                    "No student matches that student number or RFID UID."
                )
                return

            student_id, student_name, student_email = student

            # Check again in case another loan was created after loading.
            cursor.execute("""
                SELECT id
                FROM books
                WHERE id = %s
                FOR UPDATE
            """, (book_id,))

            if not cursor.fetchone():
                connection.rollback()
                messagebox.showerror(
                    "Book Not Found",
                    "This book no longer exists."
                )
                return

            cursor.execute("""
                SELECT id
                FROM loans
                WHERE book_id = %s
                AND return_date IS NULL
                LIMIT 1
            """, (book_id,))

            if cursor.fetchone():
                connection.rollback()
                title = selected_book.split(" | ", 2)[1]
                self.send_lcd_message("BOOK BORROWED", title)
                messagebox.showwarning(
                    "Book Unavailable",
                    "This book has already been borrowed. Refresh the list."
                )
                self.load_available_books()
                return

            borrow_date = datetime.now()
            due_date = borrow_date + timedelta(days=days)

            cursor.execute("""
                INSERT INTO loans
                    (student_id, book_id, borrow_date,
                     due_date, return_date, penalty)
                VALUES (%s, %s, %s, %s, NULL, 0)
            """, (student_id, book_id, borrow_date, due_date))

            connection.commit()
            book_title = selected_book.split(" | ", 2)[1]
            self.send_lcd_message("BORROW SUCCESS", book_title)
            email_result = self.send_receipt(
                student_email,
                "Book borrowing receipt",
                f"Hello {student_name},\n\n"
                f"You borrowed '{book_title}'.\n"
                f"Borrow date: {borrow_date:%Y-%m-%d %H:%M}\n"
                f"Due date: {due_date:%Y-%m-%d %H:%M}\n\n"
                "Please return the book by its due date.\n\n"
                "Smart Library System"
            )

            messagebox.showinfo(
                "Borrow Successful",
                f"Student: {student_name}\n"
                f"Borrow duration: {days} day(s)\n"
                f"Borrow date: {borrow_date:%Y-%m-%d}\n"
                f"Due date: {due_date:%Y-%m-%d}\n\n"
                f"{email_result}"
            )

            student_entry.delete(0, "end")
            duration_entry.delete(0, "end")
            self.borrow_rfid_indicator_update()

            self.load_available_books()

        except Exception as error:
            if connection and connection.is_connected():
                connection.rollback()

            messagebox.showerror(
                "Borrowing Error",
                f"Could not process the loan:\n{error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

                
    def show_return_book(self):
        self.borrow_student_entry = None
        self.borrow_book_combo = None
        self.return_book_rfid_entry = None

        parent = self.content


        layout = self.flat(parent)
        layout.pack(fill="x", pady=(0, 6))

        selection_panel = self.card(layout, radius=16)

        self.label(
            selection_panel, "Student or Book RFID UID", size=13, bold=True
        ).pack(anchor="w", padx=20, pady=(18, 6))

        self.return_book_rfid_entry = self.entry(
            selection_panel,
            "Scan or enter a student or book RFID UID",
            width=460, height=40
        )
        self.return_book_rfid_entry.pack(anchor="w", padx=20, pady=(0, 10))
        self.return_book_rfid_entry.bind(
            "<Return>", lambda event: self.lookup_active_return_book()
        )

        self.active_return_loan_id = None
        self.return_rfid_indicator_update, indicator = (
            self.create_rfid_indicator(
                layout,
                self.return_book_rfid_entry,
                "Scan a student card or book tag to find its active loan.",
                detected_text="RFID received",
                is_detected=lambda: self.registered_rfid_exists(
                    self.return_book_rfid_entry.get()
                )
            )
        )

        self.return_preview_values = {}
        for key, label in (
            ("student", "Student"),
            ("book", "Book"),
            ("due_date", "Due Date")
        ):
            preview = self.card(selection_panel, radius=12)
            preview.pack(fill="x", padx=20, pady=5)

            self.label(
                preview, label, size=11, bold=True, color=TXT_MUTED
            ).pack(anchor="w", padx=14, pady=(9, 0))

            self.return_preview_values[key] = self.label(
                preview, "—", size=14, bold=True, wrap=480
            )
            self.return_preview_values[key].pack(
                anchor="w", padx=14, pady=(2, 10)
            )

        self.return_due_status = self.label(
            selection_panel, "", size=12, bold=True,
            color=TXT_MUTED, wrap=480
        )
        self.return_due_status.pack(anchor="w", padx=20, pady=(6, 8))

        return_button_row = self.flat(selection_panel)
        return_button_row.pack(anchor="w", padx=20, pady=(4, 18))

        self.button(
            return_button_row, "Confirm Return", self.process_return,
            color=BTN_TEAL, icon="swap", width=190, height=42
        ).pack(side="left", padx=(0, 12))
        self.button(
            return_button_row, "Cancel Return",
            lambda: self.reset_return_form(cancelled=True),
            color=BTN_RED, width=150, height=42
        ).pack(side="left")

        indicator.pack(side="left", fill="y", padx=(0, 14))
        selection_panel.pack(side="left", fill="both", expand=True)

    def reset_return_form(self, cancelled=False):
        self.active_return_loan_id = None
        self.return_student_id = None

        if self.return_book_rfid_entry.winfo_exists():
            self.return_book_rfid_entry.delete(0, "end")

        self.return_rfid_indicator_update()
        self.update_return_preview(None)

        self.return_due_status.configure(text="")
        if cancelled:
            self.send_lcd_message("RETURN CANCELLED", "")


    def update_return_preview(self, loan_details, student_name=None):
        if not loan_details:
            self.return_preview_values["student"].configure(
                text=student_name or "—"
            )
            self.return_preview_values["book"].configure(text="—")
            self.return_preview_values["due_date"].configure(text="—")
            self.return_due_status.configure(text="")
            return

        _, student_name, book_title, due_date = loan_details
        self.return_preview_values["student"].configure(text=student_name)
        self.return_preview_values["book"].configure(text=book_title)
        self.return_preview_values["due_date"].configure(
            text=due_date.strftime("%b %d, %Y")
            if hasattr(due_date, "strftime") else str(due_date)
        )

        due_day = due_date.date() if isinstance(due_date, datetime) else due_date
        today = datetime.now().date()
        if due_day < today:
            days_overdue = (today - due_day).days
            status = f"Overdue by {days_overdue} day(s)"
            color = "#F85149"
        elif due_day == today:
            status = "Due today"
            color = "#FF0101"
        else:
            days_remaining = (due_day - today).days
            status = f"{days_remaining} day(s) until due"
            color = "#3FB950"

        self.return_due_status.configure(text=status, text_color=color)

    def lookup_active_return_book(self):
        rfid_uid = self.return_book_rfid_entry.get().strip().upper()
        self.active_return_loan_id = None
        self.update_return_preview(None)

        if not rfid_uid:
            messagebox.showwarning(
                "Missing RFID",
                "Scan or enter a student or book RFID UID first."
            )
            return

        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute("""
                SELECT id, full_name
                FROM students
                WHERE UPPER(rfid_uid) = %s
                LIMIT 1
            """, (rfid_uid,))
            student = cursor.fetchone()

            if student:
                student_id, student_name = student
                self.update_return_preview(None, student_name)

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM loans
                    WHERE student_id = %s
                      AND return_date IS NULL
                """, (student_id,))
                active_loan_count = cursor.fetchone()[0]
                if active_loan_count == 0:
                    self.send_lcd_message("NO ACTIVE LOAN", student_name)
                    messagebox.showwarning(
                        "No Active Loan",
                        f"{student_name} has no active loans."
                    )
                    self.return_due_status.configure(
                        text="This student has no active loans.",
                        text_color="#F85149"
                    )
                    return

                self.return_due_status.configure(
                    text="Student found. Scan the book RFID to view its loan.",
                    text_color="#3FB950"
                )
                return

            cursor.execute("""
                SELECT l.id, s.full_name, b.title, l.due_date
                FROM loans l
                JOIN students s ON s.id = l.student_id
                JOIN books b ON b.id = l.book_id
                WHERE UPPER(b.rfid_uid) = %s
                  AND l.return_date IS NULL
                ORDER BY l.due_date ASC
                LIMIT 1
            """, (rfid_uid,))

            loan = cursor.fetchone()
            if not loan:
                self.send_lcd_message("NO ACTIVE LOAN", rfid_uid)
                messagebox.showwarning(
                    "No Active Loan",
                    "No student or active loan was found for this RFID."
                )
                return

            self.active_return_loan_id = loan[0]
            self.update_return_preview(loan)

        except Exception as error:
            messagebox.showerror(
                "Return Lookup Error",
                f"Could not find an active loan:\n{error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def process_return(self):
        loan_id = self.active_return_loan_id
        if loan_id is None:
            messagebox.showwarning(
                "No Active Loan",
                "Scan or enter a borrowed book's RFID and find its active loan."
            )
            return

        connection = None
        cursor = None

        try:
            connection = get_connection()
            connection.start_transaction()
            cursor = connection.cursor()

            cursor.execute("""
                SELECT l.due_date, s.full_name, b.title, s.email
                FROM loans l
                JOIN students s ON s.id = l.student_id
                JOIN books b ON b.id = l.book_id
                WHERE l.id = %s AND l.return_date IS NULL
                FOR UPDATE
            """, (loan_id,))

            loan = cursor.fetchone()

            if not loan:
                connection.rollback()
                messagebox.showwarning(
                    "Already Returned",
                    "This book no longer has an active loan. Scan it again."
                )
                self.reset_return_form()
                return

            due_date, student_name, book_title, student_email = loan
            returned_at = datetime.now()

            cursor.execute("""
                UPDATE loans
                SET return_date = NOW()
                WHERE id = %s AND return_date IS NULL
            """, (loan_id,))

            connection.commit()
            self.send_lcd_message("RETURN SUCCESS", book_title)
            email_result = self.send_receipt(
                student_email,
                "Book return receipt",
                f"Hello {student_name},\n\n"
                f"You returned '{book_title}'.\n"
                f"Return date: {returned_at:%Y-%m-%d %H:%M}\n"
                f"Original due date: {due_date}\n\n"
                "Thank you for using the library.\n\n"
                "Smart Library System"
            )

            messagebox.showinfo(
                "Return Successful",
                f"Student: {student_name}\n"
                f"Book: {book_title}\n"
                f"Due date: {due_date}\n"
                "The book has been marked as returned.\n\n"
                f"{email_result}"
            )

            self.reset_return_form()

        except Exception as error:
            if connection and connection.is_connected():
                connection.rollback()

            messagebox.showerror(
                "Return Error",
                f"Could not process the return:\n{error}"
            )

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

                
    def show_loan_catalog(self, loan_status):
        is_overdue = loan_status == "Overdue"
        description = (
            "Students with active loans past their due date."
            if is_overdue else
            "Students with books that have not yet been returned. "
            "This list includes overdue loans."
        )

        self.label(
            self.content, description, size=13, color=TXT_MUTED
        ).pack(anchor="w", pady=(0, 12))

        search_bar = self.flat(self.content)
        search_bar.pack(fill="x", pady=(0, 12))

        search_entry = self.entry(
            search_bar, "Search student, phone, email, or book",
            width=380, height=40
        )
        search_entry.pack(side="left", padx=(0, 10))

        loan_frame = self.table_card(self.content)

        def load_loans(_event=None):
            connection = None
            cursor = None

            try:
                connection = get_connection()
                cursor = connection.cursor()
                self.ensure_student_phone_column(cursor)

                search_text = search_entry.get().strip()
                overdue_filter = " AND l.due_date < NOW()" if is_overdue else ""
                search_filter = """
                    AND (
                        s.student_no LIKE %s
                        OR s.full_name LIKE %s
                        OR s.phone LIKE %s
                        OR s.email LIKE %s
                        OR b.title LIKE %s
                    )
                """ if search_text else ""
                search_parameters = (f"%{search_text}%",) * 5 if search_text else ()
                cursor.execute(
                    f"""
                    SELECT
                        s.student_no,
                        s.full_name,
                        s.phone,
                        s.email,
                        b.title,
                        l.borrow_date,
                        l.due_date
                    FROM loans l
                    JOIN students s ON s.id = l.student_id
                    JOIN books b ON b.id = l.book_id
                    WHERE l.return_date IS NULL{overdue_filter}{search_filter}
                    ORDER BY l.due_date ASC, s.full_name ASC
                    """,
                    search_parameters
                )
                loans = cursor.fetchall()

                self.fill_table(
                    loan_frame,
                    [
                        "Student Number", "Student Name", "Phone Number",
                        "Email", "Book", "Borrow Date", "Due Date"
                    ],
                    loans,
                    empty_text=f"No matching {loan_status.lower()} loans found.",
                    wrap=150
                )

            except Exception as error:
                messagebox.showerror(
                    f"{loan_status} Catalog Error",
                    f"Could not load {loan_status.lower()} loans:\n{error}"
                )

            finally:
                if cursor:
                    cursor.close()
                if connection and connection.is_connected():
                    connection.close()

        search_entry.bind("<Return>", load_loans)

        def refresh_loans():
            search_entry.delete(0, "end")
            load_loans()

        self.button(
            search_bar, "Search", load_loans,
            color=BTN_BLUE, icon="search", width=110, height=40
        ).pack(side="left", padx=(0, 10))
        self.button(
            search_bar, "Refresh", refresh_loans,
            color=BTN_GHOST, width=110, height=40
        ).pack(side="left")

        load_loans()

    def show_borrowing_history(self):
        parent = self.content

        toolbar = self.flat(parent)
        toolbar.pack(fill="x", pady=(0, 12))

        search_entry = self.entry(
            toolbar, "Search student or book title", width=380, height=40
        )
        search_entry.pack(side="left", padx=(0, 10))

        status_filter = GlassCombo(
            toolbar,
            self,
            values=["All statuses", "Borrowed", "Overdue", "Returned"],
            width=150,
            height=40,
            command=lambda selected: load_history()
        )
        status_filter.set("All statuses")
        status_filter.pack(side="left", padx=(0, 10))

        history_frame = self.table_card(parent)

        def load_history(_event=None):
            connection = None
            cursor = None

            try:
                connection = get_connection()
                cursor = connection.cursor()

                search_text = search_entry.get().strip()
                selected_status = status_filter.get()

                cursor.execute("""
                    SELECT
                        l.id,
                        s.full_name,
                        b.title,
                        l.borrow_date,
                        l.due_date,
                        l.return_date
                    FROM loans l
                    JOIN students s ON s.id = l.student_id
                    JOIN books b ON b.id = l.book_id
                    WHERE s.full_name LIKE %s
                       OR b.title LIKE %s
                    ORDER BY l.borrow_date DESC, l.id DESC
                """, (
                    f"%{search_text}%",
                    f"%{search_text}%"
                ))

                records = cursor.fetchall()

                rows = []
                for record in records:
                    (
                        loan_id,
                        student_name,
                        book_title,
                        borrow_date,
                        due_date,
                        return_date
                    ) = record

                    if return_date is not None:
                        status = "Returned"
                    elif due_date < datetime.now():
                        status = "Overdue"
                    else:
                        status = "Borrowed"

                    if selected_status != "All statuses" and status != selected_status:
                        continue

                    rows.append((
                        str(loan_id),
                        student_name,
                        book_title,
                        str(borrow_date),
                        str(due_date),
                        str(return_date) if return_date else "Not returned",
                        status
                    ))

                self.fill_table(
                    history_frame,
                    [
                        "Loan ID", "Student", "Book", "Borrow Date",
                        "Due Date", "Return Date", "Status"
                    ],
                    rows,
                    weights=[1, 2, 2, 2, 2, 2, 2],
                    status_col=6,
                    empty_text="No borrowing records found.",
                    wrap=130
                )

            except Exception as error:
                messagebox.showerror(
                    "History Error",
                    f"Could not load borrowing history:\n{error}"
                )

            finally:
                if cursor:
                    cursor.close()
                if connection and connection.is_connected():
                    connection.close()

        search_entry.bind("<Return>", load_history)

        self.button(
            toolbar, "Search", load_history,
            color=BTN_BLUE, icon="search", width=110, height=40
        ).pack(side="left", padx=(0, 10))
        self.button(
            toolbar, "Refresh", load_history,
            color=BTN_GHOST, width=110, height=40
        ).pack(side="left")

        load_history()


if __name__ == "__main__":
    app = SmartLibraryApp()
    app.mainloop()
