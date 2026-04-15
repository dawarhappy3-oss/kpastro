from flask import Flask, request, jsonify
import swisseph as swe
from datetime import datetime, timedelta
import pytz
import requests
import geonamescache
from timezonefinder import TimezoneFinder

app = Flask(__name__)

# --- INITIALIZE GLOBAL TOOLS ---
gc = geonamescache.GeonamesCache(min_city_population=1000)
tf = TimezoneFinder()

swe.set_ephe_path('')

# --- CONSTANTS ---
PLANETS = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE}
LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
YRS = [7, 20, 6, 10, 7, 18, 16, 19, 17]
ZODIAC = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORDS = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
DEGREE_ASPECTS = {0: ("Conjunction", "Variable"), 30: ("Semi-Sextile", "Positive"), 45: ("Semi-Square", "Negative"), 60: ("Sextile", "Positive"), 90: ("Square", "Negative"), 120: ("Trine", "Positive"), 135: ("Sesquisquare", "Negative"), 180: ("Opposition", "Negative")}

LK_MATRIX = [
    [ 1,  9, 10,  3,  5,  2, 11,  7,  6, 12,  4,  8], [ 4,  1, 12,  9,  3,  7,  5,  6,  2,  8, 10, 11],
    [ 9,  4,  1,  2,  8,  3, 10,  5,  7, 11, 12,  6], [ 3,  8,  4,  1, 10,  9,  6, 11,  5,  7,  2, 12],
    [11,  3,  8,  4,  1,  5,  9,  2, 12,  6,  7, 10], [ 5, 12,  3,  8,  4, 11,  2,  9,  1, 10,  6,  7],
    [ 7,  6,  9,  5, 12,  4,  1, 10, 11,  2,  8,  3], [ 2,  7,  6, 12,  9, 10,  3,  1,  8,  5, 11,  4],
    [12,  2,  7,  6, 11,  1,  8,  4, 10,  3,  5,  9], [10, 11,  2,  7,  6, 12,  4,  8,  3,  1,  9,  5],
    [ 8,  5, 11, 10,  7,  6, 12,  3,  9,  4,  1,  2], [ 6, 10,  5, 11,  2,  8,  7, 12,  4,  9,  3,  1],
    [ 1,  5, 10,  8, 11,  6,  7,  2, 12,  3,  9,  4], [ 4,  1,  3,  2,  5,  7,  8, 11,  6, 12, 10,  9],
    [ 9,  4,  1,  6,  8,  5,  2,  7, 11, 10, 12,  3], [ 3,  9,  4,  1, 12,  8,  6,  5,  2,  7, 11, 10],
    [11,  3,  9,  4,  1, 10,  5,  6,  7,  8,  2, 12], [ 5, 11,  6,  9,  4,  1, 12,  8, 10,  2,  3,  7],
    [ 7, 10, 11,  3,  9,  4,  1, 12,  8,  5,  6,  2], [ 2,  7,  5, 12,  3,  9, 10,  1,  4,  6,  8, 11],
    [12,  2,  8,  5, 10,  3,  9,  4,  1, 11,  7,  6], [10, 12,  2,  7,  6, 11,  3,  9,  5,  1,  4,  8],
    [ 8,  6, 12, 10,  7,  2, 11,  3,  9,  4,  1,  5], [ 6,  8,  7, 11,  2, 12,  4, 10,  3,  9,  5,  1],
    [ 1,  6, 10,  3,  2,  8,  7,  4, 11,  5, 12,  9], [ 4,  1,  3,  8,  6,  7,  2, 11, 12,  9,  5, 10],
    [ 9,  4,  1,  5, 10, 11, 12,  7,  6,  8,  2,  3], [ 3,  9,  4,  1, 11,  5,  6,  8,  7,  2, 10, 12],
    [11,  3,  9,  4,  1,  6,  8,  2, 10, 12,  7,  5], [ 5, 11,  8,  9,  4,  1,  3, 12,  2, 10,  6,  7],
    [ 7,  5, 11, 12,  9,  4,  1, 10,  8,  6,  3,  2], [ 2,  7,  5, 11,  3, 12, 10,  6,  4,  1,  9,  8],
    [12,  2,  6, 10,  8,  3,  9,  1,  5,  7,  4, 11], [10, 12,  2,  7,  5,  9, 11,  3,  1,  4,  8,  6],
    [ 8, 10, 12,  6,  7,  2,  4,  5,  9,  3, 11,  1], [ 6,  8,  7,  2, 12, 10,  5,  9,  3, 11,  1,  4],
    [ 1,  3, 10,  6,  9, 12,  7,  5, 11,  2,  4,  8], [ 4,  1,  3,  8,  6,  5,  2,  7, 12, 10, 11,  9],
    [ 9,  4,  1, 12,  8,  2, 10, 11,  6,  3,  5,  7], [ 3,  9,  4,  1, 11,  8,  6, 12,  2,  5,  7, 10],
    [11,  7,  9,  4,  1,  6,  8,  2, 10, 12,  3,  5], [ 5, 11,  8,  9, 12,  1,  3,  4,  7,  6, 10,  2],
    [ 7,  5, 11,  2,  3,  4,  1, 10,  8,  9, 12,  6], [ 2, 10,  5,  3,  4,  9, 12,  8,  1,  7,  6, 11],
    [12,  2,  6,  5, 10,  7,  9,  1,  3, 11,  8,  4], [10, 12,  2,  7,  5,  3, 11,  6,  4,  8,  9,  1],
    [ 8,  6, 12, 10,  7, 11,  4,  9,  5,  1,  2,  3], [ 6,  8,  7, 11,  2, 10,  5,  3,  9,  4,  1, 12],
    [ 1,  7, 10,  6, 12,  2,  8,  4, 11,  9,  3,  5], [ 4,  1,  8,  3,  6, 12,  5, 11,  2,  7, 10,  9],
    [ 9,  4,  1,  2,  8,  3, 12,  6,  7, 10,  5, 11], [ 3,  9,  4,  1, 11,  7,  2, 12,  5,  8,  6, 10],
    [11, 10,  7,  4,  1,  6,  3,  9, 12,  5,  8,  2], [ 5, 11,  3,  9,  4,  1,  6,  2, 10, 12,  7,  8],
    [ 7,  5, 11,  8,  3,  9,  1, 10,  6,  4,  2, 12], [ 2,  3,  5, 11,  9,  4, 10,  1,  8,  6, 12,  7],
    [12,  2,  6,  5, 10,  8,  9,  7,  4, 11,  1,  3], [10, 12,  2,  7,  5, 11,  4,  8,  3,  1,  9,  6],
    [ 8,  6, 12, 10,  7,  5, 11,  3,  9,  2,  4,  1], [ 6,  8,  9, 12,  2, 10,  7,  5,  1,  3, 11,  4],
    [ 1, 11, 10,  6, 12,  2,  4,  7,  8,  9,  5,  3], [ 4,  1,  6,  8,  3, 12,  2, 10,  9,  5,  7, 11],
    [ 9,  4,  1,  2,  8,  6, 12, 11,  7,  3, 10,  5], [ 3,  9,  4,  1,  6,  8,  7, 12,  5,  2, 11, 10],
    [11,  2,  9,  4,  1,  5,  8,  3, 10, 12,  6,  7], [ 5, 10,  3,  9,  2,  1,  6,  8, 11,  7, 12,  4],
    [ 7,  5, 11,  3, 10,  4,  1,  9, 12,  6,  8,  2], [ 2,  3,  5, 11,  9,  7, 10,  1,  6,  8,  4, 12],
    [12,  8,  7,  5, 11,  3,  9,  4,  1, 10,  2,  6], [10, 12,  2,  7,  5, 11,  3,  6,  4,  1,  9,  8],
    [ 8,  6, 12, 10,  7,  9, 11,  5,  2,  4,  3,  1], [ 6,  7,  8, 12,  4, 10,  5,  2,  3, 11,  1,  9],
    [ 1,  4, 10,  6, 12, 11,  7,  8,  2,  5,  9,  3], [ 4,  2,  3,  8,  6, 12,  1, 11,  7, 10,  5,  9],
    [ 9, 10,  1,  3,  8,  6,  2,  7,  5,  4, 12, 11], [ 3,  9,  6,  1,  2,  8,  5, 12, 11,  7, 10,  4],
    [11,  3,  9,  4,  1,  2,  8, 10, 12,  6,  7,  5], [ 5, 11,  4,  9,  7,  1,  6,  2, 10, 12,  3,  8],
    [ 7,  5, 11,  2,  9,  4, 12,  6,  3,  1,  8, 10], [ 2,  8,  5, 11,  4,  7, 10,  3,  1,  9,  6, 12],
    [12,  1,  7,  5, 11, 10,  9,  4,  8,  3,  2,  6], [10, 12,  2,  7,  5,  3,  4,  9,  6,  8, 11,  1],
    [ 8,  6, 12, 10,  3,  5, 11,  1,  9,  2,  4,  7], [ 6,  7,  8, 12, 10,  9,  3,  5,  4, 11,  1,  2],
    [ 1,  3, 10,  6, 12,  2,  8, 11,  5,  4,  9,  7], [ 4,  1,  8,  3,  6, 12, 11,  2,  7,  9, 10,  5],
    [ 9,  4,  1,  7,  3,  8, 12,  5,  2,  6, 11, 10], [ 3,  9,  4,  1,  8, 10,  2,  7, 12,  5,  6, 11],
    [11, 10,  9,  4,  1,  6,  7, 12,  3,  8,  5,  2], [ 5, 11,  6,  9,  4,  1,  3,  8, 10,  2,  7, 12],
    [ 7,  5, 11,  2, 10,  4,  6,  9,  8,  3, 12,  1], [ 2,  7,  5, 11,  9,  3, 10,  4,  1, 12,  8,  6],
    [12,  8,  7,  5,  2, 11,  9,  1,  6, 10,  3,  4], [10, 12,  2,  8, 11,  5,  4,  6,  9,  7,  1,  3],
    [ 8,  6, 12, 10,  5,  7,  1,  3,  4, 11,  2,  9], [ 6,  2,  3, 12,  7,  9,  5, 10, 11,  1,  4,  8],
    [ 1,  9, 10,  6, 12,  2,  7,  5,  3,  4,  8, 11], [ 4,  1,  6,  8, 10, 12, 11,  2,  9,  7,  3,  5],
    [ 9,  4,  1,  2,  6,  8, 12, 11,  5,  3, 10,  7], [ 3, 10,  8,  1,  5,  7,  6, 12,  2,  9, 11,  4],
    [11,  3,  9,  4,  1,  6,  8, 10,  7,  5, 12,  2], [ 5, 11,  3,  9,  4,  1,  2,  6,  8, 12,  7, 10],
    [ 7,  5, 11,  3,  9,  4,  1,  8, 12, 10,  2,  6], [ 2,  7,  5, 11,  3,  9, 10,  1,  6,  8,  4, 12],
    [12,  2,  4,  5, 11,  3,  9,  7, 10,  6,  1,  8], [10, 12,  2,  7,  8,  5,  3,  9,  4, 11,  6,  1],
    [ 8,  6, 12, 10,  7, 11,  4,  3,  1,  2,  5,  9], [ 6,  8,  7, 12,  2, 10,  5,  4, 11,  1,  9,  3],
    [ 1,  9, 10,  6, 12,  2,  7, 11,  5,  3,  4,  8], [ 4,  1,  6,  8, 10, 12,  3,  5,  7,  2, 11,  9],
    [ 9,  4,  1,  2,  5,  8, 12, 10,  6,  7,  3, 11], [ 3, 10,  8,  9, 11,  7,  4,  1,  2, 12,  6,  5],
    [11,  3,  9,  4,  1,  6,  2,  7, 10,  5,  8, 12], [ 5, 11,  3,  1,  4, 10,  6,  8, 12,  9,  7,  2],
    [ 7,  5, 11,  3,  9,  4,  1, 12,  8, 10,  2,  6], [ 2,  7,  5, 11,  3,  9, 10,  6,  4,  8, 12,  1],
    [12,  2,  4,  5,  6,  1,  8,  9,  3, 11, 10,  7], [10, 12,  2,  7,  8, 11,  9,  3,  1,  6,  5,  4],
    [ 8,  6, 12, 10,  7,  5, 11,  2,  9,  4,  1,  3], [ 6,  8,  7, 12,  2,  3,  5,  4, 11,  1,  9, 10]
]

# --- MATH HELPERS ---
def format_dms(d):
    d_val = d % 30
    deg = int(d_val)
    m = int((d_val-deg)*60)
    s = int((d_val-deg-m/60)*3600)
    return f"{deg:02d}° {m:02d}' {s:02d}\""

def get_kp_lords(lon):
    sp = 360/27; n = int(lon/sp); st = LORDS[n%9]
    rem = lon - (n*sp); ps = 0.0; sb = ""; ssb = ""; sidx = 0; s_sp = 0
    for i in range(9):
        idx = (n%9 + i)%9
        s_sp = (YRS[idx]/120)*sp; ps += s_sp
        if rem <= ps: 
            sb = LORDS[idx]; sidx = idx; break
    rem_s = rem - (ps - s_sp); ps_s = 0.0
    for i in range(9):
        idx = (sidx + i)%9
        ss_sp = (YRS[idx]/120)*s_sp; ps_s += ss_sp
        if rem_s <= ps_s: 
            ssb = LORDS[idx]; break
    return st, sb, ssb

def get_horary_ascendant(number):
    num = int(number)
    curr_deg, curr_idx = 0.0, 1
    for star in range(27):
        star_lord = star % 9
        for sub in range(9):
            sub_lord = (star_lord + sub) % 9
            span = (YRS[sub_lord] / 120.0) * (360.0 / 27.0)
            next_deg = curr_deg + span
            if int(next_deg/30) > int(curr_deg/30) and abs(next_deg%30) > 1e-6:
                if curr_idx == num: return curr_deg
                curr_idx += 1
                if curr_idx == num: return int(next_deg/30)*30.0
                curr_idx += 1
            else:
                if curr_idx == num: return curr_deg
                curr_idx += 1
            curr_deg = next_deg
    return 0.0

def get_kp_color(p_name):
    c = {"Sun": "#b03a2e", "Moon": "#21618c", "Mars": "#cb4335", "Mercury": "#1e8449", "Jupiter": "#d35400", "Venus": "#c71585", "Saturn": "#2874a6", "Rahu": "#873600", "Ketu": "#873600", "Asc": "#d35400"}
    for k in c:
        if k in p_name: return c[k]
    return "#000000"

def draw_svg_square(house_data, cusp_signs, title):
    svg = '<svg viewBox="0 0 400 400" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">\n'
    svg += '<rect x="0" y="0" width="400" height="400" fill="#fdf0d5"/>\n' 
    gc, gw = "#8c7b65", "1.5"
    svg += f'<line x1="2" y1="2" x2="398" y2="398" stroke="{gc}" stroke-width="{gw}"/>\n<line x1="398" y1="2" x2="2" y2="398" stroke="{gc}" stroke-width="{gw}"/>\n'
    svg += f'<polygon points="200,2 2,200 200,398 398,200" fill="none" stroke="{gc}" stroke-width="{gw}"/>\n<rect x="2" y="2" width="396" height="396" fill="none" stroke="{gc}" stroke-width="2.5"/>\n'
    
    pos_planets = {1: (200, 100), 2: (100, 50), 3: (50, 100), 4: (100, 200), 5: (50, 300), 6: (100, 350), 7: (200, 300), 8: (300, 350), 9: (350, 300), 10: (300, 200), 11: (350, 100), 12: (300, 50)}
    pos_signs = {1: (200, 165), 2: (100, 75), 3: (75, 100), 4: (165, 200), 5: (75, 300), 6: (100, 325), 7: (200, 235), 8: (300, 325), 9: (325, 300), 10: (235, 200), 11: (325, 100), 12: (300, 75)}
    
    for i in range(1, 13):
        sx, sy = pos_signs[i]
        svg += f'<text x="{sx}" y="{sy+4}" text-anchor="middle" font-size="12" font-family="Arial" font-weight="bold" fill="#1e8449">{cusp_signs[i-1]}</text>\n'
        px, py = pos_planets[i]
        planets = house_data.get(i, [])
        if planets:
            cy = py - ((len(planets) - 1) * 7.5) 
            for p in planets:
                svg += f'<text x="{px}" y="{cy}" text-anchor="middle" font-size="12" font-family="Arial" font-weight="bold" fill="{get_kp_color(p)}">{p}</text>\n'
                cy += 15
    svg += '</svg>'
    return svg

def draw_svg_lk(house_data):
    svg = '<svg viewBox="0 0 400 400" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">\n<rect x="0" y="0" width="400" height="400" fill="#ffffff"/>\n' 
    gc, gw, cx, cy, R = "#8b0000", "1.5", 200, 200, 190
    x1, y1, x2, y2 = cx - R, cy - R, cx + R, cy + R
    svg += f'<rect x="{x1}" y="{y1}" width="{R*2}" height="{R*2}" fill="none" stroke="{gc}" stroke-width="{gw}"/>\n'
    svg += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{gc}" stroke-width="{gw}"/>\n<line x1="{x2}" y1="{y1}" x2="{x1}" y2="{y2}" stroke="{gc}" stroke-width="{gw}"/>\n'
    svg += f'<polygon points="{cx},{y1} {x2},{cy} {cx},{y2} {x1},{cy}" fill="none" stroke="{gc}" stroke-width="{gw}"/>\n'
    
    pos = {1: (cx, cy - R/2), 2: (cx - R/2, cy - 3*R/4), 3: (cx - 3*R/4, cy - R/2), 4: (cx - R/2, cy), 5: (cx - 3*R/4, cy + R/2), 6: (cx - R/2, cy + 3*R/4), 7: (cx, cy + R/2), 8: (cx + R/2, cy + 3*R/4), 9: (cx + 3*R/4, cy + R/2), 10: (cx + R/2, cy), 11: (cx + 3*R/4, cy - R/2), 12: (cx + R/2, cy - 3*R/4)}
    offsets = {1: (0, -25), 2: (0, -15), 3: (-15, 0), 4: (-25, 0), 5: (-15, 0), 6: (0, 15), 7: (0, 25), 8: (0, 15), 9: (15, 0), 10: (25, 0), 11: (15, 0), 12: (0, -15)}

    for i in range(1, 13):
        px, py = pos[i]; ox, oy = offsets[i]
        svg += f'<text x="{px + ox}" y="{py + oy + 4}" text-anchor="middle" font-size="11" font-family="Arial" fill="#c0392b">{i}</text>\n'
        planets = house_data.get(i, [])
        if planets:
            cY = py - ((len(planets) - 1) * 7.5)
            for p in planets:
                svg += f'<text x="{px}" y="{cY}" text-anchor="middle" font-size="11" font-family="Arial" fill="{get_kp_color(p)}">{p}</text>\n'
                cY += 15
    svg += '</svg>'
    return svg

# --- HTML/JS SPA FRONTEND ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KP Astro Pro Web</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .hidden { display: none !important; }
        .tab-btn.active { border-color: #3b82f6; color: #2563eb; font-weight: bold; }
        th, td { border: 1px solid #e5e7eb; padding: 0.5rem; text-align: center; }
        th { background-color: #1e3a8a; color: white; }
    </style>
</head>
<body class="bg-gray-100 text-gray-800 font-sans">

    <div id="input-screen" class="min-h-screen flex items-center justify-center p-4">
        <div class="bg-white rounded-xl shadow-xl p-8 max-w-3xl w-full">
            <h1 class="text-3xl font-extrabold text-center text-blue-900 mb-8">KP Astrology Pro Setup</h1>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div><label class="block text-sm font-bold text-gray-700">Name</label><input type="text" id="i-name" value="Happy" class="mt-1 w-full border rounded p-2"></div>
                <div><label class="block text-sm font-bold text-gray-700">DOB (DD-MM-YYYY)</label><input type="text" id="i-dob" value="01-09-1975" class="mt-1 w-full border rounded p-2"></div>
                <div><label class="block text-sm font-bold text-gray-700">Time (HH:MM:SS)</label><input type="text" id="i-time" value="05:16:00" class="mt-1 w-full border rounded p-2"></div>
                
                <div>
                    <label class="block text-sm font-bold text-gray-700">City</label>
                    <div class="relative">
                        <input type="text" id="i-city" value="Ludhiana" onblur="fetchLocation()" class="mt-1 w-full border rounded p-2">
                        <span id="city-status" class="absolute right-2 top-3 text-xs font-bold text-blue-600"></span>
                    </div>
                </div>

                <div><label class="block text-sm font-bold text-gray-700">Latitude</label><input type="text" id="i-lat" value="30.9010" class="mt-1 w-full border rounded p-2"></div>
                <div><label class="block text-sm font-bold text-gray-700">Longitude</label><input type="text" id="i-lon" value="75.8573" class="mt-1 w-full border rounded p-2"></div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div>
                    <label class="block text-sm font-bold text-gray-700">Timezone</label>
                    <input type="text" id="i-tz" value="Asia/Kolkata" class="mt-1 w-full border rounded p-2">
                </div>
                <div><label class="block text-sm font-bold text-gray-700">Horary (1-249)</label><input type="number" id="i-horary" value="1" class="mt-1 w-full border rounded p-2"></div>
                <div>
                    <label class="block text-sm font-bold text-gray-700">Ayanamsa</label>
                    <select id="i-aya" class="mt-1 w-full border rounded p-2">
                        <option value="K.P.">K.P.</option>
                        <option value="Chitrapaksha">Lahiri</option>
                        <option value="Raman">Raman</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-bold text-gray-700">Rahu</label>
                    <select id="i-rahu" class="mt-1 w-full border rounded p-2">
                        <option value="Mean">Mean Node</option>
                        <option value="True">True Node</option>
                    </select>
                </div>
            </div>

            <button onclick="openDashboard()" class="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-4 rounded text-lg shadow">
                OPEN DASHBOARD
            </button>
        </div>
    </div>

    <div id="dashboard-screen" class="hidden p-4 max-w-7xl mx-auto">
        <div class="flex flex-col md:flex-row justify-between items-center mb-6 bg-blue-900 text-white p-4 rounded shadow gap-4">
            <div>
                <h2 class="text-2xl font-bold" id="d-name">Client Name</h2>
                <p class="text-sm text-gray-300" id="d-details">DOB | Time | Place</p>
            </div>
            <div class="flex items-center gap-4">
                <div class="flex flex-col">
                    <label class="text-xs font-bold text-gray-300">Chart Mode</label>
                    <select id="d-mode" class="text-black p-1 rounded font-bold" onchange="fetchData()">
                        <option value="Natal">Natal</option>
                        <option value="Horary">Horary</option>
                    </select>
                </div>
                <div class="flex flex-col">
                    <label class="text-xs font-bold text-gray-300">Lal Kitab Age</label>
                    <input type="number" id="d-age" value="51" class="text-black w-16 p-1 rounded font-bold" onchange="fetchData()">
                </div>
                <button onclick="backToInput()" class="bg-red-500 hover:bg-red-600 px-4 py-2 rounded font-bold mt-4">Close</button>
            </div>
        </div>

        <div id="loader" class="hidden text-center text-blue-600 font-bold text-xl my-8">Calculating Ephemeris Data... Please wait.</div>

        <div id="content-wrap" class="hidden">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <div class="bg-white rounded shadow p-4"><h3 class="font-bold text-center text-blue-900 mb-2">Lagna Chart</h3><div id="svg-lagna"></div></div>
                <div class="bg-white rounded shadow p-4"><h3 class="font-bold text-center text-green-900 mb-2">Bhava Chalit</h3><div id="svg-chalit"></div></div>
                <div class="bg-white rounded shadow p-4"><h3 class="font-bold text-center text-red-900 mb-2">Lal Kitab Varshphal</h3><div id="svg-lk"></div></div>
            </div>

            <div class="border-b mb-6 flex space-x-4 overflow-x-auto">
                <button onclick="switchTab('tab-pos', this)" class="tab-btn active px-4 py-2 border-b-2 border-blue-500 text-blue-600 font-bold whitespace-nowrap">Positions</button>
                <button onclick="switchTab('tab-nadi', this)" class="tab-btn px-4 py-2 border-b-2 border-transparent font-bold whitespace-nowrap">Nadi</button>
                <button onclick="switchTab('tab-hits', this)" class="tab-btn px-4 py-2 border-b-2 border-transparent font-bold whitespace-nowrap">Degree Hits</button>
            </div>

            <div id="tab-pos" class="tab-pane grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="bg-white shadow rounded p-4 overflow-auto">
                    <h3 class="font-bold text-blue-900 mb-2">Planetary Positions</h3>
                    <table class="w-full text-xs">
                        <thead><tr><th>Planet</th><th>Sign</th><th>Degree</th><th>Star L</th><th>Sub L</th><th>S-Sub</th></tr></thead>
                        <tbody id="tb-planets"></tbody>
                    </table>
                </div>
                <div class="bg-white shadow rounded p-4 overflow-auto">
                    <h3 class="font-bold text-green-900 mb-2">Cusp Positions</h3>
                    <table class="w-full text-xs">
                        <thead><tr><th>House</th><th>Sign</th><th>Degree</th><th>Star L</th><th>Sub L</th><th>S-Sub</th></tr></thead>
                        <tbody id="tb-cusps"></tbody>
                    </table>
                </div>
            </div>

            <div id="tab-nadi" class="tab-pane hidden bg-white shadow rounded p-4 overflow-auto">
                <table class="w-full text-sm">
                    <thead><tr><th>PLANET</th><th>P-SIGNIFS</th><th>STAR LORD</th><th>ST-SIGNIFS</th><th>SUB LORD</th><th>SB-SIGNIFS</th></tr></thead>
                    <tbody id="tb-nadi"></tbody>
                </table>
            </div>

            <div id="tab-hits" class="tab-pane hidden grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="bg-white shadow rounded p-4 overflow-auto">
                    <h3 class="font-bold mb-2">Planet to Planet</h3>
                    <table class="w-full text-xs">
                        <thead><tr><th>P1</th><th>P2</th><th>Aspect</th><th>Diff</th><th>Nature</th></tr></thead>
                        <tbody id="tb-p2p"></tbody>
                    </table>
                </div>
                <div class="bg-white shadow rounded p-4 overflow-auto">
                    <h3 class="font-bold mb-2">Planet to House</h3>
                    <table class="w-full text-xs">
                        <thead><tr><th>Planet</th><th>House</th><th>Aspect</th><th>Diff</th><th>Nature</th></tr></thead>
                        <tbody id="tb-p2h"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function fetchLocation() {
            const city = document.getElementById('i-city').value;
            if(!city) return;
            
            const statusLabel = document.getElementById('city-status');
            statusLabel.innerText = "Searching...";
            statusLabel.classList.remove('text-red-600', 'text-green-600');
            statusLabel.classList.add('text-blue-600');

            try {
                const res = await fetch('/api/location', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({city: city})
                });
                const data = await res.json();
                
                if(data.status === 'success') {
                    document.getElementById('i-lat').value = data.lat;
                    document.getElementById('i-lon').value = data.lon;
                    document.getElementById('i-tz').value = data.tz;
                    statusLabel.innerText = "Found!";
                    statusLabel.classList.replace('text-blue-600', 'text-green-600');
                } else {
                    statusLabel.innerText = "Not found. Enter manually.";
                    statusLabel.classList.replace('text-blue-600', 'text-red-600');
                }
            } catch(e) {
                statusLabel.innerText = "API Error.";
            }
        }

        function openDashboard() {
            document.getElementById('input-screen').classList.add('hidden');
            document.getElementById('dashboard-screen').classList.remove('hidden');
            
            document.getElementById('d-name').innerText = document.getElementById('i-name').value;
            document.getElementById('d-details').innerText = `${document.getElementById('i-dob').value} | ${document.getElementById('i-time').value} | TZ: ${document.getElementById('i-tz').value}`;
            
            fetchData();
        }

        function backToInput() {
            document.getElementById('dashboard-screen').classList.add('hidden');
            document.getElementById('input-screen').classList.remove('hidden');
            document.getElementById('content-wrap').classList.add('hidden');
        }

        function switchTab(id, el) {
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.add('hidden'));
            document.querySelectorAll('.tab-btn').forEach(b => {
                b.classList.remove('active', 'border-blue-500', 'text-blue-600');
                b.classList.add('border-transparent');
            });
            document.getElementById(id).classList.remove('hidden');
            el.classList.add('active', 'border-blue-500', 'text-blue-600');
            el.classList.remove('border-transparent');
        }

        async function fetchData() {
            document.getElementById('content-wrap').classList.add('hidden');
            document.getElementById('loader').classList.remove('hidden');

            const payload = {
                date: document.getElementById('i-dob').value,
                time: document.getElementById('i-time').value,
                lat: document.getElementById('i-lat').value,
                lon: document.getElementById('i-lon').value,
                tz: document.getElementById('i-tz').value,
                horary: document.getElementById('i-horary').value,
                aya: document.getElementById('i-aya').value,
                rahu: document.getElementById('i-rahu').value,
                age: document.getElementById('d-age').value,
                mode: document.getElementById('d-mode').value
            };

            try {
                const res = await fetch('/api/calculate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                const d = await res.json();
                
                if (d.status !== 'success') { alert(d.message); return; }

                // Inject SVGs
                document.getElementById('svg-lagna').innerHTML = d.svg_lagna;
                document.getElementById('svg-chalit').innerHTML = d.svg_chalit;
                document.getElementById('svg-lk').innerHTML = d.svg_lk;

                // Build Tables
                const buildTr = (arr, colorCol=null) => arr.map((r,i) => `<tr class="${i%2==0?'bg-white':'bg-gray-50'}">${r.map((c, j) => `<td class="${j===colorCol?'font-bold text-blue-700':''}">${c}</td>`).join('')}</tr>`).join('');
                
                document.getElementById('tb-planets').innerHTML = buildTr(d.planets, 1);
                document.getElementById('tb-cusps').innerHTML = buildTr(d.cusps, 1);
                document.getElementById('tb-nadi').innerHTML = buildTr(d.nadi);
                
                document.getElementById('tb-p2p').innerHTML = d.hits_p2p.map((r,i) => `<tr class="${i%2==0?'bg-white':'bg-gray-50'} ${r[4]==='Positive'?'text-green-700':r[4]==='Negative'?'text-red-700':''} font-bold"><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td><td>${r[4]}</td></tr>`).join('');
                document.getElementById('tb-p2h').innerHTML = d.hits_p2h.map((r,i) => `<tr class="${i%2==0?'bg-white':'bg-gray-50'} ${r[4]==='Positive'?'text-green-700':r[4]==='Negative'?'text-red-700':''} font-bold"><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td><td>${r[4]}</td></tr>`).join('');

                document.getElementById('loader').classList.add('hidden');
                document.getElementById('content-wrap').classList.remove('hidden');

            } catch (err) {
                alert("Network Error: " + err);
                document.getElementById('loader').classList.add('hidden');
            }
        }
    </script>
</body>
</html>
"""

# --- FLASK ROUTES ---

@app.route('/', methods=['GET'])
def home():
    return HTML_PAGE

@app.route('/api/location', methods=['POST'])
def fetch_location_api():
    city_name = request.json.get('city', '').strip().title()
    if not city_name: return jsonify({"status": "error"})

    # 1. Try Offline Dictionary (Fastest)
    matches = gc.get_cities_by_name(city_name)
    if matches:
        city_data_list = []
        for match in matches: city_data_list.extend(match.values())
        if city_data_list:
            best_match = sorted(city_data_list, key=lambda x: x.get('population', 0), reverse=True)[0]
            lat, lon = best_match['latitude'], best_match['longitude']
            tz = best_match.get('timezone') or tf.timezone_at(lng=lon, lat=lat) or 'UTC'
            return jsonify({"status": "success", "lat": f"{lat:.4f}", "lon": f"{lon:.4f}", "tz": tz})

    # 2. Try Online Fetch (Nominatim fallback)
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'KPAstroAppWeb/1.0'}
        resp = requests.get(url, headers=headers, timeout=5).json()
        if resp:
            lat, lon = float(resp[0]['lat']), float(resp[0]['lon'])
            tz = tf.timezone_at(lng=lon, lat=lat) or 'UTC'
            return jsonify({"status": "success", "lat": f"{lat:.4f}", "lon": f"{lon:.4f}", "tz": tz})
    except: pass

    return jsonify({"status": "error", "message": "Not found"})

@app.route('/api/calculate', methods=['POST'])
def calculate_api():
    data = request.json
    try:
        # 1. Parse Data & TZ Localization
        dt = datetime.strptime(f"{data['date']} {data['time']}", "%d-%m-%Y %H:%M:%S")
        tz = pytz.timezone(data['tz'])
        utc_dt = tz.localize(dt).astimezone(pytz.utc)
        
        # CRITICAL FIX: The seconds calculation was missing in the previous version!
        jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0 + utc_dt.second/3600.0)
        
        # 2. Ayanamsa
        aya = data.get('aya', 'K.P.')
        if aya == "Chitrapaksha": swe.set_sid_mode(swe.SIDM_LAHIRI)
        elif aya == "Raman": swe.set_sid_mode(swe.SIDM_RAMAN)
        else: swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
        
        flags = swe.FLG_SIDEREAL | swe.FLG_SPEED
        
        # 3. Cusps & Horary Adjustment
        cusps_raw, _ = swe.houses_ex(jd, float(data['lat']), float(data['lon']), b'P', flags=flags)
        
        mode = data.get('mode', 'Natal')
        try:
            if mode == "Horary":
                h_num = int(data.get('horary', 1))
                if 1 <= h_num <= 249:
                    h_asc = get_horary_ascendant(h_num)
                    diff = h_asc - cusps_raw[0]
                    cusps_raw = [(c + diff) % 360 for c in cusps_raw]
        except: pass

        asc_sign = int(cusps_raw[0] / 30) + 1
        lagna_signs = [((asc_sign + i - 1) % 12) + 1 for i in range(12)]
        chalit_signs = [int(c / 30) + 1 for c in cusps_raw]

        cusp_res = []
        for i in range(12):
            c_lon = cusps_raw[i]
            st, sb, ssb = get_kp_lords(c_lon)
            cusp_res.append([i+1, ZODIAC[int(c_lon/30)], format_dms(c_lon), st, sb, ssb])

        # 4. Planets & Rahu setting
        if data.get('rahu') == "True": PLANETS["Rahu"] = swe.TRUE_NODE
        else: PLANETS["Rahu"] = swe.MEAN_NODE

        planet_res, p_data = [], {}
        rahu_lon = 0
        h_lagna, h_chalit = {i: [] for i in range(1, 13)}, {i: [] for i in range(1, 13)}

        for name, p_id in PLANETS.items():
            calc, _ = swe.calc_ut(jd, p_id, flags)
            lon = calc[0]
            if name == "Rahu": rahu_lon = lon
            is_retro = calc[3] < 0 if name not in ["Sun", "Moon"] else False
            disp = f"{name}(R)" if is_retro else name
            st, sb, ssb = get_kp_lords(lon)
            
            planet_res.append([disp, ZODIAC[int(lon/30)], format_dms(lon), st, sb, ssb])
            p_data[name] = {"lon": lon, "st": st, "sb": sb}
            
            l_house = (int(lon/30) + 1 - asc_sign + 12) % 12 + 1
            h_lagna[l_house].append(name[:2])
            for h_idx in range(12):
                h_s, h_e = cusps_raw[h_idx], cusps_raw[(h_idx + 1) % 12]
                if (h_s < h_e and h_s <= lon < h_e) or (h_s > h_e and (lon >= h_s or lon < h_e)):
                    h_chalit[h_idx+1].append(name[:2]); break

        # Manual Ketu
        k_lon = (rahu_lon + 180.0) % 360.0
        st, sb, ssb = get_kp_lords(k_lon)
        planet_res.append(["Ketu(R)", ZODIAC[int(k_lon/30)], format_dms(k_lon), st, sb, ssb])
        p_data["Ketu"] = {"lon": k_lon, "st": st, "sb": sb}
        
        h_lagna[(int(k_lon/30) + 1 - asc_sign + 12) % 12 + 1].append("Ke")
        for h_idx in range(12):
            h_s, h_e = cusps_raw[h_idx], cusps_raw[(h_idx + 1) % 12]
            if (h_s < h_e and h_s <= k_lon < h_e) or (h_s > h_e and (k_lon >= h_s or k_lon < h_e)):
                h_chalit[h_idx+1].append("Ke"); break

        # 5. Nadi Significators
        nadi_res = []
        nadi_order = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        base_sigs = {}
        for p in nadi_order:
            lon = p_data[p]['lon']
            occ = 1
            for i in range(12):
                h_s, h_e = cusps_raw[i], cusps_raw[(i + 1) % 12]
                if (h_s < h_e and h_s <= lon < h_e) or (h_s > h_e and (lon >= h_s or lon < h_e)): occ = i+1; break
            owns = [i+1 for i in range(12) if SIGN_LORDS[chalit_signs[i]-1] == p] if p not in ["Rahu", "Ketu"] else []
            base_sigs[p] = {'occ': occ, 'owns': owns}

        for p in nadi_order:
            sig = sorted(list(set([base_sigs[p]['occ']] + base_sigs[p]['owns'])))
            st = p_data[p]['st']
            st_sig = sorted(list(set([base_sigs[st]['occ']] + base_sigs[st]['owns'])))
            sb = p_data[p]['sb']
            sb_sig = sorted(list(set([base_sigs[sb]['occ']] + base_sigs[sb]['owns'])))
            nadi_res.append([p, ", ".join(map(str, sig)) or "-", st, ", ".join(map(str, st_sig)) or "-", sb, ", ".join(map(str, sb_sig)) or "-"])

        # 6. Degree Hits
        hits_p2p, hits_p2h = [], []
        p_keys = list(p_data.keys())
        for i in range(len(p_keys)):
            for j in range(i+1, len(p_keys)):
                p1, p2 = p_keys[i], p_keys[j]
                diff = abs(p_data[p1]['lon'] - p_data[p2]['lon'])
                diff = 360 - diff if diff > 180 else diff
                for asp_deg, (asp_name, nature) in DEGREE_ASPECTS.items():
                    if abs(diff - asp_deg) <= 3.0: hits_p2p.append([p1, p2, asp_name, f"{diff:.2f}°", nature])

        for p_name, p_info in p_data.items():
            for h_idx in range(12):
                diff = abs(p_info['lon'] - cusps_raw[h_idx])
                diff = 360 - diff if diff > 180 else diff
                for asp_deg, (asp_name, nature) in DEGREE_ASPECTS.items():
                    if abs(diff - asp_deg) <= 3.0: hits_p2h.append([p_name, f"House {h_idx+1}", asp_name, f"{diff:.2f}°", nature])

        # 7. Lal Kitab
        age = int(data.get('age', 51))
        varshphal = {i: [] for i in range(1, 13)}
        for p in nadi_order:
            n_house = (int(p_data[p]['lon']/30) + 1 - asc_sign + 12) % 12 + 1
            varshphal[LK_MATRIX[age - 1][n_house - 1]].append(p[:2])

        return jsonify({
            "status": "success",
            "planets": planet_res, "cusps": cusp_res, "nadi": nadi_res,
            "hits_p2p": hits_p2p, "hits_p2h": hits_p2h,
            "svg_lagna": draw_svg_square(h_lagna, lagna_signs, "Lagna"),
            "svg_chalit": draw_svg_square(h_chalit, chalit_signs, "Chalit"),
            "svg_lk": draw_svg_lk(varshphal)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
