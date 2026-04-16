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
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
DEGREE_ASPECTS = {0: ("Conjunction", "Variable"), 30: ("Semi-Sextile", "Positive"), 45: ("Semi-Square", "Negative"), 60: ("Sextile", "Positive"), 90: ("Square", "Negative"), 120: ("Trine", "Positive"), 135: ("Sesquisquare", "Negative"), 180: ("Opposition", "Negative")}

SIGN_PROPS = { 
    1: {"dir": "E/ESE6", "tatwa": "Fire", "mob": "Movable", "gender": "M"},
    2: {"dir": "WNW/NW", "tatwa": "Earth", "mob": "Fixed", "gender": "F"},
    3: {"dir": "NNW", "tatwa": "Air", "mob": "Dual", "gender": "M"},
    4: {"dir": "NNE", "tatwa": "Water", "mob": "Movable", "gender": "F"},
    5: {"dir": "ENE", "tatwa": "Fire", "mob": "Fixed", "gender": "M"},
    6: {"dir": "N", "tatwa": "Earth", "mob": "Dual", "gender": "F"},
    7: {"dir": "WSW", "tatwa": "Air", "mob": "Movable", "gender": "M"},
    8: {"dir": "SSW", "tatwa": "Water", "mob": "Fixed", "gender": "F"},
    9: {"dir": "NE", "tatwa": "Fire", "mob": "Dual", "gender": "M"},
    10: {"dir": "SSE/S", "tatwa": "Earth", "mob": "Movable", "gender": "F"},
    11: {"dir": "W", "tatwa": "Air", "mob": "Fixed", "gender": "M"},
    12: {"dir": "ESE7/SE", "tatwa": "Water", "mob": "Dual", "gender": "F"}
}

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
        # Draw fixed Kal Purush numbers as requested in Ledger
        svg += f'<text x="{px + ox}" y="{py + oy + 4}" text-anchor="middle" font-size="11" font-family="Arial" fill="#c0392b">{i}</text>\n'
        planets = house_data.get(i, [])
        if planets:
            cY = py - ((len(planets) - 1) * 7.5)
            for p in planets:
                svg += f'<text x="{px}" y="{cY}" text-anchor="middle" font-size="11" font-family="Arial" fill="{get_kp_color(p)}">{p}</text>\n'
                cY += 15
    svg += '</svg>'
    return svg

def calculate_dasha(moon_lon, start_dt, current_eval_dt):
    nak_span = 360 / 27
    nak_val = moon_lon / nak_span
    idx = int(nak_val) % 9
    rem_prc = 1.0 - (nak_val - int(nak_val))
    
    bal_days = rem_prc * YRS[idx] * 365.2425
    bal_y = int(bal_days // 365.2425)
    rem_m = (bal_days % 365.2425) / 30.436875
    bal_m = int(rem_m)
    bal_d = int((rem_m - bal_m) * 30.436875)
    balance_str = f"Balance of Dasha: {LORDS[idx]} {bal_y}Y {bal_m}M {bal_d}D"
    
    dasha_list = []
    md_start = start_dt - timedelta(days=(1 - rem_prc) * YRS[idx] * 365.2425)
    
    # 5-Level Deep Dasha Loop
    for i in range(9):
        md_idx = (idx + i) % 9
        md_days = YRS[md_idx] * 365.2425
        md_end = md_start + timedelta(days=md_days)
        md_active = md_start <= current_eval_dt < md_end
        
        ad_list = []
        ad_start = md_start
        for j in range(9):
            ad_idx = (md_idx + j) % 9
            ad_days = md_days * (YRS[ad_idx] / 120.0)
            ad_end = ad_start + timedelta(days=ad_days)
            ad_active = ad_start <= current_eval_dt < ad_end
            
            pd_list = []
            pd_start = ad_start
            for k in range(9):
                pd_idx = (ad_idx + k) % 9
                pd_days = ad_days * (YRS[pd_idx] / 120.0)
                pd_end = pd_start + timedelta(days=pd_days)
                pd_active = pd_start <= current_eval_dt < pd_end
                
                sd_list = []
                sd_start = pd_start
                for l in range(9):
                    sd_idx = (pd_idx + l) % 9
                    sd_days = pd_days * (YRS[sd_idx] / 120.0)
                    sd_end = sd_start + timedelta(days=sd_days)
                    sd_active = sd_start <= current_eval_dt < sd_end
                    
                    prd_list = []
                    prd_start = sd_start
                    for m in range(9):
                        prd_idx = (sd_idx + m) % 9
                        prd_days = sd_days * (YRS[prd_idx] / 120.0)
                        prd_end = prd_start + timedelta(days=prd_days)
                        prd_active = prd_start <= current_eval_dt < prd_end
                        
                        prd_list.append({
                            "lord": LORDS[prd_idx],
                            "start": prd_start.strftime("%d-%m-%Y %H:%M"),
                            "end": prd_end.strftime("%d-%m-%Y %H:%M"),
                            "active": prd_active
                        })
                        prd_start = prd_end
                    
                    sd_list.append({
                        "lord": LORDS[sd_idx],
                        "start": sd_start.strftime("%d-%m-%Y %H:%M"),
                        "end": sd_end.strftime("%d-%m-%Y %H:%M"),
                        "active": sd_active,
                        "subs": prd_list
                    })
                    sd_start = sd_end
                    
                pd_list.append({
                    "lord": LORDS[pd_idx],
                    "start": pd_start.strftime("%d-%m-%Y"),
                    "end": pd_end.strftime("%d-%m-%Y"),
                    "active": pd_active,
                    "subs": sd_list
                })
                pd_start = pd_end
                
            ad_list.append({
                "lord": LORDS[ad_idx],
                "start": ad_start.strftime("%d-%m-%Y"),
                "end": ad_end.strftime("%d-%m-%Y"),
                "active": ad_active,
                "subs": pd_list
            })
            ad_start = ad_end
            
        dasha_list.append({
            "lord": LORDS[md_idx],
            "start": md_start.strftime("%d-%m-%Y"),
            "end": md_end.strftime("%d-%m-%Y"),
            "active": md_active,
            "subs": ad_list
        })
        md_start = md_end
        
    return dasha_list, balance_str

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
        .modal { background-color: rgba(0,0,0,0.5); }
    </style>
</head>
<body class="bg-gray-100 text-gray-800 font-sans relative">

    <div id="input-screen" class="min-h-screen flex items-center justify-center p-4">
        <div class="bg-white rounded-xl shadow-xl p-8 max-w-3xl w-full border border-gray-200">
            <h1 class="text-3xl font-extrabold text-center text-blue-900 mb-8 tracking-wide drop-shadow-sm">KP Astrology Pro Setup</h1>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div><label class="block text-sm font-bold text-blue-900 mb-1">Name</label><input type="text" id="i-name" value="Happy" class="w-full border border-gray-200 rounded p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"></div>
                <div><label class="block text-sm font-bold text-blue-900 mb-1">DOB (DD-MM-YYYY)</label><input type="text" id="i-dob" value="01-09-1975" class="w-full border border-gray-200 rounded p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"></div>
                <div><label class="block text-sm font-bold text-blue-900 mb-1">Time (HH:MM:SS)</label><input type="text" id="i-time" value="05:16:00" class="w-full border border-gray-200 rounded p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"></div>
                
                <div>
                    <label class="block text-sm font-bold text-blue-900 mb-1">City</label>
                    <div class="relative">
                        <input type="text" id="i-city" value="Ludhiana" onblur="fetchLocation()" class="w-full border border-gray-200 rounded p-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                        <span id="city-status" class="absolute right-2 top-3 text-xs font-bold text-blue-600"></span>
                    </div>
                </div>

                <div><label class="block text-sm font-bold text-blue-900 mb-1">Latitude</label><input type="text" id="i-lat" value="30.9010" class="w-full border border-gray-200 rounded p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"></div>
                <div><label class="block text-sm font-bold text-blue-900 mb-1">Longitude</label><input type="text" id="i-lon" value="75.8573" class="w-full border border-gray-200 rounded p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"></div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div>
                    <label class="block text-sm font-bold text-blue-900 mb-1">Timezone</label>
                    <input type="text" id="i-tz" value="Asia/Kolkata" class="w-full border border-gray-200 rounded p-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                </div>
                <div><label class="block text-sm font-bold text-blue-900 mb-1">Horary (1-249)</label><input type="number" id="i-horary" value="1" class="w-full border border-gray-200 rounded p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"></div>
                <div>
                    <label class="block text-sm font-bold text-blue-900 mb-1">Ayanamsa</label>
                    <select id="i-aya" class="w-full border border-gray-200 rounded p-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                        <option value="Chitrapaksha" selected>Lahiri</option>
                        <option value="K.P.">K.P.</option>
                        <option value="Raman">Raman</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-bold text-blue-900 mb-1">Rahu</label>
                    <select id="i-rahu" class="w-full border border-gray-200 rounded p-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                        <option value="Mean">Mean Node</option>
                        <option value="True">True Node</option>
                    </select>
                </div>
            </div>

            <button onclick="openDashboard()" class="w-full bg-[#16a34a] hover:bg-[#15803d] text-white font-bold py-3 px-4 rounded text-lg shadow drop-shadow-md tracking-wider">
                OPEN DASHBOARD
            </button>
        </div>
    </div>

    <div id="dashboard-screen" class="hidden p-4 max-w-7xl mx-auto">
        <div class="flex flex-col md:flex-row justify-between items-center mb-4 bg-[#1e3a8a] text-white p-4 rounded shadow gap-4">
            <div>
                <h2 class="text-2xl font-bold tracking-wide" id="d-name">Client Name</h2>
                <p class="text-sm text-blue-200 font-semibold mt-1" id="d-details">DOB | Time | Place</p>
            </div>
            <div class="flex items-center gap-3 flex-wrap justify-end">
                <button onclick="generateMasterReport()" class="bg-blue-500 hover:bg-blue-600 px-3 py-1 rounded font-bold text-sm shadow text-white">Print Report 📄</button>
                <button onclick="openModal('forward-modal')" class="bg-orange-500 hover:bg-orange-600 px-3 py-1 rounded font-bold text-sm shadow">Forward Check 🔎</button>
                <button onclick="openModal('ssub-modal')" class="bg-teal-500 hover:bg-teal-600 px-3 py-1 rounded font-bold text-sm shadow">S-Sub Tracker ⏱️</button>
                <button onclick="openModal('retro-modal')" class="bg-purple-500 hover:bg-purple-600 px-3 py-1 rounded font-bold text-sm shadow">Retro Report 🔄</button>
                <div class="flex flex-col border-l border-blue-400 pl-3 ml-1">
                    <label class="text-xs font-bold text-blue-200">Lal Kitab Age</label>
                    <input type="number" id="d-age" class="text-black w-16 p-1 rounded font-bold focus:outline-none" onchange="fetchData()">
                </div>
                <button onclick="backToInput()" class="bg-red-500 hover:bg-red-600 px-4 py-2 rounded font-bold mt-4 md:mt-0 shadow ml-2">Close</button>
            </div>
        </div>

        <div class="bg-white p-4 rounded shadow mb-6 flex flex-wrap gap-4 items-center justify-between border border-gray-200">
            <div class="flex items-center gap-2">
                <label class="font-bold text-sm text-blue-900">Mode:</label>
                <select id="ctrl-mode" class="border border-gray-300 p-1 rounded bg-gray-50 focus:outline-none" onchange="modeChanged()">
                    <option value="Natal">Natal</option>
                    <option value="Transit">Transit</option>
                    <option value="Horary">Horary</option>
                </select>
            </div>
            
            <div class="flex items-center gap-2">
                <label class="font-bold text-sm text-blue-900">Revolve House:</label>
                <select id="ctrl-rot" class="border border-gray-300 p-1 rounded bg-gray-50 focus:outline-none" onchange="fetchData()">
                    <option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4">4</option>
                    <option value="5">5</option><option value="6">6</option><option value="7">7</option><option value="8">8</option>
                    <option value="9">9</option><option value="10">10</option><option value="11">11</option><option value="12">12</option>
                </select>
            </div>

            <div class="flex items-center gap-2 text-sm font-bold">
                <div class="flex items-center bg-gray-100 rounded px-2 py-1 shadow-sm"><button onclick="adjTime(-1, 'y')" class="text-red-500 px-1 hover:text-red-700">-</button>Year<button onclick="adjTime(1, 'y')" class="text-green-500 px-1 hover:text-green-700">+</button></div>
                <div class="flex items-center bg-gray-100 rounded px-2 py-1 shadow-sm"><button onclick="adjTime(-1, 'm')" class="text-red-500 px-1 hover:text-red-700">-</button>Month<button onclick="adjTime(1, 'm')" class="text-green-500 px-1 hover:text-green-700">+</button></div>
                <div class="flex items-center bg-gray-100 rounded px-2 py-1 shadow-sm"><button onclick="adjTime(-1, 'd')" class="text-red-500 px-1 hover:text-red-700">-</button>Day<button onclick="adjTime(1, 'd')" class="text-green-500 px-1 hover:text-green-700">+</button></div>
                <div class="flex items-center bg-gray-100 rounded px-2 py-1 shadow-sm"><button onclick="adjTime(-1, 'h')" class="text-red-500 px-1 hover:text-red-700">-</button>Hour<button onclick="adjTime(1, 'h')" class="text-green-500 px-1 hover:text-green-700">+</button></div>
                <div class="flex items-center bg-gray-100 rounded px-2 py-1 shadow-sm"><button onclick="adjTime(-1, 'min')" class="text-red-500 px-1 hover:text-red-700">-</button>Min<button onclick="adjTime(1, 'min')" class="text-green-500 px-1 hover:text-green-700">+</button></div>
            </div>

            <div class="font-bold text-red-600 bg-red-50 border border-red-100 px-3 py-1 rounded" id="current-chart-time">--</div>
        </div>

        <div id="loader" class="hidden text-center text-blue-600 font-bold text-xl my-8">Calculating Ephemeris Data... Please wait.</div>

        <div id="content-wrap" class="hidden">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <div class="bg-white rounded shadow p-4"><h3 class="font-bold text-center text-blue-900 mb-2 tracking-wide" id="title-lagna">Lagna Chart</h3><div id="svg-lagna"></div></div>
                <div class="bg-white rounded shadow p-4"><h3 class="font-bold text-center text-green-900 mb-2 tracking-wide" id="title-chalit">Bhava Chalit</h3><div id="svg-chalit"></div></div>
                <div class="bg-white rounded shadow p-4"><h3 class="font-bold text-center text-red-900 mb-2 tracking-wide" id="title-lk">Lal Kitab Varshphal</h3><div id="svg-lk"></div></div>
            </div>

            <div class="border-b border-gray-300 mb-6 flex space-x-4 overflow-x-auto">
                <button onclick="switchTab('tab-pos', this)" class="tab-btn active px-4 py-2 border-b-2 border-blue-500 text-blue-600 font-bold whitespace-nowrap">Positions</button>
                <button onclick="switchTab('tab-nadi', this)" class="tab-btn px-4 py-2 border-b-2 border-transparent font-bold whitespace-nowrap">Nadi</button>
                <button onclick="switchTab('tab-hits', this)" class="tab-btn px-4 py-2 border-b-2 border-transparent font-bold whitespace-nowrap">Degree Hits</button>
                <button onclick="switchTab('tab-vastu', this)" class="tab-btn px-4 py-2 border-b-2 border-transparent font-bold whitespace-nowrap text-green-700">Astro Vastu</button>
                <button onclick="switchTab('tab-dasha', this)" class="tab-btn px-4 py-2 border-b-2 border-transparent font-bold whitespace-nowrap text-purple-700">Vimshottari Dasha</button>
            </div>

            <div id="tab-pos" class="tab-pane grid grid-cols-1 xl:grid-cols-2 gap-6">
                <div class="bg-white shadow rounded overflow-x-auto border border-gray-200">
                    <h3 class="font-bold text-blue-900 p-3 bg-gray-50 border-b">Planetary Positions</h3>
                    <table class="w-full text-xs text-center border-collapse">
                        <thead class="bg-[#1e3a8a] text-white"><tr><th class="p-2 border border-blue-800">Planet</th><th class="p-2 border border-blue-800">Sign</th><th class="p-2 border border-blue-800">Degree</th><th class="p-2 border border-blue-800">Nakshatra</th><th class="p-2 border border-blue-800">Star L</th><th class="p-2 border border-blue-800">Sub L</th><th class="p-2 border border-blue-800">S-Sub</th></tr></thead>
                        <tbody id="tb-planets"></tbody>
                    </table>
                </div>
                <div class="bg-white shadow rounded overflow-x-auto border border-gray-200">
                    <h3 class="font-bold text-green-900 p-3 bg-gray-50 border-b">Cusp Positions</h3>
                    <table class="w-full text-xs text-center border-collapse">
                        <thead class="bg-[#1e3a8a] text-white"><tr><th class="p-2 border border-blue-800">House</th><th class="p-2 border border-blue-800">Sign</th><th class="p-2 border border-blue-800">Degree</th><th class="p-2 border border-blue-800">Nakshatra</th><th class="p-2 border border-blue-800">Star L</th><th class="p-2 border border-blue-800">Sub L</th><th class="p-2 border border-blue-800">S-Sub</th></tr></thead>
                        <tbody id="tb-cusps"></tbody>
                    </table>
                </div>
            </div>

            <div id="tab-nadi" class="tab-pane hidden bg-white shadow rounded overflow-x-auto border border-gray-200">
                <table class="w-full text-sm text-center border-collapse">
                    <thead class="bg-[#1e3a8a] text-white">
                        <tr>
                            <th class="p-3 border border-blue-800">PLANET</th>
                            <th class="p-3 border border-blue-800">P-SIGNIFS</th>
                            <th class="p-3 border border-blue-800">STAR LORD</th>
                            <th class="p-3 border border-blue-800">ST-SIGNIFS</th>
                            <th class="p-3 border border-blue-800">SUB LORD</th>
                            <th class="p-3 border border-blue-800">SB-SIGNIFS</th>
                        </tr>
                    </thead>
                    <tbody id="tb-nadi"></tbody>
                </table>
            </div>

            <div id="tab-hits" class="tab-pane hidden grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="bg-white shadow rounded overflow-x-auto border border-gray-200">
                    <h3 class="font-bold text-gray-800 p-3 bg-gray-50 border-b">Planet to Planet</h3>
                    <table class="w-full text-xs text-center border-collapse">
                        <thead class="bg-[#1e3a8a] text-white"><tr><th class="p-2 border border-blue-800">P1</th><th class="p-2 border border-blue-800">P2</th><th class="p-2 border border-blue-800">Aspect</th><th class="p-2 border border-blue-800">Diff</th><th class="p-2 border border-blue-800">Nature</th></tr></thead>
                        <tbody id="tb-p2p"></tbody>
                    </table>
                </div>
                <div class="bg-white shadow rounded overflow-x-auto border border-gray-200">
                    <h3 class="font-bold text-gray-800 p-3 bg-gray-50 border-b">Planet to House</h3>
                    <table class="w-full text-xs text-center border-collapse">
                        <thead class="bg-[#1e3a8a] text-white"><tr><th class="p-2 border border-blue-800">Planet</th><th class="p-2 border border-blue-800">House</th><th class="p-2 border border-blue-800">Aspect</th><th class="p-2 border border-blue-800">Diff</th><th class="p-2 border border-blue-800">Nature</th></tr></thead>
                        <tbody id="tb-p2h"></tbody>
                    </table>
                </div>
            </div>

            <div id="tab-vastu" class="tab-pane hidden grid grid-cols-1 gap-6">
                <div class="bg-white shadow rounded overflow-x-auto border border-gray-200">
                    <h3 class="font-bold text-green-900 p-3 bg-gray-50 border-b">Planet to House (Directional Aspects)</h3>
                    <table class="w-full text-xs text-center border-collapse" style="table-layout: fixed; word-wrap: break-word;">
                        <thead id="th-vastu-p2c"></thead>
                        <tbody id="tb-vastu-p2c"></tbody>
                    </table>
                </div>
                <div class="bg-white shadow rounded overflow-x-auto border border-gray-200">
                    <h3 class="font-bold text-blue-900 p-3 bg-gray-50 border-b">Planet to Planet (Directional Aspects)</h3>
                    <table class="w-full text-xs text-center border-collapse">
                        <thead class="bg-[#1e3a8a] text-white"><tr><th class="p-2 border border-blue-800">FROM</th><th class="p-2 border border-blue-800">DIR 1</th><th class="p-2 border border-blue-800">TO</th><th class="p-2 border border-blue-800">DIR 2</th><th class="p-2 border border-blue-800">ASP</th></tr></thead>
                        <tbody id="tb-vastu-p2p"></tbody>
                    </table>
                </div>
            </div>
            
            <div id="tab-dasha" class="tab-pane hidden bg-white shadow rounded p-4 overflow-auto max-h-[600px] border border-gray-200">
                <h3 class="font-bold text-purple-900 mb-2">Vimshottari Dasha (5 Levels)</h3>
                <p id="dasha-bal" class="font-bold text-red-600 mb-4"></p>
                <table class="w-full text-sm text-left border-collapse">
                    <thead class="bg-[#1e3a8a] text-white sticky top-0"><tr><th class="p-2 border border-blue-800 w-1/2">Dasha Lord</th><th class="p-2 border border-blue-800 w-1/4">Start Date</th><th class="p-2 border border-blue-800 w-1/4">End Date</th></tr></thead>
                    <tbody id="tb-dasha"></tbody>
                </table>
            </div>
        </div>
    </div>

    <div id="ssub-modal" class="modal hidden fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="bg-gray-100 rounded-lg shadow-2xl p-6 max-w-5xl w-full border-4 border-teal-500 relative flex flex-col max-h-[90vh]">
            <button onclick="closeModal('ssub-modal')" class="absolute top-4 right-4 font-bold text-2xl text-gray-700 hover:text-black focus:outline-none">&times;</button>
            <h2 class="text-2xl font-bold text-teal-800 mb-4 tracking-wide">Planet Sub-Sub Lord Tracker Matrix</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4 shrink-0">
                <div><label class="text-xs font-bold text-gray-700 mb-1 block">From (DD-MM-YYYY HH:MM:SS)</label><input type="text" id="ss-start" class="w-full border p-2 rounded bg-white focus:outline-none focus:ring-1 focus:ring-teal-400"></div>
                <div><label class="text-xs font-bold text-gray-700 mb-1 block">To (DD-MM-YYYY HH:MM:SS)</label><input type="text" id="ss-end" class="w-full border p-2 rounded bg-white focus:outline-none focus:ring-1 focus:ring-teal-400"></div>
            </div>
            <button onclick="runSSubTracker()" class="w-full bg-teal-600 hover:bg-teal-700 text-white font-bold py-2 rounded mb-4 shadow transition-colors shrink-0">Generate Matrix (Max 3 Days)</button>
            
            <div id="ss-loader" class="hidden text-center text-teal-600 font-bold py-4 shrink-0">Calculating exact matrix minute-by-minute... This may take a few seconds.</div>
            
            <div class="overflow-y-auto border border-gray-300 rounded p-4 bg-white flex-1" id="ss-body"></div>
        </div>
    </div>

    <div id="forward-modal" class="modal hidden fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="bg-[#fcf5cd] rounded-md shadow-2xl p-6 max-w-2xl w-full relative border-2 border-yellow-200">
            <button onclick="closeModal('forward-modal')" class="absolute top-4 right-4 font-bold text-2xl text-gray-700 hover:text-black focus:outline-none">&times;</button>
            <h2 class="text-2xl font-bold text-[#b91c1c] mb-6 tracking-wide">Forward Checking of Planet</h2>
            
            <div class="grid grid-cols-2 gap-x-6 gap-y-4 mb-6">
                <div>
                    <label class="block text-sm font-bold text-[#0f172a] mb-1">Start Date (DD-MM-YYYY)</label>
                    <input type="text" id="fc-date" class="w-full border border-gray-300 p-2 rounded bg-white focus:outline-none focus:ring-1 focus:ring-yellow-400">
                </div>
                <div>
                    <label class="block text-sm font-bold text-[#0f172a] mb-1">Target Type</label>
                    <select id="fc-type" class="w-full border border-gray-300 p-2 rounded bg-white focus:outline-none focus:ring-1 focus:ring-yellow-400">
                        <option value="Sign">Sign (1-12)</option>
                        <option value="Nakshatra">Nakshatra (1-27)</option>
                        <option value="Degree">Exact Degree (0-360)</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-bold text-[#0f172a] mb-1">Planet</label>
                    <select id="fc-planet" class="w-full border border-gray-300 p-2 rounded bg-white focus:outline-none focus:ring-1 focus:ring-yellow-400">
                        <option>Sun</option><option>Moon</option><option>Mars</option><option>Mercury</option><option>Jupiter</option><option>Venus</option><option>Saturn</option><option>Rahu</option><option>Ketu</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-bold text-[#0f172a] mb-1">Target Value</label>
                    <input type="text" id="fc-val" value="1" class="w-full border border-gray-300 p-2 rounded bg-white focus:outline-none focus:ring-1 focus:ring-yellow-400">
                </div>
            </div>
            
            <button onclick="runForwardCheck()" class="w-full bg-[#cbd5e1] hover:bg-[#94a3b8] text-black font-bold py-3 rounded shadow transition-colors">Start Checking (Max 100 Yrs)</button>
            <p id="fc-res" class="mt-6 font-bold text-center text-lg text-[#1d4ed8]"></p>
        </div>
    </div>

    <div id="retro-modal" class="modal hidden fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-lg shadow-2xl p-6 max-w-lg w-full border border-gray-300 relative">
            <button onclick="closeModal('retro-modal')" class="absolute top-4 right-4 font-bold text-2xl text-gray-700 hover:text-black focus:outline-none">&times;</button>
            <h2 class="text-2xl font-bold text-purple-800 mb-6 tracking-wide">Planet Retro/Direct Report</h2>
            <div class="grid grid-cols-3 gap-3 mb-6">
                <div><label class="text-xs font-bold text-gray-700 mb-1 block">From (DD-MM-YYYY)</label><input type="text" id="rr-start" class="w-full border p-2 rounded bg-gray-50 focus:outline-none focus:ring-1 focus:ring-purple-400"></div>
                <div><label class="text-xs font-bold text-gray-700 mb-1 block">To (DD-MM-YYYY)</label><input type="text" id="rr-end" class="w-full border p-2 rounded bg-gray-50 focus:outline-none focus:ring-1 focus:ring-purple-400"></div>
                <div><label class="text-xs font-bold text-gray-700 mb-1 block">Planet</label><select id="rr-planet" class="w-full border p-2 rounded bg-gray-50 focus:outline-none focus:ring-1 focus:ring-purple-400"><option>Mercury</option><option>Venus</option><option>Mars</option><option>Jupiter</option><option>Saturn</option></select></div>
            </div>
            <button onclick="runRetroReport()" class="w-full bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 rounded mb-4 shadow transition-colors">Generate Report</button>
            <div class="h-64 overflow-y-auto border border-gray-200 rounded">
                <table class="w-full text-sm text-center border-collapse">
                    <thead class="bg-gray-100 text-gray-700 sticky top-0 shadow-sm"><tr><th class="p-2 border">Approx Date</th><th class="p-2 border">Movement Change</th></tr></thead>
                    <tbody id="rr-body"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let calcDateObj = new Date();
        let natalDateStr = "";
        let natalTimeStr = "";

        function parseDateStr(dateStr, timeStr) {
            let dmy = dateStr.split('-');
            let hms = timeStr.split(':');
            return new Date(dmy[2], dmy[1]-1, dmy[0], hms[0], hms[1], hms[2]);
        }

        function getFormattedCalc() {
            let pad = (n) => n.toString().padStart(2, '0');
            return {
                d: `${pad(calcDateObj.getDate())}-${pad(calcDateObj.getMonth()+1)}-${calcDateObj.getFullYear()}`,
                t: `${pad(calcDateObj.getHours())}:${pad(calcDateObj.getMinutes())}:${pad(calcDateObj.getSeconds())}`
            };
        }

        async function fetchLocation() {
            const city = document.getElementById('i-city').value;
            if(!city) return;
            const statusLabel = document.getElementById('city-status');
            statusLabel.innerText = "Searching...";
            statusLabel.className = "absolute right-2 top-3 text-xs font-bold text-blue-600";
            try {
                const res = await fetch('/api/location', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({city: city}) });
                const data = await res.json();
                if(data.status === 'success') {
                    document.getElementById('i-lat').value = data.lat;
                    document.getElementById('i-lon').value = data.lon;
                    document.getElementById('i-tz').value = data.tz;
                    statusLabel.innerText = "Found!";
                    statusLabel.classList.replace('text-blue-600', 'text-green-600');
                } else {
                    statusLabel.innerText = "Not found.";
                    statusLabel.classList.replace('text-blue-600', 'text-red-600');
                }
            } catch(e) { statusLabel.innerText = "API Error."; }
        }

        function openDashboard() {
            document.getElementById('input-screen').classList.add('hidden');
            document.getElementById('dashboard-screen').classList.remove('hidden');
            document.getElementById('d-name').innerText = document.getElementById('i-name').value;
            natalDateStr = document.getElementById('i-dob').value;
            natalTimeStr = document.getElementById('i-time').value;
            document.getElementById('d-details').innerText = `${natalDateStr} | ${natalTimeStr} | TZ: ${document.getElementById('i-tz').value}`;
            
            document.getElementById('ctrl-mode').value = "Natal";
            calcDateObj = parseDateStr(natalDateStr, natalTimeStr);
            updateTimeDisplay();
            fetchData();
        }

        function modeChanged() {
            let mode = document.getElementById('ctrl-mode').value;
            if (mode === 'Transit') calcDateObj = new Date();
            else calcDateObj = parseDateStr(natalDateStr, natalTimeStr); 
            updateTimeDisplay();
            fetchData();
        }

        function adjTime(val, unit) {
            if (unit === 'y') calcDateObj.setFullYear(calcDateObj.getFullYear() + val);
            if (unit === 'm') calcDateObj.setMonth(calcDateObj.getMonth() + val);
            if (unit === 'd') calcDateObj.setDate(calcDateObj.getDate() + val);
            if (unit === 'h') calcDateObj.setHours(calcDateObj.getHours() + val);
            if (unit === 'min') calcDateObj.setMinutes(calcDateObj.getMinutes() + val);
            updateTimeDisplay();
            fetchData();
        }

        function updateTimeDisplay() {
            let obj = getFormattedCalc();
            document.getElementById('current-chart-time').innerText = `Chart Time: ${obj.d} ${obj.t}`;
            
            if (natalDateStr && natalTimeStr) {
                let natal = parseDateStr(natalDateStr, natalTimeStr);
                let modeStr = document.getElementById('ctrl-mode').value;
                let refDate = (modeStr === 'Natal') ? new Date() : calcDateObj;
                
                let ageCompleted = refDate.getFullYear() - natal.getFullYear();
                let m = refDate.getMonth() - natal.getMonth();
                if (m < 0 || (m === 0 && refDate.getDate() < natal.getDate())) {
                    ageCompleted--;
                }
                let runningAge = ageCompleted >= 0 ? ageCompleted + 1 : 1;
                document.getElementById('d-age').value = runningAge;
            }
        }

        function backToInput() {
            document.getElementById('dashboard-screen').classList.add('hidden');
            document.getElementById('input-screen').classList.remove('hidden');
            document.getElementById('content-wrap').classList.add('hidden');
        }

        function switchTab(id, el) {
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.add('hidden'));
            document.querySelectorAll('.tab-btn').forEach(b => {
                b.classList.remove('active', 'border-blue-500', 'text-blue-600', 'text-green-700', 'text-purple-700');
                b.classList.add('border-transparent');
            });
            document.getElementById(id).classList.remove('hidden');
            el.classList.add('active', 'border-blue-500');
            if(id === 'tab-vastu') el.classList.add('text-green-700');
            else if(id === 'tab-dasha') el.classList.add('text-purple-700');
            else el.classList.add('text-blue-600');
            el.classList.remove('border-transparent');
        }

        function toggleDasha(targetClass) {
            const rows = document.querySelectorAll('.' + targetClass);
            const icon = document.getElementById('icon-' + targetClass);
            let isHidden = true;

            rows.forEach(row => {
                if (row.classList.contains('hidden')) {
                    row.classList.remove('hidden');
                    isHidden = false;
                } else {
                    row.classList.add('hidden');
                    if (targetClass.startsWith('ad-')) {
                        const idxs = targetClass.split('-').slice(1);
                        document.querySelectorAll(`[class^="pd-${idxs[0]}-"]`).forEach(el => el.classList.add('hidden'));
                        document.querySelectorAll(`[class^="sd-${idxs[0]}-"]`).forEach(el => el.classList.add('hidden'));
                        document.querySelectorAll(`[class^="prd-${idxs[0]}-"]`).forEach(el => el.classList.add('hidden'));
                        document.querySelectorAll(`[id^="icon-pd-${idxs[0]}-"]`).forEach(ic => ic.innerText = '+');
                        document.querySelectorAll(`[id^="icon-sd-${idxs[0]}-"]`).forEach(ic => ic.innerText = '+');
                    } else if (targetClass.startsWith('pd-')) {
                        const idxs = targetClass.split('-').slice(1);
                        document.querySelectorAll(`[class^="sd-${idxs[0]}-${idxs[1]}-"]`).forEach(el => el.classList.add('hidden'));
                        document.querySelectorAll(`[class^="prd-${idxs[0]}-${idxs[1]}-"]`).forEach(el => el.classList.add('hidden'));
                        document.querySelectorAll(`[id^="icon-sd-${idxs[0]}-${idxs[1]}-"]`).forEach(ic => ic.innerText = '+');
                    } else if (targetClass.startsWith('sd-')) {
                        const idxs = targetClass.split('-').slice(1);
                        document.querySelectorAll(`[class^="prd-${idxs[0]}-${idxs[1]}-${idxs[2]}-"]`).forEach(el => el.classList.add('hidden'));
                    }
                }
            });
            if (icon) icon.innerText = isHidden ? '-' : '+';
        }

        function openModal(id) {
            let pad = (n) => n.toString().padStart(2, '0');
            let today = new Date(); 
            
            if(id === 'forward-modal') {
                document.getElementById('fc-date').value = `${pad(today.getDate())}-${pad(today.getMonth()+1)}-${today.getFullYear()}`;
            }
            if(id === 'retro-modal') {
                document.getElementById('rr-start').value = `${pad(today.getDate())}-${pad(today.getMonth()+1)}-${today.getFullYear()}`;
                let nextYr = new Date(today); nextYr.setFullYear(nextYr.getFullYear()+1);
                document.getElementById('rr-end').value = `${pad(nextYr.getDate())}-${pad(nextYr.getMonth()+1)}-${nextYr.getFullYear()}`;
            }
            if(id === 'ssub-modal') {
                document.getElementById('ss-start').value = `${pad(today.getDate())}-${pad(today.getMonth()+1)}-${today.getFullYear()} 00:00:00`;
                document.getElementById('ss-end').value = `${pad(today.getDate())}-${pad(today.getMonth()+1)}-${today.getFullYear()} 23:59:59`;
                document.getElementById('ss-body').innerHTML = '';
            }
            document.getElementById(id).classList.remove('hidden');
        }
        function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

        async function runForwardCheck() {
            document.getElementById('fc-res').innerText = "Calculating...";
            const payload = {
                date: document.getElementById('fc-date').value || getFormattedCalc().d,
                planet: document.getElementById('fc-planet').value,
                t_type: document.getElementById('fc-type').value,
                t_val: parseFloat(document.getElementById('fc-val').value),
                tz: document.getElementById('i-tz').value,
                aya: document.getElementById('i-aya').value
            };
            const res = await fetch('/api/forward_check', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const d = await res.json();
            if (d.status === 'success') document.getElementById('fc-res').innerText = d.result;
            else document.getElementById('fc-res').innerText = "Error: " + d.message;
        }

        async function runRetroReport() {
            document.getElementById('rr-body').innerHTML = "<tr><td colspan='2' class='p-4 text-gray-500 font-bold'>Calculating...</td></tr>";
            const payload = {
                start: document.getElementById('rr-start').value,
                end: document.getElementById('rr-end').value,
                planet: document.getElementById('rr-planet').value,
                tz: document.getElementById('i-tz').value,
                aya: document.getElementById('i-aya').value
            };
            const res = await fetch('/api/retro_report', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const d = await res.json();
            if (d.status === 'success') {
                document.getElementById('rr-body').innerHTML = d.results.map(r => `<tr><td class="font-bold border border-gray-200 px-2 py-2 text-gray-800">${r.date}</td><td class="${r.status.includes('RETRO')?'text-red-600':'text-green-600'} font-bold border border-gray-200 px-2 py-2">${r.status}</td></tr>`).join('');
            } else {
                document.getElementById('rr-body').innerHTML = `<tr><td colspan='2' class="text-red-500 font-bold border px-2 py-2">Error: ${d.message}</td></tr>`;
            }
        }
        
        async function runSSubTracker() {
            document.getElementById('ss-body').innerHTML = "";
            document.getElementById('ss-loader').classList.remove('hidden');
            
            const payload = {
                start: document.getElementById('ss-start').value,
                end: document.getElementById('ss-end').value,
                tz: document.getElementById('i-tz').value,
                aya: document.getElementById('i-aya').value,
                rahu: document.getElementById('i-rahu').value
            };
            
            try {
                const res = await fetch('/api/ssub_tracker', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                const d = await res.json();
                document.getElementById('ss-loader').classList.add('hidden');
                
                if (d.status === 'success') {
                    let html = '';
                    const planets = ["Moon", "Sun", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"];
                    for (let p of planets) {
                        let events = d.results[p];
                        if (events && events.length > 0) {
                            html += `<div class="flex flex-col md:flex-row items-start mb-4 border-b pb-4">`;
                            html += `<div class="w-24 font-bold text-lg pt-1 text-gray-800 shrink-0">${p}</div>`;
                            html += `<div class="flex flex-wrap gap-2 flex-1">`;
                            for (let ev of events) {
                                html += `<div class="bg-gray-50 border border-gray-300 rounded px-2 py-1 text-center min-w-[80px] shadow-sm">
                                            <div class="text-xs text-blue-800 font-bold">${ev.val}</div>
                                            <div class="text-[10px] text-gray-600 font-semibold">${ev.date}</div>
                                            <div class="text-xs text-gray-800">${ev.time}</div>
                                         </div>`;
                            }
                            html += `</div></div>`;
                        }
                    }
                    if(html === '') html = '<div class="text-gray-500 font-bold text-center py-4">No changes found in this timeframe.</div>';
                    document.getElementById('ss-body').innerHTML = html;
                } else {
                    document.getElementById('ss-body').innerHTML = `<div class="text-red-500 font-bold text-center py-4">Error: ${d.message}</div>`;
                }
            } catch(e) {
                document.getElementById('ss-loader').classList.add('hidden');
                document.getElementById('ss-body').innerHTML = `<div class="text-red-500 font-bold text-center py-4">Network or API Error</div>`;
            }
        }

        function generateMasterReport() {
            if (!window.latestAstroData) {
                alert("Please wait for chart calculations to finish.");
                return;
            }
            let d = window.latestAstroData;
            let name = document.getElementById('i-name').value || "Client";
            let dob = document.getElementById('i-dob').value;
            let time = document.getElementById('i-time').value;
            let city = document.getElementById('i-city').value;
            let mode = document.getElementById('ctrl-mode').value;
            let rot = document.getElementById('ctrl-rot').value;
            
            let printWindow = window.open('', '_blank');
            if (!printWindow) {
                alert("Please allow popups for this site to print the report.");
                return;
            }
            
            try {
                let vastuP2cRows = d.vastu_p2c.map(r => {
                    let rowData = [...r];
                    let header = rowData[0];
                    let cells = rowData.slice(1).map(c => {
                        let style = "";
                        let val = c;
                        if(c.includes('*')) { style = "background-color:#fadbd8; color:#c0392b; font-weight:bold;"; val = c.replace('*',''); }
                        else if(c.includes('+')) { style = "background-color:#d5f5e3; color:#27ae60; font-weight:bold;"; val = c.replace('+',''); }
                        return `<td style="border: 1px solid #ccc; padding: 2px; ${style}">${val}</td>`;
                    }).join('');
                    return `<tr><td style="border: 1px solid #ccc; padding: 2px; font-weight:bold; background-color:#f0f0f0;">${header}</td>${cells}</tr>`;
                }).join('');

                let vastuP2pRows = d.vastu_p2p.map(r => {
                    let color = r[4].includes('*') ? 'color:#c0392b;' : r[4].includes('+') ? 'color:#27ae60;' : '';
                    let val = r[4].replace('*','').replace('+','');
                    return `<tr>
                        <td style="border: 1px solid #ccc; padding: 2px;"><b>${r[0]}</b></td>
                        <td style="border: 1px solid #ccc; padding: 2px;">${r[1]}</td>
                        <td style="border: 1px solid #ccc; padding: 2px;"><b>${r[2]}</b></td>
                        <td style="border: 1px solid #ccc; padding: 2px;">${r[3]}</td>
                        <td style="border: 1px solid #ccc; padding: 2px; ${color} font-weight:bold;">${val}</td>
                    </tr>`;
                }).join('');
                
                let dashaHtmlRows = '';
                d.dasha.forEach(md => {
                    dashaHtmlRows += `<tr style="background-color: #e2e8f0;"><td style="border: 1px solid #ccc; padding: 2px; text-align: left; font-weight:bold;">${md.lord}</td><td style="border: 1px solid #ccc; padding: 2px; font-weight:bold;">${md.start}</td><td style="border: 1px solid #ccc; padding: 2px; font-weight:bold;">${md.end}</td></tr>`;
                    md.subs.forEach(ad => {
                        dashaHtmlRows += `<tr style="background-color: #f8fafc;"><td style="border: 1px solid #ccc; padding: 2px; text-align: left; padding-left: 10px; font-weight:bold;">↳ ${ad.lord}</td><td style="border: 1px solid #ccc; padding: 2px;">${ad.start}</td><td style="border: 1px solid #ccc; padding: 2px;">${ad.end}</td></tr>`;
                        ad.subs.forEach(pd => {
                            dashaHtmlRows += `<tr style="background-color: #ffffff;"><td style="border: 1px solid #ccc; padding: 2px; text-align: left; padding-left: 20px; font-size: 8px; color: #555;">• ${pd.lord}</td><td style="border: 1px solid #ccc; padding: 2px; font-size: 8px; color: #555;">${pd.start}</td><td style="border: 1px solid #ccc; padding: 2px; font-size: 8px; color: #555;">${pd.end}</td></tr>`;
                        });
                    });
                });

                let html = `
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>${name} - Master Report</title>
                    <style>
                        @page { margin: 10mm; size: A4; }
                        body { font-family: 'Verdana', sans-serif; font-size: 8px; color: #000; background: #fff; line-height: 1.2; }
                        .header { text-align: center; border-bottom: 2px solid #0d2538; padding-bottom: 5px; margin-bottom: 10px; }
                        .header h1 { margin: 0; font-size: 16px; color: #0d2538; text-transform: uppercase; }
                        .header p { margin: 3px 0; font-size: 10px; }
                        .grid-charts { display: flex; justify-content: space-between; margin-bottom: 15px; }
                        .chart-box { border: 1px solid #0d2538; width: 32%; text-align: center; padding: 2px; page-break-inside: avoid; border-radius: 4px; }
                        .chart-box h2 { margin: 0; background: #0d2538; color: #fff; font-size: 10px; padding: 3px; text-transform: uppercase; }
                        .chart-box svg { width: 100%; height: auto; max-width: 250px; margin: auto; display: block; }
                        .section { margin-bottom: 15px; page-break-inside: avoid; border: 1px solid #0d2538; border-radius: 4px; }
                        .section h2 { margin: 0; background: #0d2538; color: #fff; font-size: 10px; padding: 3px; text-transform: uppercase; text-align: center;}
                        table { width: 100%; border-collapse: collapse; text-align: center; margin-top: 2px; }
                        th { background-color: #0d2538; color: white; font-weight: bold; padding: 2px; border: 1px solid #ccc; }
                        td { border: 1px solid #ccc; padding: 2px; }
                        tr:nth-child(even) td { background-color: #f9f9f9; }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>KP ASTROLOGY MASTER REPORT DETAILS</h1>
                        <p><b>Name:</b> ${name} | <b>DOB:</b> ${dob} | <b>Time:</b> ${time} | <b>Place:</b> ${city}</p>
                        <p><b>Mode:</b> ${mode} | <b>Rotated to House:</b> ${rot}</p>
                    </div>
                    
                    <div class="grid-charts">
                        <div class="chart-box"><h2>Lagna Chart</h2>${d.svg_lagna}</div>
                        <div class="chart-box"><h2>Bhava Chalit</h2>${d.svg_chalit}</div>
                        <div class="chart-box"><h2>Lal Kitab (${d.lk_range})</h2>${d.svg_lk}</div>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; gap: 10px;">
                        <div class="section" style="width: 50%;">
                            <h2>Planetary Positions</h2>
                            <table>
                                <tr><th>Planet</th><th>Sign</th><th>Degree</th><th>Nakshatra</th><th>Star L</th><th>Sub L</th><th>S-Sub</th></tr>
                                ${d.planets.map(r => `<tr><td><b>${r[0]}</b></td><td><b style="color:#0d2538;">${r[1]}</b></td><td>${r[2]}</td><td>${r[3]}</td><td>${r[4]}</td><td>${r[5]}</td><td>${r[6]}</td></tr>`).join('')}
                            </table>
                        </div>
                        <div class="section" style="width: 50%;">
                            <h2>Cusp Positions</h2>
                            <table>
                                <tr><th>House</th><th>Sign</th><th>Degree</th><th>Nakshatra</th><th>Star L</th><th>Sub L</th><th>S-Sub</th></tr>
                                ${d.cusps.map(r => `<tr><td><b>${r[0]}</b></td><td><b style="color:#0d2538;">${r[1]}</b></td><td>${r[2]}</td><td>${r[3]}</td><td>${r[4]}</td><td>${r[5]}</td><td>${r[6]}</td></tr>`).join('')}
                            </table>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>Nadi Significators</h2>
                        <table>
                            <tr><th>PLANET</th><th>P-SIGNIFS</th><th>STAR LORD</th><th>ST-SIGNIFS</th><th>SUB LORD</th><th>SB-SIGNIFS</th></tr>
                            ${d.nadi.map(r => `<tr><td><b>${r[0]}</b></td><td>${r[1]}</td><td><b style="color:#0d2538;">${r[2]}</b></td><td>${r[3]}</td><td><b style="color:#0d2538;">${r[4]}</b></td><td>${r[5]}</td></tr>`).join('')}
                        </table>
                    </div>
                    
                    <div class="section">
                        <h2>Vimshottari Dasha (3 Levels)</h2>
                        <div style="padding: 3px; font-weight:bold; color: #c0392b;">${d.dasha_bal}</div>
                        <table>
                            <tr><th>Dasha Lord</th><th>Start Date</th><th>End Date</th></tr>
                            ${dashaHtmlRows}
                        </table>
                    </div>

                    <div class="section" style="border-color: #1e8449;">
                        <h2 style="background-color: #1e8449;">Astro Vastu</h2>
                        <div style="padding: 5px;">
                            <h3 style="margin: 0 0 5px 0; font-size: 10px; color: #0d2538;">Planet to House Aspects</h3>
                            <table style="table-layout: fixed; word-wrap: break-word;">
                                <tr><th style="background-color: #eaecee; color:#0d2538;">Dir</th>${d.vastu_dirs.map(dir => `<th style="background-color: #82e0aa; color:black;">${dir}</th>`).join('')}</tr>
                                ${vastuP2cRows}
                            </table>
                            
                            <h3 style="margin: 10px 0 5px 0; font-size: 10px; color: #0d2538;">Planet to Planet Aspects</h3>
                            <table>
                                <tr><th>FROM</th><th style="background-color:#eaecee; color:#000;">DIR 1</th><th>TO</th><th style="background-color:#eaecee; color:#000;">DIR 2</th><th>ASP</th></tr>
                                ${vastuP2pRows}
                            </table>
                        </div>
                    </div>

                </body>
                </html>
                `;

                printWindow.document.write(html);
                printWindow.document.close();
                printWindow.focus();
                setTimeout(() => { printWindow.print(); printWindow.close(); }, 500);
            } catch (e) {
                printWindow.close();
                alert("Error generating report: " + e.message);
            }
        }

        async function fetchData() {
            document.getElementById('content-wrap').classList.add('hidden');
            document.getElementById('loader').classList.remove('hidden');

            let calcFmt = getFormattedCalc();
            let modeStr = document.getElementById('ctrl-mode').value;
            let rotStr = document.getElementById('ctrl-rot').value;

            document.getElementById('title-lagna').innerText = `Lagna Chart (${modeStr} - House ${rotStr})`;
            document.getElementById('title-chalit').innerText = `Bhava Chalit (${modeStr} - House ${rotStr})`;

            const payload = {
                natal_date: natalDateStr, natal_time: natalTimeStr,
                calc_date: calcFmt.d, calc_time: calcFmt.t,
                lat: document.getElementById('i-lat').value, lon: document.getElementById('i-lon').value,
                tz: document.getElementById('i-tz').value, mode: modeStr, rot_house: rotStr,
                horary: document.getElementById('i-horary').value,
                aya: document.getElementById('i-aya').value, rahu: document.getElementById('i-rahu').value,
                age: document.getElementById('d-age').value
            };

            try {
                const res = await fetch('/api/calculate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                const d = await res.json();
                if (d.status !== 'success') { alert(d.message); return; }

                window.latestAstroData = d;

                document.getElementById('svg-lagna').innerHTML = d.svg_lagna;
                document.getElementById('svg-chalit').innerHTML = d.svg_chalit;
                document.getElementById('svg-lk').innerHTML = d.svg_lk;
                
                document.getElementById('title-lk').innerText = `Lal Kitab Varshphal (${d.lk_range})`;

                const buildTr = (arr, colorCol=null) => arr.map((r,i) => `<tr class="${i%2==0?'bg-white':'bg-gray-50'}">${r.map((c, j) => `<td class="${j===colorCol?'font-bold text-blue-700':''}">${c}</td>`).join('')}</tr>`).join('');
                
                document.getElementById('tb-planets').innerHTML = d.planets.map((r,i) => `
                    <tr class="${i%2==0?'bg-white':'bg-gray-50'} text-gray-800 border-b border-gray-200 hover:bg-blue-50 transition-colors">
                        <td class="border border-gray-200 p-2 font-bold">${r[0]}</td>
                        <td class="border border-gray-200 p-2 text-blue-800 font-bold">${r[1]}</td>
                        <td class="border border-gray-200 p-2">${r[2]}</td>
                        <td class="border border-gray-200 p-2">${r[3]}</td>
                        <td class="border border-gray-200 p-2">${r[4]}</td>
                        <td class="border border-gray-200 p-2">${r[5]}</td>
                        <td class="border border-gray-200 p-2">${r[6]}</td>
                    </tr>
                `).join('');

                document.getElementById('tb-cusps').innerHTML = d.cusps.map((r,i) => `
                    <tr class="${i%2==0?'bg-white':'bg-gray-50'} text-gray-800 border-b border-gray-200 hover:bg-green-50 transition-colors">
                        <td class="border border-gray-200 p-2 font-bold">${r[0]}</td>
                        <td class="border border-gray-200 p-2 text-green-800 font-bold">${r[1]}</td>
                        <td class="border border-gray-200 p-2">${r[2]}</td>
                        <td class="border border-gray-200 p-2">${r[3]}</td>
                        <td class="border border-gray-200 p-2">${r[4]}</td>
                        <td class="border border-gray-200 p-2">${r[5]}</td>
                        <td class="border border-gray-200 p-2">${r[6]}</td>
                    </tr>
                `).join('');

                document.getElementById('tb-nadi').innerHTML = d.nadi.map((r,i) => `
                    <tr class="${i%2==0?'bg-white':'bg-blue-50'} border-b border-gray-200 text-gray-800 hover:bg-gray-100 transition-colors">
                        <td class="border border-gray-200 p-3 font-bold">${r[0]}</td>
                        <td class="border border-gray-200 p-3">${r[1]}</td>
                        <td class="border border-gray-200 p-3 font-bold text-blue-800">${r[2]}</td>
                        <td class="border border-gray-200 p-3">${r[3]}</td>
                        <td class="border border-gray-200 p-3 font-bold text-blue-800">${r[4]}</td>
                        <td class="border border-gray-200 p-3">${r[5]}</td>
                    </tr>
                `).join('');
                
                document.getElementById('tb-p2p').innerHTML = d.hits_p2p.map((r,i) => `<tr class="${i%2==0?'bg-white':'bg-gray-50'} ${r[4]==='Positive'?'text-green-700':r[4]==='Negative'?'text-red-700':''} font-bold border-b border-gray-200 hover:bg-gray-100"><td class="border border-gray-200 p-2">${r[0]}</td><td class="border border-gray-200 p-2">${r[1]}</td><td class="border border-gray-200 p-2">${r[2]}</td><td class="border border-gray-200 p-2">${r[3]}</td><td class="border border-gray-200 p-2">${r[4]}</td></tr>`).join('');
                document.getElementById('tb-p2h').innerHTML = d.hits_p2h.map((r,i) => `<tr class="${i%2==0?'bg-white':'bg-gray-50'} ${r[4]==='Positive'?'text-green-700':r[4]==='Negative'?'text-red-700':''} font-bold border-b border-gray-200 hover:bg-gray-100"><td class="border border-gray-200 p-2">${r[0]}</td><td class="border border-gray-200 p-2">${r[1]}</td><td class="border border-gray-200 p-2">${r[2]}</td><td class="border border-gray-200 p-2">${r[3]}</td><td class="border border-gray-200 p-2">${r[4]}</td></tr>`).join('');

                let thHtml = '<tr><th class="bg-[#1e3a8a] text-white p-2 border border-blue-800">Direction</th>';
                for(let i=1; i<=12; i++) thHtml += `<th class="bg-[#22c55e] text-white p-2 border border-green-700">${d.vastu_dirs[i-1]}</th>`;
                thHtml += '</tr>';
                document.getElementById('th-vastu-p2c').innerHTML = thHtml;
                
                let tbHtml = '';
                for(let r of d.vastu_p2c) {
                    let rowData = [...r];
                    tbHtml += `<tr class="border-b border-gray-200 hover:bg-gray-50"><td class="font-bold bg-gray-100 p-2 border border-gray-200 text-gray-800">${rowData[0]}</td>`;
                    for(let cell of rowData.slice(1)) {
                        let style = "";
                        if(cell.includes('*')) { style = "background-color:#fadbd8; color:#c0392b; font-weight:bold;"; cell=cell.replace('*','');}
                        else if(cell.includes('+')) { style = "background-color:#d5f5e3; color:#27ae60; font-weight:bold;"; cell=cell.replace('+','');}
                        tbHtml += `<td style="${style}" class="border border-gray-200 p-2">${cell}</td>`;
                    }
                    tbHtml += `</tr>`;
                }
                document.getElementById('tb-vastu-p2c').innerHTML = tbHtml;
                
                document.getElementById('tb-vastu-p2p').innerHTML = d.vastu_p2p.map((r,i) => {
                    let color = r[4].includes('*') ? 'text-red-600 bg-red-50' : r[4].includes('+') ? 'text-green-600 bg-green-50' : '';
                    let val = r[4].replace('*','').replace('+','');
                    return `<tr class="${i%2==0?'bg-white':'bg-gray-50'} border-b border-gray-200 text-gray-800 hover:bg-gray-100"><td class="border border-gray-200 p-2 font-bold">${r[0]}</td><td class="border border-gray-200 p-2">${r[1]}</td><td class="border border-gray-200 p-2 font-bold">${r[2]}</td><td class="border border-gray-200 p-2">${r[3]}</td><td class="${color} border border-gray-200 p-2 font-bold">${val}</td></tr>`;
                }).join('');

                // Dasha Tree Generation (5 Levels)
                document.getElementById('dasha-bal').innerText = d.dasha_bal;
                let dashaHtml = '';
                d.dasha.forEach((md, i) => {
                    let mdBg = md.active ? 'bg-green-200' : 'bg-blue-50 hover:bg-blue-100';
                    let mdIcon = md.active ? '-' : '+';
                    dashaHtml += `
                        <tr class="${mdBg} border-b border-gray-300 cursor-pointer" onclick="toggleDasha('ad-${i}')">
                            <td class="p-2 text-left font-bold text-blue-900 border border-gray-300"><span id="icon-ad-${i}" class="mr-2 border border-blue-900 px-1 text-xs">${mdIcon}</span>${md.lord}</td>
                            <td class="p-2 font-bold border border-gray-300">${md.start}</td>
                            <td class="p-2 font-bold border border-gray-300">${md.end}</td>
                        </tr>`;
                    md.subs.forEach((ad, j) => {
                        let adBg = ad.active ? 'bg-green-100' : 'bg-white hover:bg-gray-50';
                        let adHidden = md.active ? '' : 'hidden';
                        let adIcon = ad.active ? '-' : '+';
                        dashaHtml += `
                            <tr class="ad-${i} ${adHidden} ${adBg} border-b border-gray-200 cursor-pointer" onclick="toggleDasha('pd-${i}-${j}')">
                                <td class="p-2 text-left pl-8 font-semibold text-gray-800 border border-gray-200"><span id="icon-pd-${i}-${j}" class="mr-2 border border-gray-500 px-1 text-xs">${adIcon}</span>${ad.lord}</td>
                                <td class="p-2 border border-gray-200">${ad.start}</td>
                                <td class="p-2 border border-gray-200">${ad.end}</td>
                            </tr>`;
                        ad.subs.forEach((pd, k) => {
                            let pdBg = pd.active ? 'bg-green-200 font-bold text-black' : 'bg-gray-50 hover:bg-gray-100 text-gray-600';
                            let pdHidden = ad.active ? '' : 'hidden';
                            let pdIcon = pd.active ? '-' : '+';
                            dashaHtml += `
                                <tr class="pd-${i}-${j} ${pdHidden} ${pdBg} border-b border-gray-100 text-xs cursor-pointer" onclick="toggleDasha('sd-${i}-${j}-${k}')">
                                    <td class="p-2 text-left pl-12 border border-gray-100"><span id="icon-sd-${i}-${j}-${k}" class="mr-2 border border-gray-400 px-1 text-xs">${pdIcon}</span>${pd.lord}</td>
                                    <td class="p-2 border border-gray-100">${pd.start}</td>
                                    <td class="p-2 border border-gray-100">${pd.end}</td>
                                </tr>`;
                            pd.subs.forEach((sd, l) => {
                                let sdBg = sd.active ? 'bg-green-100 font-bold text-black' : 'bg-white hover:bg-gray-50 text-gray-500';
                                let sdHidden = pd.active ? '' : 'hidden';
                                let sdIcon = sd.active ? '-' : '+';
                                dashaHtml += `
                                    <tr class="sd-${i}-${j}-${k} ${sdHidden} ${sdBg} border-b border-gray-100 text-[11px] cursor-pointer" onclick="toggleDasha('prd-${i}-${j}-${k}-${l}')">
                                        <td class="p-2 text-left pl-16 border border-gray-100"><span id="icon-prd-${i}-${j}-${k}-${l}" class="mr-2 border border-gray-300 px-1 text-[10px]">${sdIcon}</span>${sd.lord}</td>
                                        <td class="p-2 border border-gray-100">${sd.start}</td>
                                        <td class="p-2 border border-gray-100">${sd.end}</td>
                                    </tr>`;
                                sd.subs.forEach((prd, m) => {
                                    let prdBg = prd.active ? 'bg-green-200 font-bold text-black' : 'bg-gray-50 hover:bg-gray-100 text-gray-400';
                                    let prdHidden = sd.active ? '' : 'hidden';
                                    dashaHtml += `
                                        <tr class="prd-${i}-${j}-${k}-${l} ${prdHidden} ${prdBg} border-b border-gray-50 text-[10px]">
                                            <td class="p-2 text-left pl-20 border border-gray-50">↳ ${prd.lord}</td>
                                            <td class="p-2 border border-gray-50">${prd.start}</td>
                                            <td class="p-2 border border-gray-50">${prd.end}</td>
                                        </tr>`;
                                });
                            });
                        });
                    });
                });
                document.getElementById('tb-dasha').innerHTML = dashaHtml;

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
    matches = gc.get_cities_by_name(city_name)
    if matches:
        city_data_list = []
        for match in matches: city_data_list.extend(match.values())
        if city_data_list:
            bm = sorted(city_data_list, key=lambda x: x.get('population', 0), reverse=True)[0]
            tz = bm.get('timezone') or tf.timezone_at(lng=bm['longitude'], lat=bm['latitude']) or 'UTC'
            return jsonify({"status": "success", "lat": f"{bm['latitude']:.4f}", "lon": f"{bm['longitude']:.4f}", "tz": tz})
    try:
        resp = requests.get(f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1", headers={'User-Agent': 'KPAstroWeb'}, timeout=5).json()
        if resp:
            lat, lon = float(resp[0]['lat']), float(resp[0]['lon'])
            return jsonify({"status": "success", "lat": f"{lat:.4f}", "lon": f"{lon:.4f}", "tz": tf.timezone_at(lng=lon, lat=lat) or 'UTC'})
    except: pass
    return jsonify({"status": "error"})

@app.route('/api/ssub_tracker', methods=['POST'])
def ssub_tracker_api():
    data = request.json
    try:
        tz = pytz.timezone(data['tz'])
        dt_from = datetime.strptime(data['start'], "%d-%m-%Y %H:%M:%S")
        dt_to = datetime.strptime(data['end'], "%d-%m-%Y %H:%M:%S")
        
        if (dt_to - dt_from).days > 3:
            return jsonify({"status": "error", "message": "Limit search to 3 days maximum."})

        aya = data.get('aya', 'K.P.')
        if aya == "Chitrapaksha": swe.set_sid_mode(swe.SIDM_LAHIRI)
        elif aya == "Raman": swe.set_sid_mode(swe.SIDM_RAMAN)
        else: swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
        flags = swe.FLG_SIDEREAL

        if data.get('rahu') == "True": PLANETS["Rahu"] = swe.TRUE_NODE
        else: PLANETS["Rahu"] = swe.MEAN_NODE

        planet_list = ["Moon", "Sun", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        abbr_map = {"Sun":"Su", "Moon":"Mo", "Mars":"Ma", "Mercury":"Me", "Jupiter":"Ju", "Venus":"Ve", "Saturn":"Sa", "Rahu":"Ra", "Ketu":"Ke"}

        def get_lon(dt, p):
            utc = tz.localize(dt).astimezone(pytz.utc)
            jd = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0 + utc.second/3600.0)
            if p == "Ketu": return (swe.calc_ut(jd, PLANETS["Rahu"], flags)[0][0] + 180.0) % 360.0
            return swe.calc_ut(jd, PLANETS[p], flags)[0][0]

        states = {}
        results = {p: [] for p in planet_list}
        current_dt = dt_from
        
        for p in planet_list:
            states[p] = get_kp_lords(get_lon(current_dt, p))

        delta_min = timedelta(minutes=1)
        
        while current_dt < dt_to:
            next_dt = current_dt + delta_min
            for p in planet_list:
                new_state = get_kp_lords(get_lon(next_dt, p))
                if new_state != states[p]:
                    exact_dt = current_dt
                    for sec in range(1, 61):
                        test_dt = current_dt + timedelta(seconds=sec)
                        t_state = get_kp_lords(get_lon(test_dt, p))
                        if t_state != states[p]:
                            exact_dt = test_dt
                            states[p] = t_state
                            val_str = f"{abbr_map.get(t_state[0], t_state[0][:2])}/{abbr_map.get(t_state[1], t_state[1][:2])}/{abbr_map.get(t_state[2], t_state[2][:2])}"
                            results[p].append({
                                "date": exact_dt.strftime("%d %b"),
                                "time": exact_dt.strftime("%H:%M:%S"),
                                "val": val_str
                            })
                            break
            current_dt = next_dt

        return jsonify({"status": "success", "results": results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/api/forward_check', methods=['POST'])
def forward_check():
    data = request.json
    try:
        dt = datetime.strptime(data['date'], "%d-%m-%Y")
        tz = pytz.timezone(data['tz'])
        p_id = PLANETS.get(data['planet'], swe.SUN)
        
        aya = data.get('aya', 'K.P.')
        if aya == "Chitrapaksha": swe.set_sid_mode(swe.SIDM_LAHIRI)
        elif aya == "Raman": swe.set_sid_mode(swe.SIDM_RAMAN)
        else: swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
        flags = swe.FLG_SIDEREAL

        t_type = data['t_type']
        t_val_input = float(data['t_val'])
        if t_type in ["Sign", "Nakshatra"]:
            t_val = t_val_input - 1
        else:
            t_val = t_val_input
        
        span = 30.0 if t_type == "Sign" else (360.0/27.0) if t_type == "Nakshatra" else 360.0
        target_lon = t_val * span if t_type != "Degree" else t_val % 360.0

        msg_prefix = ""
        prev_match = None

        for i in range(36500): # 100 years max
            utc = tz.localize(dt).astimezone(pytz.utc)
            jd = swe.julday(utc.year, utc.month, utc.day, 12.0)
            
            lon = (swe.calc_ut(jd, PLANETS["Rahu"], flags)[0][0] + 180.0)%360.0 if data['planet'] == "Ketu" else swe.calc_ut(jd, p_id, flags)[0][0]
            
            curr_match = False
            if t_type in ["Sign", "Nakshatra"]:
                curr_match = (int(lon / span) == t_val)
            else:
                diff = abs(lon - target_lon)
                curr_match = (diff < 1.0 or diff > 359.0)

            if prev_match is None:
                prev_match = curr_match
                if curr_match and i == 0:
                    msg_prefix = "Already in target on Start Date! Next entry: "

            if curr_match and not prev_match and i > 0:
                result_str = f"{data['planet']} enters target around {dt.strftime('%d-%m-%Y')}"
                if msg_prefix:
                    result_str = msg_prefix + dt.strftime('%d-%m-%Y')
                return jsonify({"status": "success", "result": result_str})
            
            prev_match = curr_match
            dt += timedelta(days=1)
            
        return jsonify({"status": "success", "result": "Target not reached within 100 years."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/retro_report', methods=['POST'])
def retro_report():
    data = request.json
    try:
        curr = datetime.strptime(data['start'], "%d-%m-%Y")
        end = datetime.strptime(data['end'], "%d-%m-%Y")
        tz = pytz.timezone(data['tz'])
        p_id = PLANETS.get(data['planet'])
        flags = swe.FLG_SPEED | swe.FLG_SIDEREAL
        
        prev_speed = None
        results = []
        
        while curr <= end:
            utc = tz.localize(curr).astimezone(pytz.utc)
            jd = swe.julday(utc.year, utc.month, utc.day, 12.0)
            speed = swe.calc_ut(jd, p_id, flags)[0][3]
            
            if prev_speed is not None:
                if prev_speed > 0 and speed < 0: results.append({"date": curr.strftime("%d-%b-%Y"), "status": "Direct ➔ RETROGRADE"})
                elif prev_speed < 0 and speed > 0: results.append({"date": curr.strftime("%d-%b-%Y"), "status": "Retro ➔ DIRECT"})
            prev_speed = speed
            curr += timedelta(days=1)
            
        return jsonify({"status": "success", "results": results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/calculate', methods=['POST'])
def calculate_api():
    data = request.json
    try:
        aya = data.get('aya', 'K.P.')
        if aya == "Chitrapaksha": swe.set_sid_mode(swe.SIDM_LAHIRI)
        elif aya == "Raman": swe.set_sid_mode(swe.SIDM_RAMAN)
        else: swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
        flags = swe.FLG_SIDEREAL | swe.FLG_SPEED

        tz = pytz.timezone(data['tz'])
        natal_dt = datetime.strptime(f"{data['natal_date']} {data['natal_time']}", "%d-%m-%Y %H:%M:%S")
        natal_utc = tz.localize(natal_dt).astimezone(pytz.utc)
        natal_jd = swe.julday(natal_utc.year, natal_utc.month, natal_utc.day, natal_utc.hour + natal_utc.minute/60.0 + natal_utc.second/3600.0)
        
        lat, lon = float(data['lat']), float(data['lon'])
        natal_cusps, _ = swe.houses_ex(natal_jd, lat, lon, b'P', flags=flags)
        true_asc_sign = int(natal_cusps[0] / 30) + 1

        calc_dt = datetime.strptime(f"{data['calc_date']} {data['calc_time']}", "%d-%m-%Y %H:%M:%S")
        calc_utc = tz.localize(calc_dt).astimezone(pytz.utc)
        calc_jd = swe.julday(calc_utc.year, calc_utc.month, calc_utc.day, calc_utc.hour + calc_utc.minute/60.0 + calc_utc.second/3600.0)

        cusps_raw, _ = swe.houses_ex(calc_jd, lat, lon, b'P', flags=flags)
        mode = data.get('mode', 'Natal')
        
        current_eval_dt = datetime.now(tz).replace(tzinfo=None) if mode == "Natal" else calc_dt
        
        try:
            if mode == "Horary" and 1 <= int(data.get('horary', 1)) <= 249:
                diff = get_horary_ascendant(data['horary']) - cusps_raw[0]
                cusps_raw = [(c + diff) % 360 for c in cusps_raw]
        except: pass

        rot = int(data.get('rot_house', 1)) - 1
        if rot > 0: cusps_raw = [cusps_raw[(i + rot) % 12] for i in range(12)]

        asc_sign = int(cusps_raw[0] / 30) + 1
        lagna_signs = [((asc_sign + i - 1) % 12) + 1 for i in range(12)]
        chalit_signs = [int(c / 30) + 1 for c in cusps_raw]

        nak_span = 360.0 / 27.0
        cusp_res = []
        for i in range(12):
            c_lon = cusps_raw[i]
            st, sb, ssb = get_kp_lords(c_lon)
            nak_name = NAKSHATRAS[int(c_lon / nak_span)]
            cusp_res.append([i+1, ZODIAC[int(c_lon/30)], format_dms(c_lon), nak_name, st, sb, ssb])

        if data.get('rahu') == "True": PLANETS["Rahu"] = swe.TRUE_NODE
        else: PLANETS["Rahu"] = swe.MEAN_NODE

        planet_res, p_data = [], {}
        rahu_lon = 0
        h_lagna, h_chalit = {i: [] for i in range(1, 13)}, {i: [] for i in range(1, 13)}

        for name, p_id in PLANETS.items():
            calc, _ = swe.calc_ut(calc_jd, p_id, flags)
            p_lon = calc[0]
            if name == "Rahu": rahu_lon = p_lon
            is_retro = calc[3] < 0 if name not in ["Sun", "Moon"] else False
            disp = f"{name}(R)" if is_retro else name
            st, sb, ssb = get_kp_lords(p_lon)
            nak_name = NAKSHATRAS[int(p_lon / nak_span)]
            
            planet_res.append([disp, ZODIAC[int(p_lon/30)], format_dms(p_lon), nak_name, st, sb, ssb])
            p_data[name] = {"lon": p_lon, "st": st, "sb": sb, "retro": is_retro}
            
            h_lagna[(int(p_lon/30) + 1 - asc_sign + 12) % 12 + 1].append(name[:2])
            for h_idx in range(12):
                h_s, h_e = cusps_raw[h_idx], cusps_raw[(h_idx + 1) % 12]
                if (h_s < h_e and h_s <= p_lon < h_e) or (h_s > h_e and (p_lon >= h_s or p_lon < h_e)):
                    h_chalit[h_idx+1].append(name[:2]); break

        k_lon = (rahu_lon + 180.0) % 360.0
        st, sb, ssb = get_kp_lords(k_lon)
        k_nak_name = NAKSHATRAS[int(k_lon / nak_span)]
        planet_res.append(["Ketu(R)", ZODIAC[int(k_lon/30)], format_dms(k_lon), k_nak_name, st, sb, ssb])
        p_data["Ketu"] = {"lon": k_lon, "st": st, "sb": sb, "retro": True}
        h_lagna[(int(k_lon/30) + 1 - asc_sign + 12) % 12 + 1].append("Ke")
        for h_idx in range(12):
            h_s, h_e = cusps_raw[h_idx], cusps_raw[(h_idx + 1) % 12]
            if (h_s < h_e and h_s <= k_lon < h_e) or (h_s > h_e and (k_lon >= h_s or k_lon < h_e)):
                h_chalit[h_idx+1].append("Ke"); break

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
            
            nadi_res.append([
                p, 
                ", ".join(map(str, sig)) or "-", 
                st, 
                ", ".join(map(str, st_sig)) or "-", 
                sb, 
                ", ".join(map(str, sb_sig)) or "-"
            ])

        vastu_dirs = [SIGN_PROPS[s]["dir"] for s in range(1, 13)]
        vastu_p2c = []
        for r_title in ["Zodiac", "Lord", "Tatwa", "Mobility", "Sign No", "House"]:
            row = [r_title]
            for s_idx in range(1, 13):
                h_num = (s_idx - asc_sign + 12) % 12 + 1
                if r_title == "Zodiac": row.append(ZODIAC[s_idx-1][:4])
                elif r_title == "Lord": row.append(SIGN_LORDS[s_idx-1][:3])
                elif r_title == "Tatwa": row.append(SIGN_PROPS[s_idx]["tatwa"])
                elif r_title == "Mobility": row.append(SIGN_PROPS[s_idx]["mob"][:3])
                elif r_title == "Sign No": row.append(f"{s_idx}({SIGN_PROPS[s_idx]['gender']})")
                elif r_title == "House": row.append(str(h_num))
            vastu_p2c.append(row)

        for p in ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]:
            row = [p[:3]]
            p_lon = p_data[p]['lon']
            for s_idx in range(1, 13):
                h_num = (s_idx - asc_sign + 12) % 12 + 1
                diff = (cusps_raw[h_num - 1] - p_lon) % 360
                shortest = diff if diff <= 180 else 360 - diff
                val_str = f"{diff:.2f}"
                if (diff < 360 - 3.0) and (diff > 3.0) and (abs(diff - 270) > 3.0):
                    if any(abs(shortest - d) <= 3.0 for d in [45, 90, 135, 180]): val_str += "*" 
                    elif any(abs(shortest - d) <= 3.0 for d in [30, 60, 120]): val_str += "+" 
                row.append(val_str)
            vastu_p2c.append(row)

        vastu_p2p = []
        for i in range(9):
            for j in range(i+1, 9):
                p1, p2 = nadi_order[i], nadi_order[j]
                lon1, lon2 = p_data[p1]['lon'], p_data[p2]['lon']
                d1 = SIGN_PROPS[int(lon1/30)+1]["dir"]
                d2 = SIGN_PROPS[int(lon2/30)+1]["dir"]
                diff = (lon2 - lon1) % 360
                sh = diff if diff <= 180 else 360 - diff
                val_str = f"{diff:.2f}"
                if any(abs(sh - d) <= 3.0 for d in [45, 90, 135, 180]): val_str += "*"
                elif any(abs(sh - d) <= 3.0 for d in [30, 60, 120]): val_str += "+"
                vastu_p2p.append([p1[:3], d1, p2[:3], d2, val_str])

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
                    if abs(diff - asp_deg) <= 3.0: hits_p2h.append([p_name, f"H {h_idx+1}", asp_name, f"{diff:.2f}°", nature])

        age = int(data.get('age', 51))
        try: from_dt = natal_dt.replace(year=natal_dt.year + age - 1)
        except ValueError: from_dt = natal_dt + timedelta(days=365.25 * (age - 1))
        try: to_dt = natal_dt.replace(year=natal_dt.year + age)
        except ValueError: to_dt = natal_dt + timedelta(days=365.25 * age)
        to_dt = to_dt - timedelta(days=1)
        lk_range = f"{from_dt.strftime('%d-%m-%Y')} to {to_dt.strftime('%d-%m-%Y')}"

        varshphal = {i: [] for i in range(1, 13)}
        for p in nadi_order:
            lon = (p_data["Rahu"]['lon'] + 180)%360 if p == "Ketu" else swe.calc_ut(natal_jd, PLANETS[p], flags)[0][0]
            varshphal[LK_MATRIX[age - 1][(int(lon/30) + 1 - true_asc_sign + 12) % 12]].append(p[:2])

        # Dasha (Always Natal Moon)
        natal_moon_lon = swe.calc_ut(natal_jd, swe.MOON, flags)[0][0]
        dasha_list, dasha_bal = calculate_dasha(natal_moon_lon, natal_dt, current_eval_dt)

        return jsonify({
            "status": "success",
            "planets": planet_res, "cusps": cusp_res, "nadi": nadi_res,
            "hits_p2p": hits_p2p, "hits_p2h": hits_p2h,
            "vastu_dirs": vastu_dirs, "vastu_p2c": vastu_p2c, "vastu_p2p": vastu_p2p,
            "dasha": dasha_list, "dasha_bal": dasha_bal,
            "svg_lagna": draw_svg_square(h_lagna, lagna_signs, "Lagna"),
            "svg_chalit": draw_svg_square(h_chalit, chalit_signs, "Chalit"),
            "svg_lk": draw_svg_lk(varshphal),
            "lk_range": lk_range
        })
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(debug=True)
