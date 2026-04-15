from flask import Flask, request, jsonify
import swisseph as swe
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# ── LAL KITAB 1952 ENGINE MATRIX ──────────────────────────────────────────
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

swe.set_ephe_path('')
swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)

PLANETS = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE}
LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
YRS = [7, 20, 6, 10, 7, 18, 16, 19, 17]
ZODIAC = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
SIGN_LORDS = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]

def format_dms(d):
    d_val = d % 30
    deg = int(d_val)
    m = int((d_val-deg)*60)
    s = int((d_val-deg-m/60)*3600)
    return f"{deg:02d}° {m:02d}' {s:02d}\""

def get_kp_lords(lon):
    sp = 360/27
    n = int(lon/sp)
    st = LORDS[n%9]
    rem = lon - (n*sp)
    ps = 0.0
    sb = ""
    ssb = ""
    sidx = 0
    s_sp = 0
    for i in range(9):
        idx = (n%9 + i)%9
        s_sp = (YRS[idx]/120)*sp
        ps += s_sp
        if rem <= ps: 
            sb = LORDS[idx]
            sidx = idx
            break
    rem_s = rem - (ps - s_sp)
    ps_s = 0.0
    for i in range(9):
        idx = (sidx + i)%9
        ss_sp = (YRS[idx]/120)*s_sp
        ps_s += ss_sp
        if rem_s <= ps_s: 
            ssb = LORDS[idx]
            break
    return st, sb, ssb

def get_kp_color(p_name):
    colors = {"Sun": "#b03a2e", "Moon": "#21618c", "Mars": "#cb4335", "Mercury": "#1e8449", "Jupiter": "#d35400", "Venus": "#c71585", "Saturn": "#2874a6", "Rahu": "#873600", "Ketu": "#873600", "Asc": "#d35400"}
    for key in colors:
        if key in p_name: return colors[key]
    return "#000000"

def generate_svg_chart(house_data, cusp_signs):
    svg = '<svg viewBox="0 0 400 400" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">\n'
    svg += '<rect x="0" y="0" width="400" height="400" fill="#fdf0d5"/>\n' 
    gc = "#8c7b65"
    gw = "1.5"
    svg += f'<line x1="2" y1="2" x2="398" y2="398" stroke="{gc}" stroke-width="{gw}"/>\n'
    svg += f'<line x1="398" y1="2" x2="2" y2="398" stroke="{gc}" stroke-width="{gw}"/>\n'
    svg += f'<polygon points="200,2 2,200 200,398 398,200" fill="none" stroke="{gc}" stroke-width="{gw}"/>\n'
    svg += f'<rect x="2" y="2" width="396" height="396" fill="none" stroke="{gc}" stroke-width="2.5"/>\n'

    pos_planets = {1: (200, 100), 2: (100, 50), 3: (50, 100), 4: (100, 200), 5: (50, 300), 6: (100, 350), 7: (200, 300), 8: (300, 350), 9: (350, 300), 10: (300, 200), 11: (350, 100), 12: (300, 50)}
    pos_signs = {1: (200, 165), 2: (100, 75), 3: (75, 100), 4: (165, 200), 5: (75, 300), 6: (100, 325), 7: (200, 235), 8: (300, 325), 9: (325, 300), 10: (235, 200), 11: (325, 100), 12: (300, 75)}

    for i in range(1, 13):
        sx, sy = pos_signs[i]
        svg += f'<text x="{sx}" y="{sy+4}" text-anchor="middle" font-size="12" font-family="Arial" font-weight="bold" fill="#1e8449">{cusp_signs[i-1]}</text>\n'
        px, py = pos_planets[i]
        planets = house_data.get(i, [])
        if planets:
            current_y = py - ((len(planets) - 1) * 7.5) 
            for p in planets:
                fill_c = get_kp_color(p)
                svg += f'<text x="{px}" y="{current_y}" text-anchor="middle" font-size="12" font-family="Arial" font-weight="bold" fill="{fill_c}">{p}</text>\n'
                current_y += 15
    svg += '</svg>'
    return svg

def generate_lk_svg(house_data):
    svg = '<svg viewBox="0 0 400 400" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">\n'
    svg += '<rect x="0" y="0" width="400" height="400" fill="#ffffff"/>\n' 
    gc = "#8b0000"
    gw = "1.5"
    cx, cy, R = 200, 200, 190
    x1, y1, x2, y2 = cx - R, cy - R, cx + R, cy + R
    
    svg += f'<rect x="{x1}" y="{y1}" width="{R*2}" height="{R*2}" fill="none" stroke="{gc}" stroke-width="{gw}"/>\n'
    svg += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{gc}" stroke-width="{gw}"/>\n'
    svg += f'<line x1="{x2}" y1="{y1}" x2="{x1}" y2="{y2}" stroke="{gc}" stroke-width="{gw}"/>\n'
    svg += f'<polygon points="{cx},{y1} {x2},{cy} {cx},{y2} {x1},{cy}" fill="none" stroke="{gc}" stroke-width="{gw}"/>\n'

    pos = {1: (cx, cy - R/2), 2: (cx - R/2, cy - 3*R/4), 3: (cx - 3*R/4, cy - R/2), 4: (cx - R/2, cy), 5: (cx - 3*R/4, cy + R/2), 6: (cx - R/2, cy + 3*R/4), 7: (cx, cy + R/2), 8: (cx + R/2, cy + 3*R/4), 9: (cx + 3*R/4, cy + R/2), 10: (cx + R/2, cy), 11: (cx + 3*R/4, cy - R/2), 12: (cx + R/2, cy - 3*R/4)}
    offsets = {1: (0, -25), 2: (0, -15), 3: (-15, 0), 4: (-25, 0), 5: (-15, 0), 6: (0, 15), 7: (0, 25), 8: (0, 15), 9: (15, 0), 10: (25, 0), 11: (15, 0), 12: (0, -15)}

    for i in range(1, 13):
        px, py = pos[i]
        ox, oy = offsets[i]
        svg += f'<text x="{px + ox}" y="{py + oy + 4}" text-anchor="middle" font-size="11" font-family="Arial" fill="#c0392b">{i}</text>\n'
        planets = house_data.get(i, [])
        if planets:
            current_y = py - ((len(planets) - 1) * 7.5)
            for p in planets:
                p_color = get_kp_color(p)
                svg += f'<text x="{px}" y="{current_y}" text-anchor="middle" font-size="11" font-family="Arial" fill="{p_color}">{p}</text>\n'
                current_y += 15
    svg += '</svg>'
    return svg

# --- HTML FRONTEND ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KP Astro Master Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('border-blue-500', 'text-blue-600'));
            document.getElementById(tabId).classList.remove('hidden');
            event.currentTarget.classList.add('border-blue-500', 'text-blue-600');
        }
    </script>
</head>
<body class="bg-gray-50 text-gray-800 font-sans">
    <div class="max-w-7xl mx-auto p-4">
        <h1 class="text-3xl font-extrabold text-blue-900 mb-6">KP Astro Master Dashboard</h1>

        <div class="bg-white rounded-lg shadow p-4 mb-6 grid grid-cols-1 md:grid-cols-6 gap-4">
            <div><label class="text-xs font-bold text-gray-600">Date</label><input type="text" id="date" value="01-09-1975" class="w-full border rounded p-2"></div>
            <div><label class="text-xs font-bold text-gray-600">Time</label><input type="text" id="time" value="05:16:00" class="w-full border rounded p-2"></div>
            <div><label class="text-xs font-bold text-gray-600">Lat</label><input type="text" id="lat" value="30.9010" class="w-full border rounded p-2"></div>
            <div><label class="text-xs font-bold text-gray-600">Lon</label><input type="text" id="lon" value="75.8573" class="w-full border rounded p-2"></div>
            <div><label class="text-xs font-bold text-gray-600">Target Age (Lal Kitab)</label><input type="number" id="age" value="51" class="w-full border rounded p-2"></div>
            <div class="flex items-end"><button onclick="generate()" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 rounded">Calculate</button></div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div class="bg-white rounded shadow p-4 text-center"><h3 class="font-bold mb-2">Lagna Chart</h3><div id="lagna-svg"></div></div>
            <div class="bg-white rounded shadow p-4 text-center"><h3 class="font-bold mb-2">Bhava Chalit</h3><div id="chalit-svg"></div></div>
            <div class="bg-white rounded shadow p-4 text-center"><h3 class="font-bold mb-2">Lal Kitab Varshphal</h3><div id="lk-svg"></div></div>
        </div>

        <div class="border-b border-gray-200 mb-6">
            <nav class="-mb-px flex space-x-8">
                <button onclick="switchTab('tab-basic')" class="tab-btn whitespace-nowrap py-4 px-1 border-b-2 border-blue-500 text-blue-600 font-medium text-sm">Positions</button>
                <button onclick="switchTab('tab-nadi')" class="tab-btn whitespace-nowrap py-4 px-1 border-b-2 border-transparent font-medium text-sm hover:border-gray-300">Nadi Significators</button>
            </nav>
        </div>

        <div id="tab-basic" class="tab-content grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="bg-white shadow rounded overflow-x-auto">
                <table class="min-w-full text-sm text-center">
                    <thead class="bg-gray-100 font-bold"><tr><th class="p-2">Planet</th><th class="p-2">Sign</th><th class="p-2">Degree</th><th class="p-2">Star L</th><th class="p-2">Sub L</th><th class="p-2">S-Sub</th></tr></thead>
                    <tbody id="p-body"></tbody>
                </table>
            </div>
            <div class="bg-white shadow rounded overflow-x-auto">
                <table class="min-w-full text-sm text-center">
                    <thead class="bg-gray-100 font-bold"><tr><th class="p-2">House</th><th class="p-2">Sign</th><th class="p-2">Degree</th><th class="p-2">Star L</th><th class="p-2">Sub L</th><th class="p-2">S-Sub</th></tr></thead>
                    <tbody id="c-body"></tbody>
                </table>
            </div>
        </div>

        <div id="tab-nadi" class="tab-content hidden bg-white shadow rounded p-4 overflow-x-auto">
            <table class="min-w-full text-sm text-center border">
                <thead class="bg-blue-900 text-white font-bold">
                    <tr><th class="p-2">PLANET</th><th class="p-2">P-SIGNIFS</th><th class="p-2">STAR LORD</th><th class="p-2">ST-SIGNIFS</th><th class="p-2">SUB LORD</th><th class="p-2">SB-SIGNIFS</th></tr>
                </thead>
                <tbody id="n-body"></tbody>
            </table>
        </div>
    </div>

    <script>
        async function generate() {
            const payload = {
                date: document.getElementById('date').value, time: document.getElementById('time').value,
                lat: document.getElementById('lat').value, lon: document.getElementById('lon').value,
                age: document.getElementById('age').value
            };
            const res = await fetch('/api/calc', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const d = await res.json();
            
            document.getElementById('lagna-svg').innerHTML = d.svg_lagna;
            document.getElementById('chalit-svg').innerHTML = d.svg_chalit;
            document.getElementById('lk-svg').innerHTML = d.svg_lk;

            document.getElementById('p-body').innerHTML = d.planets.map((r,i) => `<tr class="${i%2==0?'bg-white':'bg-gray-50'} border-t"><td class="p-2 font-bold">${r[0]}</td><td class="p-2 text-blue-700 font-bold">${r[1]}</td><td class="p-2">${r[2]}</td><td class="p-2">${r[3]}</td><td class="p-2">${r[4]}</td><td class="p-2">${r[5]}</td></tr>`).join('');
            document.getElementById('c-body').innerHTML = d.cusps.map((r,i) => `<tr class="${i%2==0?'bg-white':'bg-gray-50'} border-t"><td class="p-2 font-bold">${r[0]}</td><td class="p-2 text-green-700 font-bold">${r[1]}</td><td class="p-2">${r[2]}</td><td class="p-2">${r[3]}</td><td class="p-2">${r[4]}</td><td class="p-2">${r[5]}</td></tr>`).join('');
            document.getElementById('n-body').innerHTML = d.nadi.map((r,i) => `<tr class="${i%2==0?'bg-white':'bg-gray-50'} border-t"><td class="p-2 font-bold">${r[0]}</td><td class="p-2">${r[1]}</td><td class="p-2 font-bold">${r[2]}</td><td class="p-2">${r[3]}</td><td class="p-2 font-bold">${r[4]}</td><td class="p-2">${r[5]}</td></tr>`).join('');
        }
        generate();
    </script>
</body>
</html>
"""

# --- FLASK ROUTES ---
@app.route('/', methods=['GET'])
def home():
    return HTML_PAGE

@app.route('/api/calc', methods=['POST'])
def calc():
    data = request.json
    try:
        dt = datetime.strptime(f"{data['date']} {data['time']}", "%d-%m-%Y %H:%M:%S")
        tz = pytz.timezone('Asia/Kolkata')
        utc_dt = tz.localize(dt).astimezone(pytz.utc)
        jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
        
        flags = swe.FLG_SIDEREAL | swe.FLG_SPEED
        cusps_raw, _ = swe.houses_ex(jd, float(data['lat']), float(data['lon']), b'P', flags=flags)
        
        asc_sign = int(cusps_raw[0] / 30) + 1
        lagna_signs = [((asc_sign + i - 1) % 12) + 1 for i in range(12)]
        chalit_signs = [int(c / 30) + 1 for c in cusps_raw]

        cusp_res = []
        for i in range(12):
            c_lon = cusps_raw[i]
            st, sb, ssb = get_kp_lords(c_lon)
            cusp_res.append([i+1, ZODIAC[int(c_lon/30)], format_dms(c_lon), st, sb, ssb])

        planet_res = []
        p_data = {}
        rahu_lon = 0
        h_lagna = {i: [] for i in range(1, 13)}
        h_chalit = {i: [] for i in range(1, 13)}

        for name, p_id in PLANETS.items():
            calc, _ = swe.calc_ut(jd, p_id, flags)
            lon = calc[0]
            if name == "Rahu": rahu_lon = lon
            
            is_retro = calc[3] < 0 if name not in ["Sun", "Moon"] else False
            disp = f"{name}(R)" if is_retro else name
            st, sb, ssb = get_kp_lords(lon)
            planet_res.append([disp, ZODIAC[int(lon/30)], format_dms(lon), st, sb, ssb])
            p_data[name] = {"lon": lon, "st": st, "sb": sb}

            p_sign = int(lon/30) + 1
            l_house = (p_sign - asc_sign + 12) % 12 + 1
            h_lagna[l_house].append(name[:2])
            
            for h_idx in range(12):
                h_s, h_e = cusps_raw[h_idx], cusps_raw[(h_idx + 1) % 12]
                if (h_s < h_e and h_s <= lon < h_e) or (h_s > h_e and (lon >= h_s or lon < h_e)):
                    h_chalit[h_idx+1].append(name[:2])
                    break

        # Add Ketu
        ketu_lon = (rahu_lon + 180.0) % 360.0
        st, sb, ssb = get_kp_lords(ketu_lon)
        planet_res.append(["Ketu(R)", ZODIAC[int(ketu_lon/30)], format_dms(ketu_lon), st, sb, ssb])
        p_data["Ketu"] = {"lon": ketu_lon, "st": st, "sb": sb}
        
        k_sign = int(ketu_lon/30) + 1
        h_lagna[(k_sign - asc_sign + 12) % 12 + 1].append("Ke")
        for h_idx in range(12):
            h_s, h_e = cusps_raw[h_idx], cusps_raw[(h_idx + 1) % 12]
            if (h_s < h_e and h_s <= ketu_lon < h_e) or (h_s > h_e and (ketu_lon >= h_s or ketu_lon < h_e)):
                h_chalit[h_idx+1].append("Ke")
                break

        # Nadi
        nadi_res = []
        nadi_order = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        
        def get_occ(lon):
            for i in range(12):
                h_s, h_e = cusps_raw[i], cusps_raw[(i + 1) % 12]
                if (h_s < h_e and h_s <= lon < h_e) or (h_s > h_e and (lon >= h_s or lon < h_e)): return i + 1
            return 1
            
        base_sigs = {}
        for p in nadi_order:
            lon = p_data[p]['lon']
            occ = get_occ(lon)
            owns = [i+1 for i in range(12) if SIGN_LORDS[chalit_signs[i]-1] == p] if p not in ["Rahu", "Ketu"] else []
            base_sigs[p] = {'occ': occ, 'owns': owns}

        for p in nadi_order:
            sig = sorted(list(set([base_sigs[p]['occ']] + base_sigs[p]['owns'])))
            st = p_data[p]['st']
            st_sig = sorted(list(set([base_sigs[st]['occ']] + base_sigs[st]['owns'])))
            sb = p_data[p]['sb']
            sb_sig = sorted(list(set([base_sigs[sb]['occ']] + base_sigs[sb]['owns'])))
            
            nadi_res.append([p, ", ".join(map(str, sig)) or "-", st, ", ".join(map(str, st_sig)) or "-", sb, ", ".join(map(str, sb_sig)) or "-"])

        # Lal Kitab
        age = int(data.get('age', 51))
        varshphal = {i: [] for i in range(1, 13)}
        for p_name in nadi_order:
            lon = p_data[p_name]['lon']
            natal_house = (int(lon/30) + 1 - asc_sign + 12) % 12 + 1
            v_house = LK_MATRIX[age - 1][natal_house - 1]
            varshphal[v_house].append(p_name[:2])

        return jsonify({
            "status": "success",
            "planets": planet_res,
            "cusps": cusp_res,
            "nadi": nadi_res,
            "svg_lagna": generate_svg_chart(h_lagna, lagna_signs),
            "svg_chalit": generate_svg_chart(h_chalit, chalit_signs),
            "svg_lk": generate_lk_svg(varshphal)
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)