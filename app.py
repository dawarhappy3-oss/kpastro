from flask import Flask, request, jsonify, render_template_string
import swisseph as swe
from datetime import datetime, timedelta
import pytz
import requests
import geonamescache
from timezonefinder import TimezoneFinder
import os
import csv

app = Flask(__name__)

# --- INITIALIZE GLOBAL TOOLS ---
gc = geonamescache.GeonamesCache(min_city_population=1000)
tf = TimezoneFinder()

# Define your swe path if needed (Keep empty string if ephe files are in same directory)
swe.set_ephe_path('')

DB_FILE = "kp_clients_database.csv"

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
    s = int(round((d_val-deg-m/60)*3600))
    if s == 60: s = 0; m += 1
    if m == 60: m = 0; deg += 1
    return f"{deg:02d}° {m:02d}' {s:02d}\""

def get_kp_lords(lon):
    lon_sec = int(round((lon + 1e-8) * 3600)) % 1296000
    nak_idx = lon_sec // 48000
    star_lord_idx = nak_idx % 9
    st = LORDS[star_lord_idx]
    
    rem_sec = lon_sec % 48000
    curr_sec = 0
    sb_idx = star_lord_idx
    sub_start_sec = 0
    sb = ""
    
    for i in range(9):
        span = YRS[sb_idx] * 400
        curr_sec += span
        if rem_sec < curr_sec:
            sb = LORDS[sb_idx]
            sub_start_sec = curr_sec - span
            break
        sb_idx = (sb_idx + 1) % 9
        
    rem_ss_sec = rem_sec - sub_start_sec
    rem_ss_sec_x3 = rem_ss_sec * 3
    curr_ss_sec_x3 = 0
    ssb_idx = sb_idx
    ssb = ""
    
    for i in range(9):
        span_ss_x3 = YRS[sb_idx] * YRS[ssb_idx] * 10
        curr_ss_sec_x3 += span_ss_x3
        if rem_ss_sec_x3 < curr_ss_sec_x3:
            ssb = LORDS[ssb_idx]
            break
        ssb_idx = (ssb_idx + 1) % 9
        
    return st, sb, ssb

def get_horary_ascendant(number):
    num = int(number)
    if num < 1 or num > 249: return 0.0
    
    curr_sec = 0
    curr_idx = 1
    for star in range(27):
        star_lord = star % 9
        for sub in range(9):
            sub_lord = (star_lord + sub) % 9
            span_sec = YRS[sub_lord] * 400
            next_sec = curr_sec + span_sec
            boundary = (curr_sec // 108000 + 1) * 108000
            
            if curr_sec < boundary and next_sec > boundary:
                if curr_idx == num: return (curr_sec / 3600.0) + 1e-5
                curr_idx += 1
                if curr_idx == num: return (boundary / 3600.0) + 1e-5
                curr_idx += 1
            else:
                if curr_idx == num: return (curr_sec / 3600.0) + 1e-5
                curr_idx += 1
            curr_sec = next_sec
    return 0.0

def get_placidus_cusps(jd, lat, lon, mode="Natal", horary_num=1, flags=0):
    cusp_orig, _ = swe.houses_ex(jd, lat, lon, b'P', flags=flags)
    
    if mode == "Horary" and 1 <= horary_num <= 249:
        target_asc = get_horary_ascendant(horary_num)
        temp_jd = jd
        for _ in range(15):
            c_temp, _ = swe.houses_ex(temp_jd, lat, lon, b'P', flags=flags)
            curr_asc = c_temp[0]
            diff = target_asc - curr_asc
            if diff > 180: diff -= 360
            elif diff < -180: diff += 360
            
            if abs(diff) < 0.000001: break
                
            c_plus, _ = swe.houses_ex(temp_jd + 0.0001, lat, lon, b'P', flags=flags)
            asc_plus = c_plus[0]
            diff_plus = asc_plus - curr_asc
            if diff_plus < 0: diff_plus += 360
            rate = diff_plus / 0.0001
            if rate < 10: rate = 360.0
            
            temp_jd += (diff / rate)
            
        cusp_orig, _ = swe.houses_ex(temp_jd, lat, lon, b'P', flags=flags)
        
    return list(cusp_orig)

def get_kp_color(p_name):
    c = {"Sun": "#b03a2e", "Moon": "#21618c", "Mars": "#cb4335", "Mercury": "#1e8449", "Jupiter": "#d35400", "Venus": "#c71585", "Saturn": "#2874a6", "Rahu": "#873600", "Ketu": "#873600", "Asc": "#d35400"}
    for k in c:
        if k in p_name: return c[k]
    return "#000000"

def draw_svg_square(house_data, cusp_signs):
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
                    "start": pd_start.strftime("%d-%m-%Y %H:%M"),
                    "end": pd_end.strftime("%d-%m-%Y %H:%M"),
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
                        <option value="Chitrapaksha">Lahiri</option>
                        <option value="K.P." selected>K.P.</option>
                        <option value="Raman">Raman</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-bold text-blue-900 mb-1">Rahu</label>
                    <select id="i-rahu" class="w-full border border-gray-200 rounded p-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                        <option value="Mean" selected>Mean Node</option>
                        <option value="True">True Node</option>
                    </select>
                </div>
            </div>

            <div class="flex gap-4">
                <button onclick="saveClient()" class="w-1/3 bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 px-4 rounded shadow tracking-wide">SAVE CHART</button>
                <button onclick="openModal('db-modal'); loadClients();" class="w-1/3 bg-orange-500 hover:bg-orange-600 text-white font-bold py-3 px-4 rounded shadow tracking-wide">OPEN CHART</button>
                <button onclick="openDashboard()" class="w-1/3 bg-[#16a34a] hover:bg-[#15803d] text-white font-bold py-3 px-4 rounded shadow tracking-wide">OPEN DASHBOARD</button>
            </div>
        </div>
    </div>

    <div id="db-modal" class="modal hidden fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-lg shadow-2xl p-6 max-w-4xl w-full border border-gray-300 relative">
            <button onclick="closeModal('db-modal')" class="absolute top-4 right-4 font-bold text-2xl text-gray-700 hover:text-black focus:outline-none">&times;</button>
            <h2 class="text-2xl font-bold text-orange-600 mb-6 tracking-wide">Open Saved Chart</h2>
            
            <div class="flex gap-4 mb-4">
                <label class="font-bold mt-2">🔍 Search Name / City / DOB:</label>
                <input type="text" id="db-search" onkeyup="filterClients()" class="border border-gray-300 p-2 rounded w-1/2 focus:outline-none focus:ring-1 focus:ring-orange-400">
            </div>

            <div class="h-64 overflow-y-auto border border-gray-200 rounded mb-4">
                <table class="w-full text-sm text-center border-collapse">
                    <thead class="bg-gray-100 text-gray-700 sticky top-0 shadow-sm"><tr><th class="p-2 border">Name</th><th class="p-2 border">DOB</th><th class="p-2 border">Time</th><th class="p-2 border">City</th><th class="p-2 border">Saved On</th><th class="p-2 border">Action</th></tr></thead>
                    <tbody id="db-body"></tbody>
                </table>
            </div>
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
                
                <div class="bg-white shadow rounded overflow-x-auto border border-gray-200">
                    <h3 class="font-bold text-red-900 p-3 bg-gray-50 border-b">House to House Aspects (Medical)</h3>
                    <table class="w-full text-xs text-center border-collapse">
                        <thead id="th-vastu-h2h"></thead>
                        <tbody id="tb-vastu-h2h"></tbody>
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

    <div id="forward-modal" class="modal hidden fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="bg-[#f4d03f] rounded-md shadow-2xl p-6 max-w-4xl w-full relative border border-yellow-600 flex flex-col md:flex-row gap-4">
            <button onclick="closeModal('forward-modal')" class="absolute top-2 right-4 font-bold text-3xl text-gray-700 hover:text-black focus:outline-none">&times;</button>
            
            <div class="w-full md:w-1/3 flex flex-col gap-4 mt-6 md:mt-0">
                <div class="flex items-center gap-2">
                    <label class="font-bold text-[#c0392b]">Set Date</label>
                    <input type="text" id="fc-date" class="border border-gray-400 p-1 w-28 rounded bg-white">
                </div>
                
                <div class="bg-[#e8daef] p-3 rounded border border-gray-400">
                    <div class="font-bold text-[#c0392b] mb-2 border-b border-gray-400 pb-1 flex items-center gap-2">
                        <input type="radio" checked disabled> PLANETS
                    </div>
                    <div class="flex flex-col gap-2 pl-2 text-sm font-semibold">
                        <label><input type="radio" name="fc_planet" value="Sun" checked onchange="updateFcTargetUI()"> Sun</label>
                        <label><input type="radio" name="fc_planet" value="Moon" onchange="updateFcTargetUI()"> Moon</label>
                        <label><input type="radio" name="fc_planet" value="Mars" onchange="updateFcTargetUI()"> Mars</label>
                        <label><input type="radio" name="fc_planet" value="Mercury" onchange="updateFcTargetUI()"> Mercury</label>
                        <label><input type="radio" name="fc_planet" value="Jupiter" onchange="updateFcTargetUI()"> Jupiter</label>
                        <label><input type="radio" name="fc_planet" value="Venus" onchange="updateFcTargetUI()"> Venus</label>
                        <label><input type="radio" name="fc_planet" value="Saturn" onchange="updateFcTargetUI()"> Saturn</label>
                        <label><input type="radio" name="fc_planet" value="Rahu" onchange="updateFcTargetUI()"> Rahu</label>
                        <label><input type="radio" name="fc_planet" value="Ketu" onchange="updateFcTargetUI()"> Ketu</label>
                    </div>
                </div>
                
                <button onclick="runForwardCheck()" class="bg-[#e2e8f0] hover:bg-[#cbd5e1] text-black font-bold py-2 px-4 rounded border border-gray-500 shadow mt-auto">Start Checking</button>
            </div>
            
            <div class="w-full md:w-2/3 flex flex-col gap-4 md:mt-0">
                <div class="border border-[#c0392b] p-3 rounded bg-[#f4d03f]">
                    <div class="grid grid-cols-2 text-sm text-[#c0392b] font-bold gap-y-2">
                        <div class="flex items-center gap-2">Country <input type="text" value="INDIA" class="border border-gray-400 p-1 w-32 bg-white text-black" readonly></div>
                        <div id="fc-disp-lat">Latitude</div>
                        <div class="flex items-center gap-2">City <input type="text" id="fc-city" class="border border-gray-400 p-1 w-32 bg-white text-black" readonly></div>
                        <div id="fc-disp-lon">Longitude</div>
                        <div class="col-span-2 text-right" id="fc-disp-tz">Time Zone: </div>
                    </div>
                </div>
                
                <div class="bg-[#e8daef] p-3 rounded border border-gray-400 flex-1">
                    <div class="flex justify-around font-bold text-[#c0392b] mb-2 border-b border-gray-400 pb-2">
                        <label><input type="radio" name="fc_ttype" value="Sign" checked onchange="updateFcTargetUI()"> Sign</label>
                        <label><input type="radio" name="fc_ttype" value="Nakshatra" onchange="updateFcTargetUI()"> Nakshatra</label>
                        <label><input type="radio" name="fc_ttype" value="Degree" onchange="updateFcTargetUI()"> Degree</label>
                    </div>
                    <div id="fc-target-container" class="text-sm font-semibold text-[#c0392b] overflow-y-auto max-h-[220px]">
                        </div>
                </div>
                
                <div id="fc-res" class="font-bold text-center text-lg text-blue-800 bg-white p-2 rounded shadow hidden"></div>
            </div>
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

    <script>
        let calcDateObj = new Date();
        let natalDateStr = "";
        let natalTimeStr = "";
        let allClients = [];

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
        
        async function saveClient() {
            const payload = {
                name: document.getElementById('i-name').value, dob: document.getElementById('i-dob').value, tob: document.getElementById('i-time').value,
                city: document.getElementById('i-city').value, lat: document.getElementById('i-lat').value, lon: document.getElementById('i-lon').value,
                tz: document.getElementById('i-tz').value, horary: document.getElementById('i-horary').value
            };
            const res = await fetch('/api/save_client', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
            const data = await res.json();
            alert(data.message);
        }

        async function loadClients() {
            const res = await fetch('/api/get_clients');
            const data = await res.json();
            if(data.status === 'success') {
                allClients = data.clients;
                filterClients();
            }
        }

        function filterClients() {
            const term = document.getElementById('db-search').value.toLowerCase();
            const tbody = document.getElementById('db-body');
            tbody.innerHTML = '';
            allClients.forEach(c => {
                if(c.Name.toLowerCase().includes(term) || c.City.toLowerCase().includes(term) || c.DOB.includes(term)) {
                    tbody.innerHTML += `<tr class="border-b hover:bg-gray-50">
                        <td class="p-2 border">${c.Name}</td><td class="p-2 border">${c.DOB}</td><td class="p-2 border">${c.Time}</td><td class="p-2 border">${c.City}</td><td class="p-2 border">${c['Saved On']}</td>
                        <td class="p-2 border"><button onclick="selectClient('${c.ID}', '${c.Name}', '${c.DOB}', '${c.Time}')" class="bg-green-500 text-white px-2 py-1 rounded text-xs font-bold shadow">Select</button></td>
                    </tr>`;
                }
            });
        }

        function selectClient(id, name, dob, time) {
            let c = allClients.find(x => (x.ID && x.ID === id) || (!x.ID && x.Name === name && x.DOB === dob && x.Time === time));
            if(c) {
                document.getElementById('i-name').value = c.Name; document.getElementById('i-dob').value = c.DOB; document.getElementById('i-time').value = c.Time;
                document.getElementById('i-city').value = c.City; document.getElementById('i-lat').value = c.Latitude; document.getElementById('i-lon').value = c.Longitude;
                document.getElementById('i-tz').value = c.Timezone; document.getElementById('i-horary').value = c.Horary;
                closeModal('db-modal');
                alert(`Chart for ${c.Name} loaded successfully!`);
            }
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
            if (mode === 'Natal') calcDateObj = parseDateStr(natalDateStr, natalTimeStr); 
            else calcDateObj = new Date(); 
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

        // --- DYNAMIC TARGET UI FOR FORWARD CHECK ---
        function updateFcTargetUI() {
            if (!window.latestAstroData) return;
            const tt = document.querySelector('input[name="fc_ttype"]:checked').value;
            const p_name = document.querySelector('input[name="fc_planet"]:checked').value;
            const container = document.getElementById('fc-target-container');
            
            let moon_nak_idx = 0;
            let curr_lon = 0.0;
            
            let natal_moon_lon = window.latestAstroData.natal_moon_lon;
            moon_nak_idx = Math.floor(natal_moon_lon / (360.0 / 27.0));
            curr_lon = window.latestAstroData.raw_planets[p_name] || 0.0;

            let html = '';
            if (tt === 'Sign') {
                const signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"];
                let target_idx = Math.floor(curr_lon / 30.0);
                html += '<div class="grid grid-cols-2 gap-y-2 mt-2">';
                signs.forEach((s, i) => {
                    let chk = (i === target_idx) ? 'checked' : '';
                    html += `<label class="flex items-center gap-2"><input type="radio" name="fc_tval" value="${i}" ${chk}> ${s}</label>`;
                });
                html += '</div>';
            } else if (tt === 'Nakshatra') {
                const lords_seq = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"];
                const short_naks = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Pha.", "Uttara Ph.", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ash.", "Uttara As.", "Shravana", "Dhanishta", "Shatabhis.", "Purva Bha.", "Uttara Bh.", "Revati"];
                const tara_names = ["Janam", "Sampat", "Vipat", "Kshem", "Pratyari", "Sadhak", "Vadha", "Mitra", "Ati-Mitra"];
                
                let moon_lord_idx = moon_nak_idx % 9;
                let target_idx = moon_nak_idx; 

                html += '<div class="flex flex-col mt-2 text-xs w-full">';
                for (let r = 0; r < 9; r++) {
                    let tara_idx = (r - moon_lord_idx + 9) % 9;
                    let t_color = "#2980b9";
                    if ([1, 3, 5, 7, 8].includes(tara_idx)) t_color = "#27ae60"; 
                    else if ([2, 4, 6].includes(tara_idx)) t_color = "#c0392b"; 
                    
                    html += `<div class="flex items-center justify-between border-b border-purple-200 py-1">`;
                    html += `<div class="w-10 font-bold text-blue-800 text-right pr-1">${lords_seq[r].substring(0,3)}→</div>`;
                    html += `<div class="flex flex-1 justify-around px-1">`;
                    for (let c = 0; c < 3; c++) {
                        let i = r + (c * 9);
                        let chk = (i === target_idx) ? 'checked' : '';
                        html += `<label class="flex items-center gap-1 cursor-pointer truncate"><input type="radio" name="fc_tval" value="${i}" ${chk}> <span title="${short_naks[i]}">${short_naks[i].substring(0,5)}.</span></label>`;
                    }
                    html += `</div>`;
                    html += `<div class="w-20 font-bold text-left pl-1 border-l border-purple-300" style="color:${t_color}">| ${tara_names[tara_idx]}</div>`;
                    html += `</div>`;
                }
                html += '</div>';
            } else if (tt === 'Degree') {
                let target_deg = curr_lon.toFixed(2);
                html += `<div class="mt-4 flex items-center gap-2"><label>Target Degree (0.0 - 360.0):</label> <input type="number" step="0.1" id="fc_deg_val" value="${target_deg}" class="border border-gray-400 p-1 w-24 text-black"></div>`;
            }
            container.innerHTML = html;
        }

        function openModal(id) {
            let pad = (n) => n.toString().padStart(2, '0');
            let today = new Date(); 
            
            if(id === 'forward-modal') {
                document.getElementById('fc-date').value = `${pad(today.getDate())}-${pad(today.getMonth()+1)}-${today.getFullYear()}`;
                document.getElementById('fc-city').value = document.getElementById('i-city').value;
                document.getElementById('fc-disp-lat').innerText = `Latitude: ${document.getElementById('i-lat').value}`;
                document.getElementById('fc-disp-lon').innerText = `Longitude: ${document.getElementById('i-lon').value}`;
                document.getElementById('fc-disp-tz').innerText = `Time Zone: ${document.getElementById('i-tz').value}`;
                document.getElementById('fc-res').classList.add('hidden');
                updateFcTargetUI();
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
            if(id === 'db-modal') { setTimeout(() => document.getElementById('db-search').focus(), 100); }
            document.getElementById(id).classList.remove('hidden');
        }
        
        function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

        async function runForwardCheck() {
            const resDiv = document.getElementById('fc-res');
            resDiv.innerText = "Calculating... Please wait.";
            resDiv.classList.remove('hidden');
            resDiv.classList.replace('text-blue-800', 'text-red-600');

            let tt = document.querySelector('input[name="fc_ttype"]:checked').value;
            let t_val;
            if (tt === 'Degree') t_val = parseFloat(document.getElementById('fc_deg_val').value);
            else t_val = parseInt(document.querySelector('input[name="fc_tval"]:checked').value);

            const payload = {
                date: document.getElementById('fc-date').value,
                planet: document.querySelector('input[name="fc_planet"]:checked').value,
                t_type: tt,
                t_val: t_val,
                tz: document.getElementById('i-tz').value,
                aya: document.getElementById('i-aya').value
            };

            const res = await fetch('/api/forward_check', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const d = await res.json();
            
            resDiv.classList.replace('text-red-600', 'text-blue-800');
            if (d.status === 'success') resDiv.innerText = d.result;
            else resDiv.innerText = "Error: " + d.message;
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
            
            let dashaHtmlRows = '';
            d.dasha.forEach(md => {
                if(!md.active) return;
                dashaHtmlRows += `<tr style="background-color: #e2e8f0;"><td style="border: 1px solid #ccc; padding: 2px; text-align: left; font-weight:bold;">${md.lord} (MD)</td><td style="border: 1px solid #ccc; padding: 2px; font-weight:bold;">${md.start}</td><td style="border: 1px solid #ccc; padding: 2px; font-weight:bold;">${md.end}</td></tr>`;
                md.subs.forEach(ad => {
                    if(!ad.active) return;
                    dashaHtmlRows += `<tr style="background-color: #f8fafc;"><td style="border: 1px solid #ccc; padding: 2px; text-align: left; padding-left: 10px; font-weight:bold;">↳ ${ad.lord} (AD)</td><td style="border: 1px solid #ccc; padding: 2px;">${ad.start}</td><td style="border: 1px solid #ccc; padding: 2px;">${ad.end}</td></tr>`;
                    ad.subs.forEach(pd => {
                        if(!pd.active) return;
                        dashaHtmlRows += `<tr style="background-color: #ffffff;"><td style="border: 1px solid #ccc; padding: 2px; text-align: left; padding-left: 20px; font-size: 8px; color: #555;">• ${pd.lord} (PD)</td><td style="border: 1px solid #ccc; padding: 2px; font-size: 8px; color: #555;">${pd.start}</td><td style="border: 1px solid #ccc; padding: 2px; font-size: 8px; color: #555;">${pd.end}</td></tr>`;
                        pd.subs.forEach(sd => {
                            if(!sd.active) return;
                            dashaHtmlRows += `<tr style="background-color: #ffffff;"><td style="border: 1px solid #ccc; padding: 2px; text-align: left; padding-left: 30px; font-size: 8px; color: #555;">- ${sd.lord} (SD)</td><td style="border: 1px solid #ccc; padding: 2px; font-size: 8px; color: #555;">${sd.start}</td><td style="border: 1px solid #ccc; padding: 2px; font-size: 8px; color: #555;">${sd.end}</td></tr>`;
                            sd.subs.forEach(prd => {
                                if(!prd.active) return;
                                dashaHtmlRows += `<tr style="background-color: #ffffff;"><td style="border: 1px solid #ccc; padding: 2px; text-align: left; padding-left: 40px; font-size: 8px; color: #555;">▪ ${prd.lord} (PRD)</td><td style="border: 1px solid #ccc; padding: 2px; font-size: 8px; color: #555;">${prd.start}</td><td style="border: 1px solid #ccc; padding: 2px; font-size: 8px; color: #555;">${prd.end}</td></tr>`;
                            });
                        });
                    });
                });
            });

            let vastuP2cRows = d.vastu_p2c.map(r => {
                let rowData = [...r];
                let header = rowData[0];
                let cells = rowData.slice(1).map(c => {
                    let style = ""; let val = c;
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

            let vastuH2hRows = d.vastu_h2h.map(r => {
                let cells = r.slice(1).map(c => {
                    let style = ""; let val = c;
                    if(c === "-") { style = "background-color:#f2f3f4; color:#bdc3c7;"; }
                    else if(c.includes('*')) { style = "background-color:#fadbd8; color:#c0392b; font-weight:bold;"; val = c.replace('*',''); }
                    else if(c.includes('+')) { style = "background-color:#d5f5e3; color:#27ae60; font-weight:bold;"; val = c.replace('+',''); }
                    return `<td style="border: 1px solid #ccc; padding: 2px; ${style}">${val}</td>`;
                }).join('');
                return `<tr><td style="border: 1px solid #ccc; padding: 2px; font-weight:bold; background-color:#f0f0f0;">House ${r[0]}</td>${cells}</tr>`;
            }).join('');

            let html = `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>${name} - Master Report</title>
                <style>
                    @page { margin: 10mm; size: A4; }
                    body { font-family: 'Verdana', sans-serif; font-size: 8px; color: #000; background: #fff; line-height: 1.2; padding: 10px; }
                    .header { text-align: center; border-bottom: 2px solid #0d2538; padding-bottom: 5px; margin-bottom: 10px; }
                    .header h1 { margin: 0; font-size: 16px; color: #0d2538; text-transform: uppercase; }
                    .header p { margin: 3px 0; font-size: 10px; }
                    .grid-charts { display: flex; justify-content: space-between; margin-bottom: 15px; }
                    .chart-box { border: 1px solid #0d2538; width: 32%; text-align: center; padding: 2px; page-break-inside: avoid; border-radius: 4px; }
                    .chart-box h2 { margin: 0; background: #0d2538; color: #fff; font-size: 10px; padding: 3px; text-transform: uppercase; }
                    .chart-box svg { width: 100%; height: auto; max-width: 220px; margin: auto; display: block; }
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
                    <p><b>Mode:</b> ${d.print_title} | <b>Rotated to House:</b> ${rot}</p>
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
                
                <div style="display: flex; justify-content: space-between; gap: 10px;">
                    <div class="section" style="width: 50%;">
                        <h2>Nadi Significators</h2>
                        <table>
                            <tr><th>PLANET</th><th>P-SIGNIFS</th><th>STAR LORD</th><th>ST-SIGNIFS</th><th>SUB LORD</th><th>SB-SIGNIFS</th></tr>
                            ${d.nadi.map(r => `<tr><td><b>${r[0]}</b></td><td>${r[1]}</td><td><b style="color:#0d2538;">${r[2]}</b></td><td>${r[3]}</td><td><b style="color:#0d2538;">${r[4]}</b></td><td>${r[5]}</td></tr>`).join('')}
                        </table>
                    </div>
                    <div class="section" style="width: 50%;">
                        <h2>Current Active Dasha (5 Levels)</h2>
                        <div style="padding: 3px; font-weight:bold; color: #c0392b;">${d.dasha_bal}</div>
                        <table>
                            <tr><th>Dasha Lord</th><th>Start Date</th><th>End Date</th></tr>
                            ${dashaHtmlRows}
                        </table>
                    </div>
                </div>

                <div class="section" style="border-color: #1e8449;">
                    <h2 style="background-color: #1e8449;">Astro Vastu & Medical Aspects</h2>
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
                        
                        <h3 style="margin: 10px 0 5px 0; font-size: 10px; color: #0d2538;">House to House Aspects (Medical)</h3>
                        <table style="table-layout: fixed; word-wrap: break-word;">
                            <tr><th style="background-color: #eaecee; color:#0d2538;">House</th>${[1,2,3,4,5,6,7,8,9,10,11,12].map(i => `<th style="background-color: #82e0aa; color:black;">${i}</th>`).join('')}</tr>
                            ${vastuH2hRows}
                        </table>
                    </div>
                </div>

            </body>
            </html>
            `;

            let printIframe = document.createElement('iframe');
            printIframe.style.position = 'absolute';
            printIframe.style.top = '-10000px';
            document.body.appendChild(printIframe);

            printIframe.contentDocument.open();
            printIframe.contentDocument.write(html);
            printIframe.contentDocument.close();

            setTimeout(() => {
                printIframe.contentWindow.focus();
                printIframe.contentWindow.print();
                setTimeout(() => { document.body.removeChild(printIframe); }, 2000);
            }, 500);
        }

        async function fetchData() {
            document.getElementById('content-wrap').classList.add('hidden');
            document.getElementById('loader').classList.remove('hidden');

            let calcFmt = getFormattedCalc();
            let modeStr = document.getElementById('ctrl-mode').value;
            let rotStr = document.getElementById('ctrl-rot').value;
            let horaryNum = document.getElementById('i-horary').value;
            
            let titlePrefix = modeStr === 'Horary' ? `Horary #${horaryNum}` : modeStr;
            document.getElementById('title-lagna').innerText = `Lagna Chart (${titlePrefix} - House ${rotStr})`;
            document.getElementById('title-chalit').innerText = `Bhava Chalit (${titlePrefix} - House ${rotStr})`;

            const payload = {
                natal_date: natalDateStr, natal_time: natalTimeStr, calc_date: calcFmt.d, calc_time: calcFmt.t,
                lat: document.getElementById('i-lat').value, lon: document.getElementById('i-lon').value,
                tz: document.getElementById('i-tz').value, mode: modeStr, rot_house: rotStr,
                horary: horaryNum, aya: document.getElementById('i-aya').value, 
                rahu: document.getElementById('i-rahu').value, age: document.getElementById('d-age').value
            };

            try {
                const res = await fetch('/api/calculate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                const d = await res.json();
                if (d.status !== 'success') { alert(d.message); return; }
                
                d.print_title = titlePrefix; 
                window.latestAstroData = d;
                
                document.getElementById('svg-lagna').innerHTML = d.svg_lagna;
                document.getElementById('svg-chalit').innerHTML = d.svg_chalit;
                document.getElementById('svg-lk').innerHTML = d.svg_lk;
                document.getElementById('title-lk').innerText = `Lal Kitab Varshphal (${d.lk_range})`;

                document.getElementById('tb-planets').innerHTML = d.planets.map((r,i) => `<tr class="${i%2==0?'bg-white':'bg-gray-50'} border-b"><td class="p-2 font-bold">${r[0]}</td><td class="p-2 text-blue-800 font-bold">${r[1]}</td><td class="p-2">${r[2]}</td><td class="p-2">${r[3]}</td><td class="p-2">${r[4]}</td><td class="p-2">${r[5]}</td><td class="p-2">${r[6]}</td></tr>`).join('');
                document.getElementById('tb-cusps').innerHTML = d.cusps.map((r,i) => `<tr class="${i%2==0?'bg-white':'bg-gray-50'} border-b"><td class="p-2 font-bold">${r[0]}</td><td class="p-2 text-green-800 font-bold">${r[1]}</td><td class="p-2">${r[2]}</td><td class="p-2">${r[3]}</td><td class="p-2">${r[4]}</td><td class="p-2">${r[5]}</td><td class="p-2">${r[6]}</td></tr>`).join('');
                document.getElementById('tb-nadi').innerHTML = d.nadi.map((r,i) => `<tr class="${i%2==0?'bg-white':'bg-blue-50'} border-b"><td class="p-3 font-bold">${r[0]}</td><td class="p-3">${r[1]}</td><td class="p-3 font-bold text-blue-800">${r[2]}</td><td class="p-3">${r[3]}</td><td class="p-3 font-bold text-blue-800">${r[4]}</td><td class="p-3">${r[5]}</td></tr>`).join('');
                
                document.getElementById('tb-p2p').innerHTML = d.hits_p2p.map((r,i) => `<tr class="${i%2==0?'bg-white':'bg-gray-50'} ${r[4]==='Positive'?'text-green-700':r[4]==='Negative'?'text-red-700':''} font-bold border-b"><td class="p-2">${r[0]}</td><td class="p-2">${r[1]}</td><td class="p-2">${r[2]}</td><td class="p-2">${r[3]}</td><td class="p-2">${r[4]}</td></tr>`).join('');
                document.getElementById('tb-p2h').innerHTML = d.hits_p2h.map((r,i) => `<tr class="${i%2==0?'bg-white':'bg-gray-50'} ${r[4]==='Positive'?'text-green-700':r[4]==='Negative'?'text-red-700':''} font-bold border-b"><td class="p-2">${r[0]}</td><td class="p-2">${r[1]}</td><td class="p-2">${r[2]}</td><td class="p-2">${r[3]}</td><td class="p-2">${r[4]}</td></tr>`).join('');

                let thHtml = '<tr><th class="bg-[#1e3a8a] text-white p-2 border border-blue-800">Direction</th>';
                for(let i=1; i<=12; i++) thHtml += `<th class="bg-[#22c55e] text-white p-2 border border-green-700">${d.vastu_dirs[i-1]}</th>`;
                thHtml += '</tr>';
                document.getElementById('th-vastu-p2c').innerHTML = thHtml;
                
                let tbHtml = '';
                for(let r of d.vastu_p2c) {
                    let rowData = [...r];
                    tbHtml += `<tr class="border-b hover:bg-gray-50"><td class="font-bold bg-gray-100 p-2 border">${rowData[0]}</td>`;
                    for(let cell of rowData.slice(1)) {
                        let style = "";
                        if(cell.includes('*')) { style = "background-color:#fadbd8; color:#c0392b; font-weight:bold;"; cell=cell.replace('*','');}
                        else if(cell.includes('+')) { style = "background-color:#d5f5e3; color:#27ae60; font-weight:bold;"; cell=cell.replace('+','');}
                        tbHtml += `<td style="${style}" class="border p-2">${cell}</td>`;
                    }
                    tbHtml += `</tr>`;
                }
                document.getElementById('tb-vastu-p2c').innerHTML = tbHtml;
                
                document.getElementById('tb-vastu-p2p').innerHTML = d.vastu_p2p.map((r,i) => {
                    let color = r[4].includes('*') ? 'text-red-600 bg-red-50' : r[4].includes('+') ? 'text-green-600 bg-green-50' : '';
                    let val = r[4].replace('*','').replace('+','');
                    return `<tr class="${i%2==0?'bg-white':'bg-gray-50'} border-b hover:bg-gray-100"><td class="border p-2 font-bold">${r[0]}</td><td class="border p-2">${r[1]}</td><td class="border p-2 font-bold">${r[2]}</td><td class="border p-2">${r[3]}</td><td class="${color} border p-2 font-bold">${val}</td></tr>`;
                }).join('');

                let thH2hHtml = '<tr><th class="bg-[#1e3a8a] text-white p-2 border">House</th>';
                for(let i=1; i<=12; i++) thH2hHtml += `<th class="bg-[#22c55e] text-white p-2 border">${i}</th>`;
                thH2hHtml += '</tr>';
                document.getElementById('th-vastu-h2h').innerHTML = thH2hHtml;
                
                document.getElementById('tb-vastu-h2h').innerHTML = d.vastu_h2h.map((r,i) => {
                    let rowHtml = `<tr class="border-b hover:bg-gray-50"><td class="font-bold bg-gray-100 p-2 border">House ${r[0]}</td>`;
                    for(let cell of r.slice(1)) {
                        let style = ""; let val = cell;
                        if(cell === "-") { style = "background-color:#f3f4f6; color:#9ca3af;"; } 
                        else if(cell.includes('*')) { style = "background-color:#fadbd8; color:#c0392b; font-weight:bold;"; val = cell.replace('*',''); } 
                        else if(cell.includes('+')) { style = "background-color:#d5f5e3; color:#27ae60; font-weight:bold;"; val = cell.replace('+',''); }
                        rowHtml += `<td style="${style}" class="border p-2">${val}</td>`;
                    }
                    rowHtml += `</tr>`;
                    return rowHtml;
                }).join('');

                document.getElementById('dasha-bal').innerText = d.dasha_bal;
                let dashaHtml = '';
                d.dasha.forEach((md, i) => {
                    let isMdActive = md.active;
                    let mdBg = isMdActive ? 'bg-green-200' : 'bg-blue-50 hover:bg-blue-100';
                    
                    dashaHtml += `
                        <tr class="${mdBg} border-b border-gray-300 cursor-pointer" onclick="toggleDasha('ad-${i}')">
                            <td class="p-2 text-left font-bold text-blue-900 border border-gray-300">
                                <span id="icon-ad-${i}" class="mr-2 border border-blue-900 px-1 text-xs">${isMdActive ? '-' : '+'}</span>
                                ${md.lord}
                            </td>
                            <td class="p-2 font-bold border border-gray-300">${md.start}</td>
                            <td class="p-2 font-bold border border-gray-300">${md.end}</td>
                        </tr>`;
                    
                    if (isMdActive) {
                        md.subs.forEach((ad, j) => {
                            let isAdActive = ad.active;
                            let adBg = isAdActive ? 'bg-green-100' : 'bg-white hover:bg-gray-50';
                            
                            dashaHtml += `
                                <tr class="ad-${i} ${adBg} border-b border-gray-200 cursor-pointer" onclick="toggleDasha('pd-${i}-${j}')">
                                    <td class="p-2 text-left pl-8 font-semibold text-gray-800 border border-gray-200">
                                        <span id="icon-pd-${i}-${j}" class="mr-2 border border-gray-500 px-1 text-xs">${isAdActive ? '-' : '+'}</span>
                                        ↳ ${ad.lord}
                                    </td>
                                    <td class="p-2 border border-gray-200">${ad.start}</td>
                                    <td class="p-2 border border-gray-200">${ad.end}</td>
                                </tr>`;
                                
                            if (isAdActive) {
                                ad.subs.forEach((pd, k) => {
                                    let isPdActive = pd.active;
                                    let pdBg = isPdActive ? 'bg-green-50 font-bold text-black' : 'bg-gray-50 hover:bg-gray-100 text-gray-600';
                                    let pdIcon = isPdActive ? '-' : '+';
                                    
                                    dashaHtml += `
                                        <tr class="pd-${i}-${j} ${pdBg} border-b border-gray-100 text-xs cursor-pointer" onclick="toggleDasha('sd-${i}-${j}-${k}')">
                                            <td class="p-2 text-left pl-16 border border-gray-100">
                                                <span id="icon-sd-${i}-${j}-${k}" class="mr-2 border border-gray-400 px-1 text-[10px]">${pdIcon}</span>
                                                • ${pd.lord}
                                            </td>
                                            <td class="p-2 border border-gray-100">${pd.start}</td>
                                            <td class="p-2 border border-gray-100">${pd.end}</td>
                                        </tr>`;
                                        
                                    if(isPdActive) {
                                        pd.subs.forEach((sd, l) => {
                                            let isSdActive = sd.active;
                                            let sdBg = isSdActive ? 'bg-green-100 font-bold text-black' : 'bg-white hover:bg-gray-50 text-gray-500';
                                            let sdIcon = isSdActive ? '-' : '+';
                                            dashaHtml += `
                                            <tr class="sd-${i}-${j}-${k} ${sdBg} border-b border-gray-100 text-[11px] cursor-pointer" onclick="toggleDasha('prd-${i}-${j}-${k}-${l}')">
                                                <td class="p-2 text-left pl-24 border border-gray-100">
                                                    <span id="icon-prd-${i}-${j}-${k}-${l}" class="mr-2 border border-gray-300 px-1 text-[10px]">${sdIcon}</span>
                                                    - ${sd.lord}
                                                </td>
                                                <td class="p-2 border border-gray-100">${sd.start}</td>
                                                <td class="p-2 border border-gray-100">${sd.end}</td>
                                            </tr>`;
                                            
                                            if(isSdActive) {
                                                sd.subs.forEach((prd, m) => {
                                                    let prdBg = prd.active ? 'bg-green-200 font-bold text-black' : 'bg-gray-50 text-gray-400';
                                                    dashaHtml += `
                                                    <tr class="prd-${i}-${j}-${k}-${l} ${prdBg} border-b border-gray-50 text-[10px]">
                                                        <td class="p-2 text-left pl-32 border border-gray-50">▪ ${prd.lord}</td>
                                                        <td class="p-2 border border-gray-50">${prd.start}</td>
                                                        <td class="p-2 border border-gray-50">${prd.end}</td>
                                                    </tr>`;
                                                });
                                            } else {
                                                sd.subs.forEach((prd, m) => {
                                                    dashaHtml += `
                                                    <tr class="prd-${i}-${j}-${k}-${l} hidden bg-gray-50 text-gray-400 border-b border-gray-50 text-[10px]">
                                                        <td class="p-2 text-left pl-32 border border-gray-50">▪ ${prd.lord}</td>
                                                        <td class="p-2 border border-gray-50">${prd.start}</td>
                                                        <td class="p-2 border border-gray-50">${prd.end}</td>
                                                    </tr>`;
                                                });
                                            }
                                        });
                                    } else {
                                        pd.subs.forEach((sd, l) => {
                                            dashaHtml += `
                                            <tr class="sd-${i}-${j}-${k} hidden bg-white hover:bg-gray-50 text-gray-500 border-b border-gray-100 text-[11px] cursor-pointer" onclick="toggleDasha('prd-${i}-${j}-${k}-${l}')">
                                                <td class="p-2 text-left pl-24 border border-gray-100"><span id="icon-prd-${i}-${j}-${k}-${l}" class="mr-2 border border-gray-300 px-1 text-[10px]">+</span>- ${sd.lord}</td>
                                                <td class="p-2 border border-gray-100">${sd.start}</td>
                                                <td class="p-2 border border-gray-100">${sd.end}</td>
                                            </tr>`;
                                            sd.subs.forEach((prd, m) => {
                                                dashaHtml += `
                                                <tr class="prd-${i}-${j}-${k}-${l} hidden bg-gray-50 text-gray-400 border-b border-gray-50 text-[10px]">
                                                    <td class="p-2 text-left pl-32 border border-gray-50">▪ ${prd.lord}</td>
                                                    <td class="p-2 border border-gray-50">${prd.start}</td>
                                                    <td class="p-2 border border-gray-50">${prd.end}</td>
                                                </tr>`;
                                            });
                                        });
                                    }
                                });
                            } else {
                                ad.subs.forEach((pd, k) => {
                                    dashaHtml += `
                                        <tr class="pd-${i}-${j} hidden bg-gray-50 text-gray-600 border-b border-gray-100 text-xs cursor-pointer" onclick="toggleDasha('sd-${i}-${j}-${k}')">
                                            <td class="p-2 text-left pl-16 border border-gray-100"><span id="icon-sd-${i}-${j}-${k}" class="mr-2 border border-gray-400 px-1 text-[10px]">+</span>• ${pd.lord}</td>
                                            <td class="p-2 border border-gray-100">${pd.start}</td>
                                            <td class="p-2 border border-gray-100">${pd.end}</td>
                                        </tr>`;
                                    pd.subs.forEach((sd, l) => {
                                        dashaHtml += `
                                        <tr class="sd-${i}-${j}-${k} hidden bg-white hover:bg-gray-50 text-gray-500 border-b border-gray-100 text-[11px] cursor-pointer" onclick="toggleDasha('prd-${i}-${j}-${k}-${l}')">
                                            <td class="p-2 text-left pl-24 border border-gray-100"><span id="icon-prd-${i}-${j}-${k}-${l}" class="mr-2 border border-gray-300 px-1 text-[10px]">+</span>- ${sd.lord}</td>
                                            <td class="p-2 border border-gray-100">${sd.start}</td>
                                            <td class="p-2 border border-gray-100">${sd.end}</td>
                                        </tr>`;
                                        sd.subs.forEach((prd, m) => {
                                            dashaHtml += `
                                            <tr class="prd-${i}-${j}-${k}-${l} hidden bg-gray-50 text-gray-400 border-b border-gray-50 text-[10px]">
                                                <td class="p-2 text-left pl-32 border border-gray-50">▪ ${prd.lord}</td>
                                                <td class="p-2 border border-gray-50">${prd.start}</td>
                                                <td class="p-2 border border-gray-50">${prd.end}</td>
                                            </tr>`;
                                        });
                                    });
                                });
                            }
                        });
                    } else {
                        md.subs.forEach((ad, j) => {
                            dashaHtml += `
                                <tr class="ad-${i} hidden bg-white hover:bg-gray-50 border-b border-gray-200 cursor-pointer" onclick="toggleDasha('pd-${i}-${j}')">
                                    <td class="p-2 text-left pl-8 font-semibold text-gray-800 border border-gray-200"><span id="icon-pd-${i}-${j}" class="mr-2 border border-gray-500 px-1 text-xs">+</span>↳ ${ad.lord}</td>
                                    <td class="p-2 border border-gray-200">${ad.start}</td>
                                    <td class="p-2 border border-gray-200">${ad.end}</td>
                                </tr>`;
                            ad.subs.forEach((pd, k) => {
                                dashaHtml += `
                                    <tr class="pd-${i}-${j} hidden bg-gray-50 text-gray-600 border-b border-gray-100 text-xs cursor-pointer" onclick="toggleDasha('sd-${i}-${j}-${k}')">
                                        <td class="p-2 text-left pl-16 border border-gray-100"><span id="icon-sd-${i}-${j}-${k}" class="mr-2 border border-gray-400 px-1 text-[10px]">+</span>• ${pd.lord}</td>
                                        <td class="p-2 border border-gray-100">${pd.start}</td>
                                        <td class="p-2 border border-gray-100">${pd.end}</td>
                                    </tr>`;
                                pd.subs.forEach((sd, l) => {
                                    dashaHtml += `
                                    <tr class="sd-${i}-${j}-${k} hidden bg-white hover:bg-gray-50 text-gray-500 border-b border-gray-100 text-[11px] cursor-pointer" onclick="toggleDasha('prd-${i}-${j}-${k}-${l}')">
                                        <td class="p-2 text-left pl-24 border border-gray-100"><span id="icon-prd-${i}-${j}-${k}-${l}" class="mr-2 border border-gray-300 px-1 text-[10px]">+</span>- ${sd.lord}</td>
                                        <td class="p-2 border border-gray-100">${sd.start}</td>
                                        <td class="p-2 border border-gray-100">${sd.end}</td>
                                    </tr>`;
                                    sd.subs.forEach((prd, m) => {
                                        dashaHtml += `
                                        <tr class="prd-${i}-${j}-${k}-${l} hidden bg-gray-50 text-gray-400 border-b border-gray-50 text-[10px]">
                                            <td class="p-2 text-left pl-32 border border-gray-50">▪ ${prd.lord}</td>
                                            <td class="p-2 border border-gray-50">${prd.start}</td>
                                            <td class="p-2 border border-gray-50">${prd.end}</td>
                                        </tr>`;
                                    });
                                });
                            });
                        });
                    }
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

# --- API ROUTES ---

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/api/location', methods=['POST'])
def api_location():
    city = request.json.get('city', '').title()
    matches = gc.get_cities_by_name(city)
    if matches:
        city_list = [val for m in matches for val in m.values()]
        if city_list:
            best = sorted(city_list, key=lambda x: x.get('population', 0), reverse=True)[0]
            lat, lon = best['latitude'], best['longitude']
            tz = best.get('timezone') or tf.timezone_at(lng=lon, lat=lat) or 'UTC'
            return jsonify({'status': 'success', 'lat': f"{lat:.4f}", 'lon': f"{lon:.4f}", 'tz': tz})
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1"
        res = requests.get(url, headers={'User-Agent': 'KPAstroApp/1.0'}, timeout=5).json()
        if res:
            lat, lon = float(res[0]['lat']), float(res[0]['lon'])
            tz = tf.timezone_at(lng=lon, lat=lat) or 'UTC'
            return jsonify({'status': 'success', 'lat': f"{lat:.4f}", 'lon': f"{lon:.4f}", 'tz': tz})
    except: pass
    return jsonify({'status': 'error'})

@app.route('/api/save_client', methods=['POST'])
def api_save_client():
    data = request.json
    name, dob, tob, city = data.get('name'), data.get('dob'), data.get('tob'), data.get('city')
    lat, lon, tz, horary = data.get('lat'), data.get('lon'), data.get('tz'), data.get('horary')
    
    file_exists = os.path.isfile(DB_FILE)
    next_id = 1
    if file_exists:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Name") == name and row.get("DOB") == dob and row.get("Time") == tob:
                    return jsonify({"status": "error", "message": "Chart already saved!"})
                try:
                    cid = int(row.get("ID", 0))
                    if cid >= next_id: next_id = cid + 1
                except ValueError: pass
                
    with open(DB_FILE, "a", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["ID", "Name", "DOB", "Time", "City", "Latitude", "Longitude", "Horary", "Timezone", "Saved On"])
        writer.writerow([next_id, name, dob, tob, city, lat, lon, horary, tz, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        
    return jsonify({"status": "success", "message": "Saved successfully!"})

@app.route('/api/get_clients', methods=['GET'])
def api_get_clients():
    clients = []
    if os.path.isfile(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader: clients.append(row)
    return jsonify({"status": "success", "clients": clients})

@app.route('/api/forward_check', methods=['POST'])
def api_forward_check():
    data = request.json
    try: 
        # Parse the date and set it to 12:00 PM Local Time to prevent UTC midnight boundary skipping
        start_dt = datetime.strptime(data['date'], "%d-%m-%Y").replace(hour=12, minute=0, second=0)
    except: 
        return jsonify({'status': 'error', 'message': 'Invalid date format'})
        
    p_name = data['planet']
    p_id = PLANETS.get(p_name, swe.SUN)
    
    tt = data['t_type']
    if tt == "Sign": 
        target_lon = float(data['t_val']) * 30.0
        span = 30.0
    elif tt == "Nakshatra": 
        target_lon = float(data['t_val']) * (360.0 / 27.0)
        span = 360.0 / 27.0
    else: 
        target_lon = float(data['t_val']) % 360.0
        span = 360.0

    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED if data['aya'] != "Western" else swe.FLG_SPEED
    if data['aya'] == "Chitrapaksha": swe.set_sid_mode(swe.SIDM_LAHIRI)
    elif data['aya'] == "Raman": swe.set_sid_mode(swe.SIDM_RAMAN)
    elif data['aya'] == "K.P.": swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)

    tz = pytz.timezone(data['tz'])
    curr_dt = start_dt
    prev_in_target = None
    
    for i in range(36500):
        utc = tz.localize(curr_dt).astimezone(pytz.utc)
        # Fix 1: Use exact hour/minute/second mathematically instead of defaulting to 0
        jd = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0 + utc.second/3600.0)
        
        # Fix 2: Properly handle Ketu calculation (180 degrees from Rahu)
        if p_name == "Ketu":
            r_id = PLANETS.get("Rahu", swe.MEAN_NODE)
            lon = (swe.calc_ut(jd, r_id, flags)[0][0] + 180.0) % 360.0
        else:
            lon = swe.calc_ut(jd, p_id, flags)[0][0]
            
        if tt in ["Sign", "Nakshatra"]:
            is_in_target = (int(lon / span) == int(data['t_val']))
        else:
            diff = abs(lon - target_lon)
            is_in_target = (diff < 1.0 or diff > 359.0)
            
        # Fix 3: Logic to catch the exact ENTRY (handles case if planet is already in target on Day 1)
        if is_in_target:
            if prev_in_target is False:
                return jsonify({'status': 'success', 'result': f"{p_name} enters target around {curr_dt.strftime('%d-%m-%Y')}"})
        
        if prev_in_target is None:
            prev_in_target = is_in_target
        else:
            prev_in_target = is_in_target
            
        curr_dt += timedelta(days=1)
        
    return jsonify({'status': 'success', 'result': "Target not reached within 100 years."})

@app.route('/api/retro_report', methods=['POST'])
def api_retro_report():
    data = request.json
    try:
        start = datetime.strptime(data['start'], "%d-%m-%Y")
        end = datetime.strptime(data['end'], "%d-%m-%Y")
    except: return jsonify({'status': 'error', 'message': 'Invalid date'})
    p_id = PLANETS.get(data['planet'])
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED if data['aya'] != "Western" else swe.FLG_SPEED
    if data['aya'] == "Chitrapaksha": swe.set_sid_mode(swe.SIDM_LAHIRI)
    elif data['aya'] == "K.P.": swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)

    curr, prev_speed, res = start, None, []
    while curr <= end:
        jd = swe.julday(curr.year, curr.month, curr.day, 12)
        speed = swe.calc_ut(jd, p_id, flags)[0][3]
        if prev_speed is not None:
            if prev_speed > 0 and speed < 0: res.append({'date': curr.strftime("%d-%b-%Y"), 'status': "Direct ➔ RETROGRADE"})
            elif prev_speed < 0 and speed > 0: res.append({'date': curr.strftime("%d-%b-%Y"), 'status': "Retro ➔ DIRECT"})
        prev_speed = speed
        curr += timedelta(days=1)
    return jsonify({'status': 'success', 'results': res})

@app.route('/api/ssub_tracker', methods=['POST'])
def api_ssub_tracker():
    data = request.json
    try:
        dt_from = datetime.strptime(data['start'], "%d-%m-%Y %H:%M:%S")
        dt_to = datetime.strptime(data['end'], "%d-%m-%Y %H:%M:%S")
    except: return jsonify({'status': 'error', 'message': 'Invalid date/time'})
    if (dt_to - dt_from).days > 3: return jsonify({'status': 'error', 'message': 'Limit search to 3 days max.'})

    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED if data['aya'] != "Western" else swe.FLG_SPEED
    if data['aya'] == "Chitrapaksha": swe.set_sid_mode(swe.SIDM_LAHIRI)
    elif data['aya'] == "K.P.": swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
    r_node = swe.TRUE_NODE if data['rahu'] == "True" else swe.MEAN_NODE
    tz = pytz.timezone(data['tz'])

    def get_lon(dt, p):
        utc = tz.localize(dt).astimezone(pytz.utc)
        jd = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60 + utc.second/3600)
        if p == "Ketu": return (swe.calc_ut(jd, r_node, flags)[0][0] + 180.0) % 360.0
        return swe.calc_ut(jd, PLANETS[p], flags)[0][0]

    plist = ["Moon", "Sun", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    abbr = {"Sun":"Su", "Moon":"Mo", "Mars":"Ma", "Mercury":"Me", "Jupiter":"Ju", "Venus":"Ve", "Saturn":"Sa", "Rahu":"Ra", "Ketu":"Ke"}
    current_dt = dt_from
    states = {p: get_kp_lords(get_lon(current_dt, p)) for p in plist}
    results = {p: [] for p in plist}
    
    while current_dt < dt_to:
        next_dt = current_dt + timedelta(minutes=1)
        for p in plist:
            st, sb, ssb = get_kp_lords(get_lon(next_dt, p))
            if (st, sb, ssb) != states[p]:
                exact_dt = current_dt
                for sec in range(1, 61):
                    test_dt = current_dt + timedelta(seconds=sec)
                    t_st, t_sb, t_ssb = get_kp_lords(get_lon(test_dt, p))
                    if (t_st, t_sb, t_ssb) != states[p]:
                        exact_dt = test_dt
                        states[p] = (t_st, t_sb, t_ssb)
                        results[p].append({"val": f"{abbr[t_st]}/{abbr[t_sb]}/{abbr[t_ssb]}", "date": exact_dt.strftime("%d-%m-%Y"), "time": exact_dt.strftime("%H:%M:%S")})
                        break
        current_dt = next_dt
    return jsonify({'status': 'success', 'results': results})

@app.route('/api/calculate', methods=['POST'])
def api_calculate():
    d = request.json
    try:
        dmy, hms = d['calc_date'].split('-'), d['calc_time'].split(':')
        dt_obj = datetime(int(dmy[2]), int(dmy[1]), int(dmy[0]), int(hms[0]), int(hms[1]), int(hms[2]))
        ndmy, nhms = d['natal_date'].split('-'), d['natal_time'].split(':')
        natal_dt = datetime(int(ndmy[2]), int(ndmy[1]), int(ndmy[0]), int(nhms[0]), int(nhms[1]), int(nhms[2]))
    except: return jsonify({'status': 'error', 'message': 'Date formatting error.'})

    lat, lon = float(d['lat']), float(d['lon'])
    tz = pytz.timezone(d['tz'])
    utc_calc = tz.localize(dt_obj).astimezone(pytz.utc)
    jd = swe.julday(utc_calc.year, utc_calc.month, utc_calc.day, utc_calc.hour + utc_calc.minute/60.0 + utc_calc.second/3600.0)
    
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED if d['aya'] != "Western" else swe.FLG_SPEED
    if d['aya'] == "Chitrapaksha": swe.set_sid_mode(swe.SIDM_LAHIRI)
    elif d['aya'] == "Raman": swe.set_sid_mode(swe.SIDM_RAMAN)
    elif d['aya'] == "K.P.": swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
    
    r_node = swe.TRUE_NODE if d['rahu'] == "True" else swe.MEAN_NODE
    
    cusps = get_placidus_cusps(jd, lat, lon, d['mode'], int(d['horary']), flags)
    rot = int(d['rot_house']) - 1
    
    orig_asc = cusps[0]
    orig_asc_sign = int(orig_asc / 30) + 1
    rotated_cusps = [cusps[(i + rot) % 12] for i in range(12)]
    asc_sign = int(rotated_cusps[0] / 30) + 1
    
    lagna_signs = [((asc_sign + i - 1) % 12) + 1 for i in range(12)]
    chalit_signs = [int(c / 30) + 1 for c in rotated_cusps]
    
    # Calculate Natal Moon for Navtara Anchoring
    utc_natal = tz.localize(natal_dt).astimezone(pytz.utc)
    jd_natal = swe.julday(utc_natal.year, utc_natal.month, utc_natal.day, utc_natal.hour + utc_natal.minute/60.0 + utc_natal.second/3600.0)
    natal_moon_lon = swe.calc_ut(jd_natal, swe.MOON, flags)[0][0]

    p_data = {}
    moon_lon = 0
    for p_name, p_id in PLANETS.items():
        if p_name == "Ketu": continue
        actual_id = r_node if p_name == "Rahu" else p_id
        calc_res = swe.calc_ut(jd, actual_id, flags)[0]
        ln, speed = calc_res[0], calc_res[3]
        retro = speed < 0 and p_name not in ["Sun", "Moon"]
        p_data[p_name] = {'lon': ln, 'retro': retro}
        if p_name == "Moon": moon_lon = ln
        if p_name == "Rahu": p_data["Ketu"] = {'lon': (ln + 180.0) % 360.0, 'retro': retro}

    h_lagna, h_chalit = {i: [] for i in range(1, 13)}, {i: [] for i in range(1, 13)}
    
    l_h_asc = (orig_asc_sign - asc_sign + 12) % 12 + 1
    h_lagna[l_h_asc].append("Asc")
    for i in range(12):
        s, e = rotated_cusps[i], rotated_cusps[(i+1)%12]
        if (s < e and s <= orig_asc < e) or (s > e and (orig_asc >= s or orig_asc < e)):
            h_chalit[i+1].append("Asc"); break

    for p, v in p_data.items():
        pn_disp = p + ("(R)" if v['retro'] else "")
        p_sgn = int(v['lon']/30) + 1
        l_h = (p_sgn - asc_sign + 12) % 12 + 1
        h_lagna[l_h].append(pn_disp)
        for i in range(12):
            s, e = rotated_cusps[i], rotated_cusps[(i+1)%12]
            if (s < e and s <= v['lon'] < e) or (s > e and (v['lon'] >= s or v['lon'] < e)):
                h_chalit[i+1].append(pn_disp); break

    lk_age = int(d['age'])
    c_birth, _ = swe.houses_ex(jd_natal, lat, lon, b'P', flags=flags)
    t_asc_sgn = int(c_birth[0] / 30) + 1
    v_houses = {i: [] for i in range(1, 13)}
    for p, p_id in PLANETS.items():
        if p == "Ketu": continue
        c_res = swe.calc_ut(jd_natal, p_id, flags)[0]
        n_house = (int(c_res[0]/30) + 1 - t_asc_sgn + 12) % 12 + 1
        v_h = LK_MATRIX[lk_age - 1][n_house - 1]
        v_houses[v_h].append(p)
        if p == "Rahu":
            kn_house = (int(((c_res[0] + 180)%360)/30) + 1 - t_asc_sgn + 12) % 12 + 1
            v_houses[LK_MATRIX[lk_age - 1][kn_house - 1]].append("Ketu")

    try: fr_dt = natal_dt.replace(year=natal_dt.year + lk_age - 1)
    except: fr_dt = natal_dt + timedelta(days=365.25 * (lk_age - 1))
    try: to_dt = natal_dt.replace(year=natal_dt.year + lk_age)
    except: to_dt = natal_dt + timedelta(days=365.25 * lk_age)
    lk_range = f"{fr_dt.strftime('%d-%m-%Y')} to {(to_dt - timedelta(days=1)).strftime('%d-%m-%Y')}"

    planets_arr = []
    p_order = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    raw_planets = {}
    for p in p_order:
        ln = p_data[p]['lon']
        raw_planets[p] = ln
        st, sb, ssb = get_kp_lords(ln)
        n_idx = int(ln / (360/27.0))
        planets_arr.append([p + ("(R)" if p_data[p]['retro'] else ""), ZODIAC[int(ln/30)], format_dms(ln), NAKSHATRAS[n_idx], st, sb, ssb])
        p_data[p]['st'] = st; p_data[p]['sb'] = sb

    cusps_arr = []
    for i in range(12):
        ln = rotated_cusps[i]
        st, sb, ssb = get_kp_lords(ln)
        n_idx = int(ln / (360/27.0))
        cusps_arr.append([i+1, ZODIAC[chalit_signs[i]-1], format_dms(ln), NAKSHATRAS[n_idx], st, sb, ssb])

    def get_occ(lon):
        for i in range(12):
            s, e = rotated_cusps[i], rotated_cusps[(i+1)%12]
            if (s < e and s <= lon < e) or (s > e and (lon >= s or lon < e)): return i+1
        return 1

    b_sigs = {}
    for p in p_order:
        occ = get_occ(p_data[p]['lon'])
        owns = [i+1 for i in range(12) if SIGN_LORDS[chalit_signs[i]-1] == p] if p not in ["Rahu", "Ketu"] else []
        b_sigs[p] = {'occ': occ, 'owns': owns, 'sl': SIGN_LORDS[int(p_data[p]['lon']/30)]}

    f_sigs = {}
    for p in p_order:
        s_list = [b_sigs[p]['occ']] + b_sigs[p]['owns']
        if p in ["Rahu", "Ketu"]:
            n_sgn = int(p_data[p]['lon']/30)+1
            sl = b_sigs[p]['sl']
            if sl in b_sigs: s_list.extend([b_sigs[sl]['occ']] + b_sigs[sl]['owns'])
            for op, odata in b_sigs.items():
                if op == p or op in ["Rahu", "Ketu"]: continue
                o_sgn = int(p_data[op]['lon']/30)+1
                if o_sgn == n_sgn: s_list.extend([odata['occ']] + odata['owns'])
                dist = (n_sgn - o_sgn + 12) % 12
                dist = 12 if dist == 0 else dist + 1
                if dist in {"Sun":[7],"Moon":[7],"Mercury":[7],"Venus":[7],"Mars":[4,7,8],"Jupiter":[5,7,9],"Saturn":[3,7,10]}.get(op, [7]):
                    s_list.extend([odata['occ']] + odata['owns'])
        f_sigs[p] = ", ".join(map(str, sorted(list(set(s_list)))))

    nadi_arr = []
    for p in p_order:
        st, sb = p_data[p]['st'], p_data[p]['sb']
        nadi_arr.append([p, f_sigs[p], st, f_sigs.get(st, "-"), sb, f_sigs.get(sb, "-")])

    hits_p2p, hits_p2h = [], []
    for i in range(len(p_order)):
        for j in range(i+1, len(p_order)):
            p1, p2 = p_order[i], p_order[j]
            diff = abs(p_data[p1]['lon'] - p_data[p2]['lon'])
            if diff > 180: diff = 360 - diff
            for a_deg, (a_nm, nat) in DEGREE_ASPECTS.items():
                if abs(diff - a_deg) <= 3.0: hits_p2p.append([p1, p2, a_nm, f"{diff:.2f}°", nat])

    for p in p_order:
        for i in range(12):
            diff = abs(p_data[p]['lon'] - rotated_cusps[i])
            if diff > 180: diff = 360 - diff
            for a_deg, (a_nm, nat) in DEGREE_ASPECTS.items():
                if abs(diff - a_deg) <= 3.0: hits_p2h.append([p, f"House {i+1}", a_nm, f"{diff:.2f}°", nat])

    v_dirs = [SIGN_PROPS[s]["dir"] for s in range(1, 13)]
    
    vastu_p2c = []
    vastu_p2c.append(["Zodiac"] + [ZODIAC[s-1][:4] for s in range(1, 13)])
    vastu_p2c.append(["Lord"] + [SIGN_LORDS[s-1] for s in range(1, 13)])
    vastu_p2c.append(["Tatwa"] + [SIGN_PROPS[s]["tatwa"] for s in range(1, 13)])
    vastu_p2c.append(["Mobility"] + [SIGN_PROPS[s]["mob"] for s in range(1, 13)])
    vastu_p2c.append(["Sign No"] + [f"{s}({SIGN_PROPS[s]['gender']})" for s in range(1, 13)])
    vastu_p2c.append(["House"] + [str((s - asc_sign + 12) % 12 + 1) for s in range(1, 13)])
    
    for p in p_order:
        row = [p]
        for s in range(1, 13):
            h_num = (s - asc_sign + 12) % 12 + 1
            tgt = rotated_cusps[h_num - 1]
            diff_360 = (tgt - p_data[p]['lon']) % 360
            shortest = diff_360 if diff_360 <= 180 else 360 - diff_360
            val = f"{diff_360:.2f}"
            is_excl = (diff_360 >= 360 - 3.0) or (diff_360 <= 3.0)
            if not is_excl:
                if any(abs(shortest - a) <= 3.0 for a in [45, 90, 135, 180]): val += "*"
                elif any(abs(shortest - a) <= 3.0 for a in [30, 60, 120]): val += "+"
            row.append(val)
        vastu_p2c.append(row)

    vastu_p2p = []
    for i in range(len(p_order)):
        for j in range(len(p_order)):
            if j <= i: continue
            p1, p2 = p_order[i], p_order[j]
            d1 = SIGN_PROPS[int(p_data[p1]['lon']/30)+1]["dir"]
            d2 = SIGN_PROPS[int(p_data[p2]['lon']/30)+1]["dir"]
            diff_360 = (p_data[p2]['lon'] - p_data[p1]['lon']) % 360
            shortest = diff_360 if diff_360 <= 180 else 360 - diff_360
            val = f"{diff_360:.2f}"
            is_excl = (diff_360 >= 360 - 3.0) or (diff_360 <= 3.0)
            if not is_excl:
                if any(abs(shortest - a) <= 3.0 for a in [45, 90, 135, 180]): val += "*"
                elif any(abs(shortest - a) <= 3.0 for a in [30, 60, 120]): val += "+"
            vastu_p2p.append([p1, d1, p2, d2, val])

    vastu_h2h = []
    for r_idx in range(1, 13):
        row = [r_idx]
        h1_lon = rotated_cusps[r_idx - 1]
        for c_idx in range(1, 13):
            if r_idx == c_idx:
                row.append("-")
            else:
                h2_lon = rotated_cusps[c_idx - 1]
                diff_360 = (h2_lon - h1_lon) % 360
                shortest = diff_360 if diff_360 <= 180 else 360 - diff_360
                val = f"{diff_360:.2f}"
                is_excl = (diff_360 >= 360 - 3.0) or (diff_360 <= 3.0)
                if not is_excl:
                    if any(abs(shortest - a) <= 3.0 for a in [45, 90, 135, 180]): val += "*"
                    elif any(abs(shortest - a) <= 3.0 for a in [30, 60, 120]): val += "+"
                row.append(val)
        vastu_h2h.append(row)

    dasha_data, bal_str = calculate_dasha(moon_lon, natal_dt, dt_obj)

    return jsonify({
        'status': 'success',
        'svg_lagna': draw_svg_square(h_lagna, lagna_signs),
        'svg_chalit': draw_svg_square(h_chalit, chalit_signs),
        'svg_lk': draw_svg_lk(v_houses),
        'lk_range': lk_range,
        'planets': planets_arr,
        'raw_planets': raw_planets,         # Needed for Forward Check default target
        'natal_moon_lon': natal_moon_lon,   # Needed for Navtara calculation
        'cusps': cusps_arr,
        'nadi': nadi_arr,
        'hits_p2p': hits_p2p,
        'hits_p2h': hits_p2h,
        'vastu_dirs': v_dirs,
        'vastu_p2c': vastu_p2c,
        'vastu_p2p': vastu_p2p,
        'vastu_h2h': vastu_h2h,
        'dasha': dasha_data,
        'dasha_bal': bal_str
    })

if __name__ == "__main__":
    app.run(port=5000, debug=True)
