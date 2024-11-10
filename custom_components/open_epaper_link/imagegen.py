from __future__ import annotations
import io
import logging
import os
import pprint
import math
import json
from math import radians

import requests
import qrcode
import shutil
import asyncio
import time
import base64
from .const import DOMAIN
from .util import get_image_folder, get_image_path
from PIL import Image, ImageDraw, ImageFont
from requests_toolbelt.multipart.encoder import MultipartEncoder
from homeassistant.exceptions import HomeAssistantError
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.util import dt
from homeassistant.components.recorder import get_instance
from datetime import timedelta, datetime

_LOGGER = logging.getLogger(__name__)

white =  (255, 255, 255,255)
black = (0, 0, 0,255)
red = (255, 0, 0,255)
yellow = (255, 255, 0,255)
queue = []
notsetup = True;
running = False;

# setup
def setup(hass,notsetup):
    if notsetup:
        hass.bus.listen(DOMAIN + "_event", handle_event)
        notsetup = False
    return True
# handle_event
def handle_event(self):
    handlequeue()
# is_decimal
def is_decimal(string):
    if not string:
        return False
    if string.startswith("-"):
        string = string[1:]
    return len(string.split(".")) <= 2 and string.replace(".", "").isdecimal()
# min_max
def min_max(data):
    if not(data):
        raise HomeAssistantError("data error, someting is not in range of the recorder")
    mi, ma = data[0], data[0]
    for d in data[1:]:
        mi = min(mi, d)
        ma = max(ma, d)
    return mi, ma
# img downloader
def downloadimg(entity_id, service, hass):
    entity = hass.states.get(entity_id)
    if not (entity and 'width' in entity.attributes):
        raise HomeAssistantError("id was not found yet, please wait for the display to check in at least once " + entity_id)
    url = service.data.get("url", "")
    rotate = service.data.get("rotation", 0)
    # get image
    response = requests.get(url)
    # load the res of the esl
    res = [hass.states.get(entity_id).attributes['width'], hass.states.get(entity_id).attributes['height']]
    img = Image.open(io.BytesIO(response.content))
    if img.mode != 'RGB':
        img = img.convert('RGB')
    if rotate != 0:
        img = img.rotate(-rotate, expand=1)
    width, height = img.size
    if width != res[0] or height != res[1]:
        img = img.resize((res[0], res[1]))
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality="maximum")
    img.save(os.path.join(os.path.dirname(__file__), entity_id + '.jpg'), format='JPEG', quality="maximum")
    byte_im = buf.getvalue()
    return byte_im
#g et_wrapped_text
def get_wrapped_text(text: str, font: ImageFont.ImageFont,line_length: int):
        lines = ['']
        for word in text.split():
            line = f'{lines[-1]} {word}'.strip()
            if font.getlength(line) <= line_length:
                lines[-1] = line
            else:
                lines.append(word)
        return '\n'.join(lines)
# converts a color name to the corresponding color index for the palette
def getIndexColor(color):
    if color is None:
        return None
    color_str = str(color)
    if color_str == "black" or color_str == "b":
        return black
    elif color_str == "red" or color_str == "r":
        return red
    elif color_str == "yellow" or color_str == "y":
        return yellow
    else:
        return white
# should_show_element
def should_show_element(element):
    return element['visible'] if 'visible' in element else True
# custom image generator
def customimage(entity_id, service, hass):
    payload = service.data.get("payload", "")
    rotate = service.data.get("rotate", 0)
    dither = service.data.get("dither", False)
    background = getIndexColor(service.data.get("background","white"))
    entity = hass.states.get(entity_id)
    if not (entity and 'width' in entity.attributes):
        raise HomeAssistantError("id was not found yet, please wait for the display to check in at least once " + entity_id)
    canvas_width = hass.states.get(entity_id).attributes['width']
    canvas_height = hass.states.get(entity_id).attributes['height']
    if rotate == 0:
        img = Image.new('RGBA', (canvas_width, canvas_height), color=background)
    elif rotate == 90:
        img = Image.new('RGBA', (canvas_height, canvas_width), color=background)
    elif rotate == 180:
        img = Image.new('RGBA', (canvas_width, canvas_height), color=background)
    elif rotate == 270:
        img = Image.new('RGBA', (canvas_height, canvas_width), color=background)
    else:
        img = Image.new('RGBA', (canvas_width, canvas_height), color=background)
    pos_y = 0
    for element in payload:
        _LOGGER.debug("type: " + element["type"])
        if not should_show_element(element):
            continue
        # line
        if element["type"] == "line":
            check_for_missing_required_arguments(element, ["x_start", "x_end"], "line")
            img_line = ImageDraw.Draw(img)
            if "y_start" not in element:
                y_start = pos_y + element.get("y_padding", 0)
                y_end = y_start
            else:
                y_start = element["y_start"]
                y_end = element["y_end"]

            fill = getIndexColor(element['fill']) if 'fill' in element else black
            width = element['width'] if 'width' in element else 1

            img_line.line([(element['x_start'], y_start), (element['x_end'], y_end)], fill=fill, width=width)
            pos_y = y_start
        # rectangle
        if element["type"] == "rectangle":
            check_for_missing_required_arguments(element, ["x_start", "x_end", "y_start", "y_end"], "rectangle")
            img_rect = ImageDraw.Draw(img)
            rect_fill = getIndexColor(element['fill']) if 'fill' in element else None
            rect_outline = getIndexColor(element['outline']) if 'outline' in element else "black"
            rect_width = element['width'] if 'width' in element else 1
            radius = element['radius'] if 'radius' in element else 10 if 'corners' in element else 0
            corners = rounded_corners(element['corners']) if 'corners' in element else rounded_corners("all") if 'radius' in element else (False, False, False, False)

            img_rect.rounded_rectangle([(element['x_start'], element['y_start']), (element['x_end'], element['y_end'])],
                               fill=rect_fill, outline=rect_outline, width=rect_width, radius=radius, corners=corners)
        # rectangle pattern
        if element["type"] == "rectangle_pattern":
            check_for_missing_required_arguments(element, ["x_start", "x_size",
                                                           "y_start", "y_size",
                                                           "x_repeat", "y_repeat",
                                                           "x_offset", "y_offset"], "rectangle_pattern")
            img_rect_pattern = ImageDraw.Draw(img)
            fill = getIndexColor(element['fill']) if 'fill' in element else None
            outline = getIndexColor(element['outline']) if 'outline' in element else "black"
            width = element['width'] if 'width' in element else 1
            radius = element['radius'] if 'radius' in element else 10 if 'corners' in element else 0
            corners = rounded_corners(element['corners']) if 'corners' in element else rounded_corners("all") if 'radius' in element else (False, False, False, False)

            for x in range(element["x_repeat"]):
                for y in range(element["y_repeat"]):
                    img_rect_pattern.rounded_rectangle([(element['x_start'] + x * (element['x_offset'] + element['x_size']),
                                                 element['y_start'] + y * (element['y_offset'] + element['y_size'])),
                                                (element['x_start'] + x * (element['x_offset'] + element['x_size'])
                                                 + element['x_size'], element['y_start'] + y * (element['y_offset']
                                                 + element['y_size'])+element['y_size'])],
                                               fill=fill, outline=outline, width=width, radius=radius, corners=corners)

        # circle
        if element["type"] == "circle":
            check_for_missing_required_arguments(element, ["x", "y", "radius"], "circle")
            img_circle = ImageDraw.Draw(img)
            fill = getIndexColor(element['fill']) if 'fill' in element else None
            outline = getIndexColor(element['outline']) if 'outline' in element else "black"
            width = element['width'] if 'width' in element else 1
            img_circle.circle((element['x'], element['y']), element['radius'], fill=fill, outline=outline, width=width)

        # ellipse
        if element["type"] == "ellipse":
            check_for_missing_required_arguments(element, ["x_start", "x_end", "y_start", "y_end"], "ellipse")
            img_ellipse = ImageDraw.Draw(img)
            fill = getIndexColor(element['fill']) if 'fill' in element else None
            outline = getIndexColor(element['outline']) if 'outline' in element else "black"
            width = element['width'] if 'width' in element else 1
            img_ellipse.ellipse([(element['x_start'], element['y_start']), (element['x_end'], element['y_end'])],
                                fill=fill, outline=outline, width=width)

        # text
        if element["type"] == "text":
            check_for_missing_required_arguments(element, ["x", "value"], "text")
            d = ImageDraw.Draw(img)
            d.fontmode = "1"
            size = element.get('size', 20)
            font = element.get('font', "ppb.ttf")
            font_file = os.path.join(os.path.dirname(__file__), font)
            font = ImageFont.truetype(font_file, size)
            if not "y" in element:
                akt_pos_y = pos_y + element.get('y_padding', 10)
            else:
                akt_pos_y = element['y']
            color = element.get('color', "black")
            anchor = element.get('anchor', '')
            align = element.get('align', "left")
            spacing = element.get('spacing', 5)
            stroke_width = element.get('stroke_width', 0)
            stroke_fill = element.get('stroke_fill', 'white')
            if "max_width" in element:
                text = get_wrapped_text(str(element['value']), font, line_length=element['max_width'])
            else:
                text = str(element['value'])
            anchor = anchor or ('la' if '\n' in text else 'lt')
            d.text((element['x'],  akt_pos_y), text, fill=getIndexColor(color), font=font, anchor=anchor, align=align, spacing=spacing, stroke_width=stroke_width, stroke_fill=stroke_fill)
            textbbox = d.textbbox((element['x'],  akt_pos_y), text, font=font, anchor=anchor, align=align, spacing=spacing, stroke_width=stroke_width)
            pos_y = textbbox[3]
        if element["type"] == "multiline":
            check_for_missing_required_arguments(element, ["x", "value", "delimiter"], "multiline")
            d = ImageDraw.Draw(img)
            d.fontmode = "1"
            size = element.get('size', 20)
            font = element.get('font', "ppb.ttf")
            font_file = os.path.join(os.path.dirname(__file__), font)
            font = ImageFont.truetype(font_file, size)
            color = element.get('color', "black")
            anchor = element.get('anchor', "lm")
            stroke_width = element.get('stroke_width', 0)
            stroke_fill = element.get('stroke_fill', 'white')
            _LOGGER.debug("Got Multiline string: %s with delimiter: %s" % (element['value'],element["delimiter"]))
            lst = element['value'].replace("\n","").split(element["delimiter"])
            pos = element.get('start_y', pos_y + element.get('y_padding', 10))
            for elem in lst:
                _LOGGER.debug("String: %s" % (elem))
                d.text((element['x'], pos ), str(elem), fill=getIndexColor(color), font=font, anchor=anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)
                pos = pos + element['offset_y']
            pos_y = pos
        # icon
        if element["type"] == "icon":
            check_for_missing_required_arguments(element, ["x", "y", "value", "size"], "icon")
            d = ImageDraw.Draw(img)
            d.fontmode = "1"
            # ttf from https://github.com/Templarian/MaterialDesign-Webfont/blob/master/fonts/materialdesignicons-webfont.ttf
            font_file = os.path.join(os.path.dirname(__file__), 'materialdesignicons-webfont.ttf')
            meta_file = os.path.join(os.path.dirname(
                __file__), "materialdesignicons-webfont_meta.json")
            f = open(meta_file)
            data = json.load(f)
            chr_hex = ""
            value = element['value']
            if value.startswith("mdi:"):
                value = value[4:]
            for icon in data:
                if icon['name'] == value:
                    chr_hex = icon['codepoint']
                    break
            if chr_hex == "":
                for icon in data:
                    if value in icon['aliases']:
                        chr_hex = icon['codepoint']
                        break
            if chr_hex == "":
                raise HomeAssistantError("Non valid icon used: "+ value)
            stroke_width = element.get('stroke_width', 0)
            stroke_fill = element.get('stroke_fill', 'white')
            font = ImageFont.truetype(font_file, element['size'])
            anchor = element['anchor'] if 'anchor' in element else "la"
            fill = getIndexColor(element['color']) if 'color' in element \
                else getIndexColor(element['fill']) if 'fill' in element else "black"
            d.text((element['x'],  element['y']), chr(int(chr_hex, 16)), fill=fill, font=font,
                   anchor=anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)
        # dlimg
        if element["type"] == "dlimg":
            check_for_missing_required_arguments(element, ["x", "y", "url", "xsize", "ysize"], "dlimg")
            url = element['url']
            pos_x = element['x']
            pos_y = element['y']
            xsize = element['xsize']
            ysize = element['ysize']
            rotate2 = element['rotate'] if 'rotate' in element else 0
            res = [xsize,ysize]
            imgdl = ""
            if "http://" in url or "https://" in url:
                response = requests.get(url)
                imgdl = Image.open(io.BytesIO(response.content))
            elif "data:" in url:
                s = url[5:]
                if not s or ',' not in s:
                    raise HomeAssistantError('invalid data url')
                media_type, _, raw_data = s.partition(',')
                is_base64_encoded = media_type.endswith(';base64')
                if is_base64_encoded:
                    media_type = media_type[:-7]
                    missing_padding = '=' * (-len(raw_data) % 4)
                    if missing_padding:
                        raw_data += missing_padding
                    try:
                        data = base64.b64decode(raw_data)
                    except ValueError as exc:
                        raise HomeAssistantError('invalid base64 in data url') from exc
                else:
                    # Note: unquote_to_bytes() does not raise exceptions for invalid
                    # or partial escapes, so there is no error handling here.
                    data = urllib.parse.unquote_to_bytes(raw_data)
                imgdl = Image.open(io.BytesIO(data))
            else:
                imgdl = Image.open(url)

            if rotate2 != 0:
                imgdl = imgdl.rotate(-rotate2, expand=1)
            width2, height2 = imgdl.size
            if width2 != res[0] or height2 != res[1]:
                imgdl = imgdl.resize((res[0], res[1]))
            imgdl = imgdl.convert("RGBA")
            temp_image = Image.new("RGBA", img.size)
            temp_image.paste(imgdl, (pos_x,pos_y), imgdl)
            img = Image.alpha_composite(img, temp_image)
            img.convert('RGBA')
        # qrcode
        if element["type"] == "qrcode":
            check_for_missing_required_arguments(element, ["x", "y", "data"], "qrcode")
            data = element['data']
            pos_x = element['x']
            pos_y = element['y']
            color = element['color'] if 'color' in element else "black"
            bgcolor = element['bgcolor'] if 'bgcolor' in element else "white"
            border = element['border'] if 'border' in element else 1
            boxsize = element['boxsize'] if 'boxsize' in element else 2
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=boxsize,
                border=border,
            )
            qr.add_data(data)
            qr.make(fit=True)
            imgqr = qr.make_image(fill_color=color, back_color=bgcolor)
            position = (pos_x,pos_y)
            imgqr = imgqr.convert("RGBA")
            img.paste(imgqr, position, imgqr)
            img.convert('RGBA')
        # diagram
        if element["type"] == "diagram":
            img_draw = ImageDraw.Draw(img)
            d = ImageDraw.Draw(img)
            d.fontmode = "1"
            font = element.get('font', "ppb.ttf")
            pos_x = element['x']
            pos_y = element['y']
            width = element.get('width', canvas_width)
            height = element['height']
            offset_lines = element.get('margin', 20)
            # x axis line
            img_draw.line([(pos_x+offset_lines, pos_y+height-offset_lines),(pos_x+width,pos_y+height-offset_lines)],fill = getIndexColor('black'), width = 1)
            # y axis line
            img_draw.line([(pos_x+offset_lines, pos_y),(pos_x+offset_lines,pos_y+height-offset_lines)],fill = getIndexColor('black'), width = 1)
            if "bars" in element:
                bar_margin = element["bars"].get('margin', 10)
                bars = element["bars"]["values"].split(";")
                barcount = len(bars)
                bar_width = math.floor((width - offset_lines - ((barcount + 1) * bar_margin)) / barcount)
                _LOGGER.info("Found %i in bars width: %i" % (barcount,bar_width))
                size = element["bars"].get('legend_size', 10)
                font_file = os.path.join(os.path.dirname(__file__), font)
                font = ImageFont.truetype(font_file, size)
                legend_color = element["bars"].get('legend_color', "black")
                max_val = 0
                for bar in bars:
                    name, value  = bar.split(",",1)
                    if int(value) > max_val:
                        max_val = int(value)
                height_factor = (height - offset_lines) / max_val
                bar_pos = 0
                for bar in bars:
                    name, value  = bar.split(",",1)
                    # legend bottom
                    x_pos = ((bar_margin + bar_width) * bar_pos) + offset_lines
                    d.text((x_pos + (bar_width/2),  pos_y + height - offset_lines /2), str(name), fill=getIndexColor(legend_color), font=font, anchor="mm")
                    img_draw.rectangle([(x_pos, pos_y+height-offset_lines-(height_factor*int(value))),(x_pos+bar_width, pos_y+height-offset_lines)],fill = getIndexColor(element["bars"]["color"]))
                    bar_pos = bar_pos + 1
        # plot
        if element["type"] == "plot":
            check_for_missing_required_arguments(element, ["data"], "plot")
            img_draw = ImageDraw.Draw(img)
            img_draw.fontmode = "1"
            # Obtain drawing region, assume whole canvas if nothing is given
            x_start = element.get("x_start", 0)
            y_start = element.get("y_start", 0)
            x_end = element.get("x_end", canvas_width-1-x_start)
            y_end = element.get("y_end", canvas_height-1-x_start)
            width = x_end - x_start + 1
            height = y_end - y_start + 1
            # The duration of history to look at (default 1 day)
            duration = timedelta(seconds=element.get("duration", 60*60*24))

            end = dt.utcnow()
            start = end - duration
            # The label font and size
            size = element.get("size", 10)
            font_file = element.get("font", "ppb.ttf")
            abs_font_file = os.path.join(os.path.dirname(__file__), font_file)
            font = ImageFont.truetype(abs_font_file, size)
            # The value legend
            ylegend = element.get("ylegend", dict())
            if ylegend is None:
                ylegend_width = 0
            else:
                ylegend_width = ylegend.get("width", -1)
                ylegend_color = ylegend.get("color", "black")
                ylegend_pos = ylegend.get("position", "left")
                if ylegend_pos not in ("left", "right", None):
                    ylegend_pos = "left"
                ylegend_font_file = ylegend.get("font", font_file)
                ylegend_size = ylegend.get("size", size)
                if ylegend_font_file != font_file or ylegend_size != size:
                    ylegend_abs_font_file = os.path.join(os.path.dirname(__file__), ylegend_font_file)
                    ylegend_font = ImageFont.truetype(ylegend_abs_font_file, ylegend_size)
                else:
                    ylegend_font = font
            # The value axis
            yaxis = element.get("yaxis", dict())
            if yaxis is None:
                yaxis_width = 0
                yaxis_tick_width = 0
            else:
                yaxis_width = yaxis.get("width", 1)
                yaxis_color = yaxis.get("color", "black")
                yaxis_tick_width = yaxis.get("tick_width", 2)
                yaxis_tick_every = float(yaxis.get("tick_every", 1))
                yaxis_grid = yaxis.get("grid", 5)
                yaxis_grid_color = yaxis.get("grid_color", "black")
            # The minimum and maximum values that are always shown
            min_v = element.get("low", None)
            max_v = element.get("high", None)
            # Obtain all states of all given entities in the given duration
            all_states = get_significant_states(hass, start_time=start, entity_ids=[plot["entity"] for plot in element["data"]], significant_changes_only=False, minimal_response=True, no_attributes=False)

            # prepare data and obtain min_v and max_v with it
            raw_data = []
            for plot in element["data"]:
                if not(plot["entity"] in all_states):
                    raise HomeAssistantError("no recorded data found for " + plot["entity"])
                states = all_states[plot["entity"]]
                state_obj = states[0]
                states[0] = {"state": state_obj.state, "last_changed": str(state_obj.last_changed)}
                states = [(datetime.fromisoformat(s["last_changed"]), float(s["state"])) for s in states if is_decimal(s["state"])]

                min_v_local, max_v_local = min_max([s[1] for s in states])
                min_v = min(min_v or min_v_local, min_v_local)
                max_v = max(max_v or max_v_local, max_v_local)

                raw_data.append(states)

            max_v = math.ceil(max_v)
            min_v = math.floor(min_v)
            # Prevent division by zero errors
            if max_v == min_v:
                min_v -= 1
            spread = max_v - min_v

            # calculate ylenged_width if it should be automatically determined
            if ylegend_width == -1:
                ylegend_width = math.ceil(max(
                    img_draw.textlength(str(max_v), font=ylegend_font),
                    img_draw.textlength(str(min_v), font=ylegend_font),
                ))

            # effective diagram dimensions
            diag_x = x_start + (ylegend_width if ylegend_pos == "left" else 0)
            diag_y = y_start
            diag_width = width - ylegend_width
            diag_height = height

            if element.get("debug", False):
                img_draw.rectangle([(x_start, y_start), (x_end, y_end)], fill=None, outline=getIndexColor("black"), width=1)
                img_draw.rectangle([(diag_x, diag_y), (diag_x + diag_width - 1, diag_y + diag_height - 1)], fill=None, outline=getIndexColor("red"), width=1)

            # print y grid
            if yaxis is not None:
                if yaxis_grid is not None:
                    grid_points = []
                    curr = min_v
                    while curr <= max_v:
                        curr_y = round(diag_y + (1 - ((curr - min_v) / spread)) * (diag_height - 1))
                        grid_points.extend((x, curr_y) for x in range(diag_x, diag_x + diag_width, yaxis_grid))
                        curr += yaxis_tick_every
                    img_draw.point(grid_points, fill=getIndexColor(yaxis_grid_color))

            # scale data and draw plot
            for plot, data in zip(element["data"], raw_data):
                xy_raw = []
                for time, value in data:
                    rel_time = (time - start) / duration
                    rel_value = (value - min_v) / spread
                    xy_raw.append((round(diag_x + rel_time * (diag_width - 1)), round(diag_y + (1 - rel_value) * (diag_height - 1))))
                # smooth out the data, i.e. if x values appear multiple times, only add them once with the average of all y values
                xy = []
                last_x = None
                ys = []
                for x, y in xy_raw:
                    if x != last_x:
                        if ys:
                            xy.append((last_x, round(sum(ys) / len(ys))))
                            ys = []
                        last_x = x
                    ys.append(y)
                if ys:
                    xy.append((last_x, round(sum(ys) / len(ys))))

                img_draw.line(xy, fill=getIndexColor(plot.get("color", "black")), width=plot.get("width", 1), joint=plot.get("joint", None))

            # print y legend
            if ylegend_pos == "left":
                img_draw.text((x_start, y_start), str(max_v), fill=getIndexColor(ylegend_color), font=ylegend_font, anchor="lt")
                img_draw.text((x_start, y_end), str(min_v), fill=getIndexColor(ylegend_color), font=ylegend_font, anchor="ls")
            elif ylegend_pos == "right":
                img_draw.text((x_end, y_start), str(max_v), fill=getIndexColor(ylegend_color), font=ylegend_font, anchor="rt")
                img_draw.text((x_end, y_end), str(min_v), fill=getIndexColor(ylegend_color), font=ylegend_font, anchor="rs")
            # print y axis
            if yaxis is not None:
                img_draw.rectangle([(diag_x, diag_y), (diag_x + yaxis_width - 1, diag_y + diag_height - 1)], width=0, fill=getIndexColor(yaxis_color))
                if yaxis_tick_width > 0:
                    curr = min_v
                    while curr <= max_v:
                        curr_y = round(diag_y + (1 - ((curr - min_v) / spread)) * (diag_height - 1))
                        img_draw.rectangle([(diag_x + yaxis_width, curr_y), (diag_x + yaxis_width + yaxis_tick_width - 1, curr_y)], width=0, fill=getIndexColor(yaxis_color))
                        curr += yaxis_tick_every

            # print y legend
            if ylegend_pos == "left":
                img_draw.text((x_start, y_start), str(max_v), fill=getIndexColor(ylegend_color), font=ylegend_font, anchor="lt")
                img_draw.text((x_start, y_end), str(min_v), fill=getIndexColor(ylegend_color), font=ylegend_font, anchor="ls")
            elif ylegend_pos == "right":
                img_draw.text((x_end, y_start), str(max_v), fill=getIndexColor(ylegend_color), font=ylegend_font, anchor="rt")
                img_draw.text((x_end, y_end), str(min_v), fill=getIndexColor(ylegend_color), font=ylegend_font, anchor="rs")
            # print y axis
            if yaxis is not None:
                img_draw.rectangle([(diag_x, diag_y), (diag_x + yaxis_width - 1, diag_y + diag_height - 1)], width=0, fill=getIndexColor(yaxis_color))
                if yaxis_tick_width > 0:
                    curr = min_v
                    while curr <= max_v:
                        curr_y = round(diag_y + (1 - ((curr - min_v) / spread)) * (diag_height - 1))
                        img_draw.rectangle([(diag_x + yaxis_width, curr_y), (diag_x + yaxis_width + yaxis_tick_width - 1, curr_y)], width=0, fill=getIndexColor(yaxis_color))
                        curr += yaxis_tick_every

        # Plot custom
        if element["type"] == "plot_custom":
            _LOGGER.info("Started rendering custom plot.")
            img_draw = ImageDraw.Draw(img)
            img_draw.fontmode = "1"

            # Canvas dimensions
            x_start = element.get("x_start", 0)
            y_start = element.get("y_start", 0)
            x_end = element.get("x_end", canvas_width-1-x_start)
            y_end = element.get("y_end", canvas_height-1-x_start)
            width = x_end - x_start + 1
            height = y_end - y_start + 1

            # The label font and size
            size = element.get("size", 10)
            font_file = element.get("font", "ppb.ttf")
            abs_font_file = os.path.join(os.path.dirname(__file__), font_file)
            font = ImageFont.truetype(abs_font_file, size)
            # The value legend
            ylegend = element.get("ylegend", dict())
            if ylegend is None:
                ylegend_width = 0
            else:
                ylegend_width = ylegend.get("width", -1)
                ylegend_color = ylegend.get("color", "black")
                ylegend_pos = ylegend.get("position", "left")
                if ylegend_pos not in ("left", "right", None):
                    ylegend_pos = "left"
                ylegend_font_file = ylegend.get("font", font_file)
                ylegend_size = ylegend.get("size", size)
                if ylegend_font_file != font_file or ylegend_size != size:
                    ylegend_abs_font_file = os.path.join(os.path.dirname(__file__), ylegend_font_file)
                    ylegend_font = ImageFont.truetype(ylegend_abs_font_file, ylegend_size)
                else:
                    ylegend_font = font
            # The value axis
            yaxis = element.get("yaxis", dict())
            if yaxis is None:
                yaxis_width = 0
                yaxis_tick_width = 0
            else:
                yaxis_width = yaxis.get("width", 1)
                yaxis_color = yaxis.get("color", "black")
                yaxis_tick_width = yaxis.get("tick_width", 2)
                yaxis_tick_every = float(yaxis.get("tick_every", 1))
                yaxis_grid = yaxis.get("grid", 5)
                yaxis_grid_color = yaxis.get("grid_color", "black")
            # The minimum and maximum values that are always shown
            min_v = element.get("low", None)
            max_v = element.get("high", None)

            # Direct data from the YAML configuration
            _LOGGER.info("Data type: %s, Content: %s", type(element["data"]), element["data"])
            _LOGGER.info(element["data"])
            x_values = element["data"]["x"]
            y_values = element["data"]["y"]
            raw_data = list(zip(x_values, y_values))

            # Determine bounds
            min_v = min(y_values)
            max_v = max(y_values)
            max_v = math.ceil(max_v)
            min_v = math.floor(min_v)
            if max_v == min_v:
                min_v -= 1
            spread = max_v - min_v

            # calculate ylenged_width if it should be automatically determined
            if ylegend_width == -1:
                ylegend_width = math.ceil(max(
                    img_draw.textlength(str(max_v), font=ylegend_font),
                    img_draw.textlength(str(min_v), font=ylegend_font),
                ))

            # effective diagram dimensions
            diag_x = x_start + (ylegend_width if ylegend_pos == "left" else 0)
            diag_y = y_start
            diag_width = width - ylegend_width
            diag_height = height

            if element.get("debug", False):
                img_draw.rectangle([(x_start, y_start), (x_end, y_end)], fill=None, outline=getIndexColor("black"), width=1)
                img_draw.rectangle([(diag_x, diag_y), (diag_x + diag_width - 1, diag_y + diag_height - 1)], fill=None, outline=getIndexColor("red"), width=1)

            # print y grid
            if yaxis is not None:
                if yaxis_grid is not None:
                    grid_points = []
                    curr = min_v
                    while curr <= max_v:
                        curr_y = round(diag_y + (1 - ((curr - min_v) / spread)) * (diag_height - 1))
                        grid_points.extend((x, curr_y) for x in range(diag_x, diag_x + diag_width, yaxis_grid))
                        curr += yaxis_tick_every
                    img_draw.point(grid_points, fill=getIndexColor(yaxis_grid_color))

            # Scaling data to fit the plot area
            scaled_data = []
            for x, y in raw_data:
                rel_x = (x - min(x_values)) / (max(x_values) - min(x_values))
                rel_y = (y - min_v) / spread
                scaled_x = round(diag_x + rel_x * (diag_width - 1))
                scaled_y = round(diag_y + (1 - rel_y) * (diag_height - 1))
                scaled_data.append((scaled_x, scaled_y))

            _LOGGER.info("Data scaled. Next line shows scaled data.")
            _LOGGER.info(scaled_data)
            # Drawing the line
            img_draw.line(scaled_data, fill=getIndexColor(element["data"].get("color", "black")), width=element["data"].get("width", 1), joint=element["data"].get("joint", None)) # Adjust color and width as needed

            # print y legend
            if ylegend_pos == "left":
                img_draw.text((x_start, y_start), str(max_v), fill=getIndexColor(ylegend_color), font=ylegend_font, anchor="lt")
                img_draw.text((x_start, y_end), str(min_v), fill=getIndexColor(ylegend_color), font=ylegend_font, anchor="ls")
            elif ylegend_pos == "right":
                img_draw.text((x_end, y_start), str(max_v), fill=getIndexColor(ylegend_color), font=ylegend_font, anchor="rt")
                img_draw.text((x_end, y_end), str(min_v), fill=getIndexColor(ylegend_color), font=ylegend_font, anchor="rs")
            # print y axis
            if yaxis is not None:
                img_draw.rectangle([(diag_x, diag_y), (diag_x + yaxis_width - 1, diag_y + diag_height - 1)], width=0, fill=getIndexColor(yaxis_color))
                if yaxis_tick_width > 0:
                    curr = min_v
                    while curr <= max_v:
                        curr_y = round(diag_y + (1 - ((curr - min_v) / spread)) * (diag_height - 1))
                        img_draw.rectangle([(diag_x + yaxis_width, curr_y), (diag_x + yaxis_width + yaxis_tick_width - 1, curr_y)], width=0, fill=getIndexColor(yaxis_color))
                        curr += yaxis_tick_every

        # New: Column Graph
        if element["type"] == "column_graph":
            _LOGGER.debug("Processing a 'column_graph' element.")

            # Validate required fields
            required_keys = ["x_start", "y_start", "width", "height", "data", "labels"]
            missing_keys = [key for key in required_keys if key not in element]
            if missing_keys:
                _LOGGER.error(f"Missing required keys for 'column_graph': {missing_keys}")
                continue  # Skip this element

            # Extract parameters
            x_start = element["x_start"]
            y_start = element["y_start"]
            graph_width = element["width"]
            graph_height = element["height"]
            data = element["data"]
            labels = element["labels"]
            title = element.get("title", "")
            y_label = element.get("y_label", "")
            x_label = element.get("x_label", "")
            column_color = element.get("column_color", "black")
            axis_color_y = element.get("y_axis_color", "black")  # Separate Y-axis color
            axis_color_x = element.get("x_axis_color", "black")  # Separate X-axis color
            grid_color = getIndexColor(element.get("grid_color", "gray"))
            font_path = element.get("font", "/config/www/fonts/ppb.ttf")  # Default font set to "ppb.ttf"
            font_size = element.get("font_size", 10)
            label_precision = element.get("label_precision", 0)  # Default float precision
            x_label_interval = element.get("x_label_interval", None)  # Optional parameter
            y_label_prefix = element.get("y_label_prefix", "€")  # Default prefix

            # Handle Y-axis limits
            ymax_input = element.get("ymax", None)
            ymin_input = element.get("ymin", None)

            # Initialize min and max values from data
            if not isinstance(data, list) or not data:
                _LOGGER.error("'data' should be a non-empty list of numerical values.")
                continue  # Skip this element

            data_numeric = [val for val in data if isinstance(val, (int, float))]
            if len(data_numeric) != len(data):
                _LOGGER.warning("Some 'data' entries are non-numeric and will be ignored.")
                data = data_numeric
                labels = labels[:len(data)]  # Adjust labels accordingly

            if not data:
                _LOGGER.error("No valid numerical data provided for 'column_graph'. Skipping element.")
                continue  # Skip if no valid data

            actual_min = min(data)
            actual_max = max(data)

            # Determine Y-axis limits
            if ymax_input:
                if isinstance(ymax_input, str) and ymax_input.startswith("~"):
                    try:
                        ymax_soft = float(ymax_input[1:])
                        max_value = max(ymax_soft, actual_max)
                        _LOGGER.debug(f"Soft ymax set to {max_value} (input: {ymax_input}, actual_max: {actual_max}).")
                    except ValueError:
                        _LOGGER.error(f"Invalid ymax value: {ymax_input}. Using actual_max={actual_max}.")
                        max_value = actual_max
                else:
                    try:
                        max_value = float(ymax_input)
                        _LOGGER.debug(f"Hard ymax set to {max_value}.")
                    except ValueError:
                        _LOGGER.error(f"Invalid ymax value: {ymax_input}. Using actual_max={actual_max}.")
                        max_value = actual_max
            else:
                max_value = actual_max

            if ymin_input:
                if isinstance(ymin_input, str) and ymin_input.startswith("~"):
                    try:
                        ymin_soft = float(ymin_input[1:])
                        min_value = min(ymin_soft, actual_min)
                        _LOGGER.debug(f"Soft ymin set to {min_value} (input: {ymin_input}, actual_min: {actual_min}).")
                    except ValueError:
                        _LOGGER.error(f"Invalid ymin value: {ymin_input}. Using actual_min={actual_min}.")
                        min_value = actual_min
                else:
                    try:
                        min_value = float(ymin_input)
                        _LOGGER.debug(f"Hard ymin set to {min_value}.")
                    except ValueError:
                        _LOGGER.error(f"Invalid ymin value: {ymin_input}. Using actual_min={actual_min}.")
                        min_value = actual_min
            else:
                min_value = actual_min

            # Prevent division by zero and ensure min < max
            if min_value >= max_value:
                _LOGGER.warning(f"min_value ({min_value}) >= max_value ({max_value}). Adjusting min_value.")
                min_value = max_value - 1

            _LOGGER.debug(f"'column_graph' Y-axis limits: min_value={min_value}, max_value={max_value}.")

            # Load font with error handling
            try:
                font = ImageFont.truetype(font_path, font_size)
                _LOGGER.debug(f"Loaded font from '{font_path}' with size {font_size}.")
            except IOError:
                _LOGGER.error(f"Failed to load font from '{font_path}'. Using default font.")
                font = ImageFont.load_default()

            # Validate labels
            if not isinstance(labels, list):
                _LOGGER.error("'labels' should be a list of strings.")
                continue  # Skip this element
            if len(data) != len(labels):
                _LOGGER.warning(f"The length of 'data' ({len(data)}) does not match the length of 'labels' ({len(labels)}). Trimming to the shorter length.")
                min_length = min(len(data), len(labels))
                data = data[:min_length]
                labels = labels[:min_length]

            # Calculate X-axis label interval if not provided
            if x_label_interval is None:
                x_label_interval = max(1, len(labels) // 5)  # Default to show approximately 5 labels
                _LOGGER.debug(f"Calculated default x_label_interval={x_label_interval} for {len(labels)} labels.")
            else:
                if isinstance(x_label_interval, int) and x_label_interval > 0:
                    _LOGGER.debug(f"Using user-defined x_label_interval={x_label_interval}.")
                else:
                    _LOGGER.warning(f"Invalid x_label_interval={x_label_interval}. Using default value.")
                    x_label_interval = max(1, len(labels) // 5)

            # Draw axes
            draw = ImageDraw.Draw(img)
            # Y-axis
            draw.line(
                [(x_start, y_start), (x_start, y_start + graph_height)],
                fill=axis_color_y,
                width=1
            )
            _LOGGER.debug(f"Drew Y-axis from ({x_start}, {y_start}) to ({x_start}, {y_start + graph_height}) with color {axis_color_y}.")
            # X-axis
            draw.line(
                [(x_start, y_start + graph_height), (x_start + graph_width, y_start + graph_height)],
                fill=axis_color_x,
                width=1
            )
            _LOGGER.debug(f"Drew X-axis from ({x_start}, {y_start + graph_height}) to ({x_start + graph_width}, {y_start + graph_height}) with color {axis_color_x}.")

            # Draw grid lines
            grid_steps = element.get("grid_steps", 5)
            _LOGGER.debug(f"Drawing {grid_steps} grid steps.")
            for i in range(1, grid_steps):
                y = y_start + graph_height - (graph_height / grid_steps) * i
                draw.line(
                    [(x_start, y), (x_start + graph_width, y)],
                    fill=grid_color,
                    width=1
                )
                _LOGGER.debug(f"Drew grid line {i} at y={y} with color {grid_color}.")

                # Y-axis labels using textbbox
                y_val = min_value + (max_value - min_value) / grid_steps * i
                text = f"{y_label_prefix}{y_val:.{label_precision}f}"  # Prepend prefix and set float precision
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                label_x = x_start - text_width - 5
                label_y = y - text_height / 2
                draw.text((int(label_x), int(label_y)), text, fill=axis_color_y, font=font)
                _LOGGER.debug(f"Drew Y-axis label '{text}' at ({label_x}, {label_y}) with fill color {axis_color_y}.")

            # Calculate column width and spacing
            num_columns = len(data)
            spacing = element.get("spacing", 5)
            if num_columns == 0:
                _LOGGER.warning("No data points provided for 'column_graph'. Skipping column drawing.")
                continue  # Skip if no data
            column_width = (graph_width - (num_columns + 1) * spacing) / num_columns
            _LOGGER.debug(f"Calculated column_width={column_width} and spacing={spacing} for {num_columns} columns.")

            # Determine column colors
            if isinstance(column_color, list):
                if len(column_color) != num_columns:
                    _LOGGER.warning(f"Length of 'column_color' list ({len(column_color)}) does not match number of data points ({num_columns}). Using single color for all columns.")
                    column_colors = [getIndexColor(column_color[0])] * num_columns
                else:
                    column_colors = [getIndexColor(col) for col in column_color]
                    _LOGGER.debug(f"Using per-bar colors: {column_colors}")
            else:
                column_colors = [getIndexColor(column_color)] * num_columns
                _LOGGER.debug(f"Using single column color: {column_color}")

            # Draw columns
            for idx, value in enumerate(data):
                if idx >= len(labels):
                    _LOGGER.warning(f"No label provided for column index {idx}. Using index as label.")
                    label = str(idx)
                else:
                    label = labels[idx]

                # Validate numerical value
                if not isinstance(value, (int, float)):
                    _LOGGER.warning(f"Non-numeric value '{value}' at index {idx} in 'data'. Skipping this column.")
                    continue  # Skip non-numeric data

                # Calculate column height
                column_height = (value - min_value) / (max_value - min_value) * graph_height
                if column_height < 0:
                    _LOGGER.warning(f"Negative column height ({column_height}) for value '{value}' at index {idx}. Setting to 0.")
                    column_height = 0

                # Define rectangle coordinates
                x0 = x_start + spacing + idx * (column_width + spacing)
                y0 = y_start + graph_height - column_height
                x1 = x0 + column_width
                y1 = y_start + graph_height

                # Ensure coordinates are integers
                x0_int = int(round(x0))
                y0_int = int(round(y0))
                x1_int = int(round(x1))
                y1_int = int(round(y1))

                # Draw rectangle
                draw.rectangle([x0_int, y0_int, x1_int, y1_int], fill=column_colors[idx])
                _LOGGER.debug(f"Drew column {idx} with height {column_height} mm from ({x0_int}, {y0_int}) to ({x1_int}, {y1_int}) with color {column_colors[idx]}.")

                # Draw labels using textbbox
                bbox = draw.textbbox((0, 0), label, font=font)
                label_width = bbox[2] - bbox[0]
                label_height = bbox[3] - bbox[1]
                label_x = x0 + (column_width - label_width) / 2
                label_y = y_start + graph_height + 2

                # Determine if the label should be drawn based on interval
                if idx % x_label_interval == 0:
                    draw.text((int(round(label_x)), int(round(label_y))), label, fill=axis_color_x, font=font)
                    _LOGGER.debug(f"Drew X-axis label '{label}' at ({label_x}, {label_y}) with fill color {axis_color_x}.")
                else:
                    _LOGGER.debug(f"Skipped drawing X-axis label '{label}' at index {idx} based on x_label_interval={x_label_interval}.")

            # Draw title
            if title:
                bbox = draw.textbbox((0, 0), title, font=font)
                title_width = bbox[2] - bbox[0]
                title_height = bbox[3] - bbox[1]
                title_x = x_start + (graph_width - title_width) / 2
                title_y = y_start - title_height - 5
                draw.text((int(round(title_x)), int(round(title_y))), title, fill=axis_color_y, font=font)
                _LOGGER.debug(f"Drew title '{title}' at ({title_x}, {title_y}) with fill color {axis_color_y}.")

            # Draw Y-axis label (rotated)
            if y_label:
                # Create a separate image for the rotated text
                y_label_image = Image.new('RGBA', (graph_height, 50), (255, 255, 255, 0))  # Width=graph_height to accommodate rotation
                y_draw = ImageDraw.Draw(y_label_image)
                bbox = y_draw.textbbox((0, 0), y_label, font=font)
                y_label_width = bbox[2] - bbox[0]
                y_label_height = bbox[3] - bbox[1]
                y_draw.text((0, (50 - y_label_height) / 2), y_label, fill=axis_color_y, font=font)
                rotated_label = y_label_image.rotate(90, expand=1)
                # Calculate position to paste the rotated label
                label_x = x_start - 45  # Adjust as needed
                label_y = y_start + (graph_height - rotated_label.size[1]) / 2
                img.paste(rotated_label, (int(round(label_x)), int(round(label_y))), rotated_label)
                _LOGGER.debug(f"Drew Y-axis label '{y_label}' rotated at ({label_x}, {label_y}).")

            # Draw X-axis label
            if x_label:
                bbox = draw.textbbox((0, 0), x_label, font=font)
                x_label_width = bbox[2] - bbox[0]
                x_label_height = bbox[3] - bbox[1]
                x_label_x = x_start + graph_width / 2 - x_label_width / 2
                x_label_y = y_start + graph_height + 15
                draw.text((int(round(x_label_x)), int(round(x_label_y))), x_label, fill=axis_color_x, font=font)
                _LOGGER.debug(f"Drew X-axis label '{x_label}' at ({x_label_x}, {x_label_y}) with fill color {axis_color_x}.")



        # progress_bar
        if element["type"] == "progress_bar":
            check_for_missing_required_arguments(element, ["x_start", "x_end", "y_start", "y_end", "progress"], "progress_bar")
            img_draw = ImageDraw.Draw(img)

            x_start = element['x_start']
            y_start = element['y_start']
            x_end = element['x_end']
            y_end = element['y_end']
            progress = element['progress']
            direction = element.get('direction', 'right')
            background = getIndexColor(element.get('background', 'white'))
            fill = getIndexColor(element.get('fill', 'red'))
            outline = getIndexColor(element.get('outline', 'black'))
            width = element.get('width', 1)
            show_percentage = element.get('show_percentage', False)

            # background
            img_draw.rectangle([(x_start, y_start), (x_end, y_end)], fill=background, outline=outline, width=width)

            # Calculate progress dimensions
            if direction in ['right', 'left']:
                progress_width = int((x_end - x_start) * (progress / 100))
                progress_height = y_end - y_start
            else:  # up or down
                progress_width = x_end - x_start
                progress_height = int((y_end - y_start) * (progress / 100))

            # Draw progress
            if direction == 'right':
                img_draw.rectangle([(x_start, y_start), (x_start + progress_width, y_end)], fill=fill)
            elif direction == 'left':
                img_draw.rectangle([(x_end - progress_width, y_start), (x_end, y_end)], fill=fill)
            elif direction == 'up':
                img_draw.rectangle([(x_start, y_end - progress_height), (x_end, y_end)], fill=fill)
            elif direction == 'down':
                img_draw.rectangle([(x_start, y_start), (x_end, y_start + progress_height)], fill=fill)

            img_draw.rectangle([(x_start, y_start), (x_end, y_end)], fill=None, outline=outline, width=width)

            # display percentage text if enabled
            if show_percentage:
                font_size = min(y_end - y_start - 4, x_end - x_start - 4, 20)  # Adjust max font size as needed
                font = ImageFont.truetype(os.path.join(os.path.dirname(__file__), 'ppb.ttf'), font_size)
                percentage_text = f"{progress}%"

                # Calculate text position
                text_bbox = img_draw.textbbox((0, 0), percentage_text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                text_x = (x_start + x_end - text_width) / 2
                text_y = (y_start + y_end - text_height) / 2

                # text color based on progress
                if progress > 50:
                    text_color = background
                else:
                    text_color = fill

                # Draw text
                img_draw.text((text_x, text_y), percentage_text, font=font, fill=text_color, anchor='lt') # TODO anchor is still off



    #post processing
    img = img.rotate(rotate, expand=True)
    rgb_image = img.convert('RGB')
    patha = os.path.join(os.path.dirname(__file__), entity_id + '.jpg')
    pathb = get_image_path(hass, entity_id)
    pathc = get_image_folder(hass)
    isExist = os.path.exists(pathc)
    if not isExist:
        os.makedirs(pathc)
    rgb_image.save(patha, format='JPEG', quality="maximum")
    shutil.copy2(patha,pathb)
    buf = io.BytesIO()
    rgb_image.save(buf, format='JPEG', quality="maximum")
    byte_im = buf.getvalue()
    return byte_im

# adds an image to the queue
def queueimg(url, content):
    queue.append([url,content])
# if the timing is right, processes the queue
def handlequeue():
    global running
    if running:
        return True
    if len(queue) == 0:
        return True
    running = True;
    timebetweencalls = 10;
    file_path = os.path.join(os.path.dirname(__file__), "lastapinteraction" + '.txt')
    filecontent = "0";
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            filecontent = file.read()
    curtime = round(datetime.timestamp(datetime.now()))
    if round(float(filecontent)) + timebetweencalls < curtime:
        with open(file_path, 'w') as file:
            file.write(str(datetime.timestamp(datetime.now())))
        tp = queue.pop(0)
        running = False;
        response = requests.post(tp[0], headers={'Content-Type': tp[1].content_type}, data=tp[1])
        if response.status_code != 200:
            _LOGGER.warning(response.status_code)
            queue.append(tp)
    running = False;
# upload an image to the tag
def uploadimg(img, mac, ip, dither,ttl,preloadtype,preloadlut,hass):
    setup(hass,notsetup)
    url = "http://" + ip + "/imgupload"
    mp_encoder = ""
    if preloadtype == 0:
       mp_encoder = MultipartEncoder(
            fields={
                'mac': mac,
                'contentmode': "25",
                'dither': "1" if dither else "0",
                'ttl': str( ttl),
                'image': ('image.jpg', img, 'image/jpeg'),
            }
        )
    else:
       mp_encoder = MultipartEncoder(
            fields={
                'mac': mac,
                'contentmode': "25",
                'dither': "1" if dither else "0",
                'ttl': str( ttl),
                'preloadtype': str( preloadtype),
                'preloadlut': str( preloadlut),
                'image': ('image.jpg', img, 'image/jpeg'),
            }
        )
    queueimg(url, mp_encoder)
# upload a cmd to the tag
def uploadcfg(cfg, mac, contentmode, ip):
    url = "http://" + ip + "/get_db?mac=" + mac
    response = requests.get(url)
    respjson = json.loads(response.text)
    alias = respjson["tags"][0]["alias"];
    rotate = respjson["tags"][0]["rotate"];
    lut = respjson["tags"][0]["lut"];
    url = "http://" + ip + "/save_cfg"
    mp_encoder = MultipartEncoder(
        fields={
            'mac': mac,
            'contentmode': str(contentmode),
            'modecfgjson': cfg,
            'alias': alias,
            'rotate': str(rotate),
            'lut':str(lut),
        }
    )
    response = requests.post(url, headers={'Content-Type': mp_encoder.content_type}, data=mp_encoder)
    if response.status_code != 200:
        _LOGGER.warning(response.status_code)
#5 line text generator for 1.54 esls (depricated)
def gen5line(entity_id, service, hass):
    entity = hass.states.get(entity_id)
    if not (entity and 'width' in entity.attributes):
        raise HomeAssistantError("id was not found yet, please wait for the display to check in at least once " + entity_id)
    line1 = service.data.get("line1", "")
    line2 = service.data.get("line2", "")
    line3 = service.data.get("line3", "")
    line4 = service.data.get("line4", "")
    line5 = service.data.get("line5", "")
    border = service.data.get("border", "w")
    format1 = service.data.get("format1", "mwwb")
    format2 = service.data.get("format2", "mwwb")
    format3 = service.data.get("format3", "mwwb")
    format4 = service.data.get("format4", "mwwb")
    format5 = service.data.get("format5", "mwwb")
    w = 152
    h = 152
    img = Image.new('RGBA', (w, h), color=white)
    d = ImageDraw.Draw(img)
    # we don't want interpolation
    d.fontmode = "1"
    # border
    d.rectangle([(0, 0), (w - 1, h - 1)], fill=white, outline=getIndexColor(border))
    # text backgrounds
    d.rectangle([(1, 1), (150, 30)], fill=getIndexColor(format1[1]), outline=getIndexColor(format1[2]))
    d.rectangle([(1, 31), (150, 60)], fill=getIndexColor(format2[1]), outline=getIndexColor(format2[2]))
    d.rectangle([(1, 61), (150, 90)], fill=getIndexColor(format3[1]), outline=getIndexColor(format3[2]))
    d.rectangle([(1, 91), (150, 120)], fill=getIndexColor(format4[1]), outline=getIndexColor(format4[2]))
    d.rectangle([(1, 121), (150, 150)], fill=getIndexColor(format5[1]), outline=getIndexColor(format5[2]))
    # text lines
    d = textgen(d, str(line1), getIndexColor(format1[3]), format1[0], 0)
    d = textgen(d, str(line2), getIndexColor(format2[3]), format2[0], 30)
    d = textgen(d, str(line3), getIndexColor(format3[3]), format3[0], 60)
    d = textgen(d, str(line4), getIndexColor(format4[3]), format4[0], 90)
    d = textgen(d, str(line5), getIndexColor(format5[3]), format5[0], 120)
    rgb_image = img.convert('RGB')
    rgb_image.save(os.path.join(os.path.dirname(__file__), entity_id + '.jpg'), format='JPEG', quality="maximum")
    buf = io.BytesIO()
    rgb_image.save(buf, format='JPEG', quality="maximum")
    byte_im = buf.getvalue()
    return byte_im
#4 line text generator for 2.9 esls (depricated)
def gen4line(entity_id, service, hass):
    entity = hass.states.get(entity_id)
    if not (entity and 'width' in entity.attributes):
        raise HomeAssistantError("id was not found yet, please wait for the display to check in at least once " + entity_id)
    line1 = service.data.get("line1", "")
    line2 = service.data.get("line2", "")
    line3 = service.data.get("line3", "")
    line4 = service.data.get("line4", "")
    border = service.data.get("border", "w")
    format1 = service.data.get("format1", "mwwb")
    format2 = service.data.get("format2", "mwwb")
    format3 = service.data.get("format3", "mwwb")
    format4 = service.data.get("format4", "mwwb")
    w = 296
    h = 128
    img = Image.new('RGBA', (w, h), color=white)
    d = ImageDraw.Draw(img)
    # we don't want interpolation
    d.fontmode = "1"
    # border
    d.rectangle([(0, 0), (w - 2, h - 2)], fill=getIndexColor(border))
    # text backgrounds
    d.rectangle([(2, 2), (292, 32)], fill=getIndexColor(format1[1]), outline=getIndexColor(format1[2]))
    d.rectangle([(2, 33), (292, 63)], fill=getIndexColor(format2[1]), outline=getIndexColor(format2[2]))
    d.rectangle([(2, 64), (292, 94)], fill=getIndexColor(format3[1]), outline=getIndexColor(format3[2]))
    d.rectangle([(2, 95), (292, 124)], fill=getIndexColor(format4[1]), outline=getIndexColor(format4[2]))
    # text lines
    d = textgen2(d, str(line1), getIndexColor(format1[3]), format1[0], 2)
    d = textgen2(d, str(line2), getIndexColor(format2[3]), format2[0], 33)
    d = textgen2(d, str(line3), getIndexColor(format3[3]), format3[0], 64)
    d = textgen2(d, str(line4), getIndexColor(format4[3]), format4[0], 95)
    rgb_image = img.convert('RGB')
    rgb_image.save(os.path.join(os.path.dirname(__file__), entity_id + '.jpg'), format='JPEG', quality="maximum")
    buf = io.BytesIO()
    rgb_image.save(buf, format='JPEG', quality="maximum")
    byte_im = buf.getvalue()

    return byte_im
# handles Text alignment(depricated)
def textgen(d, text, col, just, yofs):
    rbm = ImageFont.truetype(os.path.join(os.path.dirname(__file__), 'rbm.ttf'), 11)
    ppb = ImageFont.truetype(os.path.join(os.path.dirname(__file__), 'ppb.ttf'), 23)
    x = 76
    if just == "l":
        x = 3
    if just == "r":
        x = 147
    if "\n" in text:
        split1 = text.split("\n")[0]
        split2 = text.split("\n")[1]
        d.text((x, 8 + yofs), split1, fill=col, anchor=just + "m", font=rbm)
        d.text((x, 22 + yofs), split2, fill=col, anchor=just + "m", font=rbm)
    elif d.textlength(text, font=ppb) < 147:
        d.text((x, 15 + yofs), text, fill=col, anchor=just + "m", font=ppb)
    else:
        d.text((x, 15 + yofs), text, fill=col, anchor=just + "m", font=rbm)
    return d
# handles Text alignment(depricated)
def textgen2(d, text, col, just, yofs):
    rbm = ImageFont.truetype(os.path.join(os.path.dirname(__file__), 'rbm.ttf'), 11)
    ppb = ImageFont.truetype(os.path.join(os.path.dirname(__file__), 'ppb.ttf'), 23)
    x = 148
    if just == "l":
        x = 3
    if just == "r":
        x = 290
    if "\n" in text:
        split1 = text.split("\n")[0]
        split2 = text.split("\n")[1]
        d.text((x, 8 + yofs), split1, fill=col, anchor=just + "m", font=rbm)
        d.text((x, 22 + yofs), split2, fill=col, anchor=just + "m", font=rbm)
    elif d.textlength(text, font=ppb) < 280:
        d.text((x, 15 + yofs), text, fill=col, anchor=just + "m", font=ppb)
    else:
        d.text((x, 15 + yofs), text, fill=col, anchor=just + "m", font=rbm)
    return d


def check_for_missing_required_arguments(element, required_keys, func_name):
    missing_keys = []
    for key in required_keys:
        if key not in element:
            missing_keys.append(key)
    if missing_keys:
        raise HomeAssistantError(f"Missing required argument(s) '{', '.join(missing_keys)}' in '{func_name}'")

def rounded_corners(corner_string):
    if corner_string == "all":
        return True, True, True, True

    corners = corner_string.split(",")
    corner_map = {
        "top_left": 0,
        "top_right": 1,
        "bottom_right": 2,
        "bottom_left": 3
    }
    result = [False] * 4
    for corner in corners:
        corner = corner.strip()
        if corner in corner_map:
            result[corner_map[corner]] = True

    return tuple(result)
